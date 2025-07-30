import logging

logger = logging.getLogger(__name__)


class FrontendOrchestrator:
    def __init__(self, system_anzeiger, kombi_anzeiger, nachweis_anzeiger):
        self.system_anzeiger = system_anzeiger
        self.kombi_anzeiger = kombi_anzeiger
        self.nachweis_anzeiger = nachweis_anzeiger
        self.busy = False
        self.pending_args = None
        self.current_update_id = 0

        # Status-Tracking für bessere Überwachbarkeit
        self.current_phase = "idle"  # idle, system, kombis, nachweise
        self.last_error = None

    def update_all(self, snapshot, lastkombis):
        """
        Startet den sequenziellen Update-Prozess:
        1. System-Anzeige
        2. Lastkombinations-Anzeige  
        3. EC5-Nachweise-Anzeige
        """
        self.current_update_id += 1
        update_id = self.current_update_id
        self.last_error = None

        logger.info(f"🔄 Starte Orchestrator-Update #{update_id}")

        # Wenn bereits ein Update läuft, speichere die neuen Argumente
        if self.busy:
            logger.debug(
                f"⏳ Update #{update_id} wartet - vorheriges Update läuft noch")
            self.pending_args = (snapshot, lastkombis)
            return

        self.busy = True
        self.current_phase = "system"

        # Phase 1: System-Anzeige aktualisieren
        logger.debug(f"📊 Phase 1: System-Update startet (#{update_id})")
        self.system_anzeiger.update(
            snapshot,
            callback=lambda success=True: self._on_system_done(
                snapshot, lastkombis, update_id, success)
        )

    def _on_system_done(self, snapshot, lastkombis, update_id, success=True):
        """Callback nach System-Update - startet Lastkombinations-Update"""
        if self._is_outdated(update_id):
            logger.debug(
                f"🚫 System-Update #{update_id} ist veraltet - überspringe")
            self._handle_outdated_update()
            return

        if not success:
            logger.error(f"❌ System-Update #{update_id} fehlgeschlagen")
            self.last_error = "System-Update fehlgeschlagen"
            self._finish_update(update_id, success=False)
            return

        logger.debug(
            f"✅ Phase 1 abgeschlossen - starte Phase 2: Lastkombis (#{update_id})")
        self.current_phase = "kombis"

        # Phase 2: Lastkombinations-Anzeige aktualisieren
        self.kombi_anzeiger.update(
            lastkombis,
            callback=lambda success=True: self._on_kombi_done(
                snapshot, lastkombis, update_id, success)
        )

    def _on_kombi_done(self, snapshot, lastkombis, update_id, success=True):
        """Callback nach Lastkombinations-Update - startet EC5-Nachweise-Update"""
        if self._is_outdated(update_id):
            logger.debug(
                f"🚫 Kombi-Update #{update_id} ist veraltet - überspringe")
            self._handle_outdated_update()
            return

        if not success:
            logger.error(f"❌ Kombi-Update #{update_id} fehlgeschlagen")
            self.last_error = "Lastkombinations-Update fehlgeschlagen"
            self._finish_update(update_id, success=False)
            return

        logger.debug(
            f"✅ Phase 2 abgeschlossen - starte Phase 3: EC5-Nachweise (#{update_id})")
        self.current_phase = "nachweise"

        # Phase 3: EC5-Nachweise direkt aus Snapshot anzeigen
        try:
            # EC5-Nachweise direkt aus dem Snapshot extrahieren (ohne system_memory)
            ec5_result = snapshot.get("EC5_Nachweise", {})

            # ec5_result enthält bereits die Nachweise direkt (nicht in einem "nachweise" Feld)
            nachweise_data = ec5_result

            if not nachweise_data:
                logger.warning(
                    f"⚠️ Keine EC5-Nachweise im Snapshot gefunden (#{update_id})")
                logger.warning(
                    f"Verfügbare Snapshot keys: {list(snapshot.keys())}")
                logger.warning(f"EC5_Nachweise Inhalt: {ec5_result}")
                # Nicht als Fehler werten - Backend-Nachweise können optional sein
                self._finish_update(update_id, success=True)
                return

            # Nachweise anzeigen
            self.nachweis_anzeiger.update(
                nachweise_data,
                callback=lambda success=True: self._on_nachweise_done(
                    update_id, success)
            )

        except Exception as e:
            logger.error(f"❌ Fehler bei EC5-Nachweisen #{update_id}: {e}")
            self.last_error = f"EC5-Nachweise fehlgeschlagen: {str(e)}"
            self._finish_update(update_id, success=False)

    def _on_nachweise_done(self, update_id, success=True):
        """Callback nach EC5-Nachweise-Update - Orchestrator-Prozess abgeschlossen"""
        if self._is_outdated(update_id):
            logger.debug(
                f"🚫 Nachweise-Update #{update_id} ist veraltet - überspringe")
            self._handle_outdated_update()
            return

        if not success:
            logger.error(f"❌ Nachweise-Update #{update_id} fehlgeschlagen")
            self.last_error = "EC5-Nachweise-Update fehlgeschlagen"
        else:
            logger.info(
                f"🎉 Orchestrator-Update #{update_id} erfolgreich abgeschlossen")

        self._finish_update(update_id, success)

    def _finish_update(self, update_id, success=True):
        """Beendet den Update-Prozess und startet ggf. wartende Updates"""
        self.current_phase = "idle"
        self.busy = False

        if success:
            logger.debug(f"✅ Update #{update_id} erfolgreich beendet")
        else:
            logger.warning(
                f"⚠️ Update #{update_id} mit Fehlern beendet: {self.last_error}")

        # Wartende Updates starten
        if self.pending_args is not None:
            args = self.pending_args
            self.pending_args = None
            logger.debug("🔄 Starte wartendes Update")
            self.update_all(*args)

    def _handle_outdated_update(self):
        """Behandelt veraltete Updates"""
        self.busy = False
        self.current_phase = "idle"

        if self.pending_args:
            args = self.pending_args
            self.pending_args = None
            self.update_all(*args)

    def _is_outdated(self, update_id):
        """Prüft ob ein Update-Prozess veraltet ist"""
        return update_id != self.current_update_id

    def get_status(self):
        """Gibt den aktuellen Status des Orchestrators zurück"""
        return {
            "busy": self.busy,
            "current_phase": self.current_phase,
            "current_update_id": self.current_update_id,
            "has_pending": self.pending_args is not None,
            "last_error": self.last_error
        }

    def clear_all(self):
        """Löscht alle Anzeigen - nützlich bei Reset oder Fehlern"""
        logger.info("🧹 Lösche alle Anzeigen")
        try:
            self.system_anzeiger.clear() if hasattr(self.system_anzeiger, 'clear') else None
            self.kombi_anzeiger.clear() if hasattr(self.kombi_anzeiger, 'clear') else None
            self.nachweis_anzeiger.clear() if hasattr(
                self.nachweis_anzeiger, 'clear') else None
        except Exception as e:
            logger.error(f"Fehler beim Löschen der Anzeigen: {e}")

    def force_stop(self):
        """Stoppt alle laufenden Updates - Notfall-Funktion"""
        logger.warning("🛑 Orchestrator wird zwangsweise gestoppt")
        self.busy = False
        self.current_phase = "idle"
        self.pending_args = None
        self.current_update_id += 1  # Macht alle laufenden Updates ungültig
