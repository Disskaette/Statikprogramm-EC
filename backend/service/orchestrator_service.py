from backend.service.memory_service import save_snapshot
from backend.service.validation_service import validate_input
from backend.service.calculation_service import add_load_cases, add_section_forces, add_gzg_load_combinations, add_ec5_verification
import json
import hashlib
import threading
import time


class OrchestratorService:
    def __init__(self, debounce_sec: float = 0.5):
        self.debounce = debounce_sec
        self._last_hash = None
        self._last_time = 0.0
        self._running = False

    def _compute_hash(self, data: dict) -> str:
        """Erzeuge einen MD5-Hash aus dem sortierten JSON-Repräsentation des Snapshots."""
        js = json.dumps(data, sort_keys=True)
        return hashlib.md5(js.encode("utf-8")).hexdigest()

    def process_snapshot(self, snapshot: dict, callback):
        """
        Validiert Eingabedaten, überspringt doppelte oder zu schnelle Aufrufe,
        speichert einen vollständigen Snapshot, führt Berechnung aus und ruft callback auf.
        callback erhält result=result oder errors=[...]
        """
        # 1) Snapshot speichern
        # save_snapshot(snapshot)
        # 2) Validierung
        errors = validate_input(snapshot)
        if errors:
            callback(result=None, errors=errors)
            return

        now = time.time()
        if self._running or (now - self._last_time) < self.debounce:
            return

        current_hash = self._compute_hash(snapshot)
        if current_hash == self._last_hash:
            return

        self._running = True
        self._last_hash = current_hash
        self._last_time = now

        def worker():
            try:
                # Berechnung ausführen
                kombi_result = add_load_cases(snapshot)
                snapshot['Lastfallkombinationen'] = kombi_result['Lastfallkombinationen']

                # GZG-Lastkombinationen für Durchbiegungsnachweise
                gzg_result = add_gzg_load_combinations(snapshot)
                snapshot['GZG_Lastfallkombinationen'] = gzg_result['GZG_Lastfallkombinationen']

                feebb_result = add_section_forces(snapshot)
                snapshot['Schnittgroessen'] = feebb_result['Schnittgroessen']

                ec5_result = add_ec5_verification(snapshot)
                snapshot['EC5_Nachweise'] = ec5_result

                result = {
                    'Lastfallkombinationen': kombi_result['Lastfallkombinationen'],
                    'GZG_Lastfallkombinationen': gzg_result['GZG_Lastfallkombinationen'],
                    'Schnittgroessen': feebb_result['Schnittgroessen'],
                    'EC5_Nachweise': ec5_result
                }
                # Debug-Ausgabe vor Callback
                print(
                    f"🚀 Orchestrator: Rufe Callback auf mit result keys: {list(result.keys())}")
                print(
                    f"🚀 EC5_Nachweise keys: {list(result['EC5_Nachweise'].keys())}")
                # Beide Argumente an den Callback übergeben
                callback(result=result, errors=None)
                print(f"✅ Orchestrator: Callback erfolgreich aufgerufen")
            except Exception as e:
                # Debug-Ausgabe für Exception
                print(f"❌ Orchestrator Exception: {e}")
                print(f"❌ Exception Type: {type(e).__name__}")
                import traceback
                print(f"❌ Traceback: {traceback.format_exc()}")
                # Beide Argumente an den Callback übergeben
                callback(result=None, errors=[str(e)])
            finally:
                # Nach der Berechnung Snapshot löschen
               # delete_snapshot(snapshot)
                self._running = False

        threading.Thread(target=worker, daemon=True).start()
