from backend.service.memory_service import save_snapshot
from backend.service.validation_service import validate_input
from backend.service.calculation_service import add_load_cases, add_section_forces
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

                feebb_result = add_section_forces(snapshot)
                snapshot['Schnittgroessen'] = feebb_result['Schnittgroessen']
                # querschnitt_result = add_cross_sectional_calculation(snapshot)

                result = {
                    'Lastfallkombinationen': kombi_result['Lastfallkombinationen'],
                    'Schnittgroessen': feebb_result['Schnittgroessen'],
                    # 'Querschnitt_Formeln': querschnitt_result['Querschnitt_Formeln']
                }
                # Beide Argumente an den Callback übergeben
                callback(result=result, errors=None)
            except Exception as e:
                # Beide Argumente an den Callback übergeben
                callback(result=None, errors=[str(e)])
            finally:
                # Nach der Berechnung Snapshot löschen
               # delete_snapshot(snapshot)
                self._running = False

        threading.Thread(target=worker, daemon=True).start()
