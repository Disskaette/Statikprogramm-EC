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
        if self._running:
            # Berechnung läuft bereits - ignorieren
            print("⏭️ Orchestrator: Überspringe (läuft bereits)")
            return
            
        if (now - self._last_time) < self.debounce:
            # Debounce - Callback aufrufen damit Ladeanimation stoppt
            print("⏭️ Orchestrator: Überspringe (debounce)")
            callback(result=None, errors=None)
            return

        # Hash nur von strukturellen Daten berechnen (calculation_mode ausschließen)
        # Bei only_deflection_check sollen Gebrauchstauglichkeits-Änderungen durchgehen
        calculation_mode = snapshot.get('calculation_mode', 'full')
        hash_data = {k: v for k, v in snapshot.items() if k != 'calculation_mode'}
        current_hash = self._compute_hash(hash_data)
        
        # Bei Durchbiegungsprüfung Hash nicht vergleichen (soll immer durchlaufen)
        if calculation_mode != 'only_deflection_check' and current_hash == self._last_hash:
            # Hash ist gleich - keine Neuberechnung nötig, aber Callback aufrufen
            print("⏭️ Orchestrator: Keine Änderung erkannt (gleicher Hash)")
            # Callback mit leeren Ergebnis aufrufen, damit Frontend weiß, dass nichts zu tun ist
            # Das Frontend sollte die bestehenden Ergebnisse behalten
            callback(result=None, errors=None)
            return

        self._running = True
        self._last_hash = current_hash
        self._last_time = now

        def worker():
            try:
                # Prüfe, ob nur Durchbiegungsnachweise neu berechnet werden sollen
                calculation_mode = snapshot.get('calculation_mode', 'full')
                
                if calculation_mode == 'only_deflection_check':
                    # Nur EC5-Nachweise neu berechnen (Schnittgrößen sind bereits vorhanden)
                    print("🔄 Orchestrator: Nur Durchbiegungsnachweise werden berechnet")
                    
                    # EC5-Nachweise mit bestehenden Daten
                    ec5_result = add_ec5_verification(snapshot)
                    
                    # Bestehende Ergebnisse übernehmen
                    result = {
                        'Lastfallkombinationen': snapshot.get('Lastfallkombinationen', {}),
                        'GZG_Lastfallkombinationen': snapshot.get('GZG_Lastfallkombinationen', {}),
                        'Schnittgroessen': snapshot.get('Schnittgroessen', {}),
                        'EC5_Nachweise': ec5_result
                    }
                else:
                    # Vollständige Berechnung (Standard)
                    print("🚀 Orchestrator: Vollständige Berechnung")
                    
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
                # print(
                #     f"🚀 Orchestrator: Rufe Callback auf mit result keys: {list(result.keys())}")
                # print(
                #     f"🚀 EC5_Nachweise keys: {list(result['EC5_Nachweise'].keys())}")
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
