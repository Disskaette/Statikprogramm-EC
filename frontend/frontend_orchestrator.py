class FrontendOrchestrator:
    def __init__(self, system_anzeiger, kombi_anzeiger):
        self.system_anzeiger = system_anzeiger
        self.kombi_anzeiger = kombi_anzeiger
        self.busy = False
        self.pending_args = None
        self.current_update_id = 0

    def update_all(self, snapshot, lastkombis):
        self.current_update_id += 1
        update_id = self.current_update_id

        if self.busy:
            self.pending_args = (snapshot, lastkombis)
            return
        self.busy = True
        self.system_anzeiger.update(
            snapshot,
            callback=lambda: self._on_system_done(lastkombis, update_id)
        )

    def _on_system_done(self, lastkombis, update_id):
        if self._is_outdated(update_id):
            self.busy = False  # Freigeben für die nächste, aktuellere Berechnung
            if self.pending_args:
                args = self.pending_args
                self.pending_args = None
                self.update_all(*args)
            return  # Diesen veralteten Zweig hier abbrechen

        self.kombi_anzeiger.update(
            lastkombis,
            callback=lambda: self._on_kombi_done(update_id)
        )

    def _on_kombi_done(self, update_id):
        # Auch hier prüfen, falls der letzte Schritt sehr lange gedauert hat
        if self._is_outdated(update_id):
            self.busy = False  # Freigeben
            # Hier nicht erneut update_all aufrufen, das passiert schon in _on_system_done
            return

        self.busy = False
        if self.pending_args is not None:
            args = self.pending_args
            self.pending_args = None
            self.update_all(*args)

    def _is_outdated(self, update_id):
        return update_id != self.current_update_id
