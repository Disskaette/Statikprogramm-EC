"""
Wrapper um die Eingabemaske, um sie in einen Frame zu integrieren.
Erstellt einen Mock-Root, der Window-Methoden auf den echten Root weiterleitet.
"""

import tkinter as tk
import logging
from typing import Optional
from frontend.gui.eingabemaske import Eingabemaske
from backend.database.datenbank_holz import datenbank_holz_class

logger = logging.getLogger(__name__)


class MockRoot:
    """
    Mock-Objekt das wie ein Tk-Root aussieht, aber auf einen Frame delegiert.
    Fängt Window-spezifische Methoden ab (title, attributes, etc.).
    """
    
    def __init__(self, real_frame: tk.Frame):
        self._frame = real_frame
        self._real_root = real_frame.winfo_toplevel()  # Echtes Toplevel-Fenster
        self.tk = self._real_root.tk  # tk-Interpreter als Attribut (nicht Methode!)
        
    def title(self, text=None):
        """title() auf echtem Root aufrufen"""
        if text:
            self._real_root.title(text)
    
    def attributes(self, *args, **kwargs):
        """attributes() auf echtem Root aufrufen"""
        return self._real_root.attributes(*args, **kwargs)
    
    def focus_force(self):
        """focus_force() auf echtem Root aufrufen"""
        return self._real_root.focus_force()
    
    def after(self, ms, func=None):
        """after() auf Frame aufrufen"""
        return self._frame.after(ms, func)
    
    def after_cancel(self, id):
        """after_cancel() auf Frame aufrufen"""
        return self._frame.after_cancel(id)
    
    def geometry(self, *args):
        """geometry() ignorieren (Frame hat keine geometry)"""
        pass
    
    def bind(self, *args, **kwargs):
        """bind() auf Frame"""
        return self._frame.bind(*args, **kwargs)
    
    def unbind(self, *args, **kwargs):
        """unbind() auf Frame"""
        return self._frame.unbind(*args, **kwargs)
    
    def update_idletasks(self):
        """update_idletasks() auf Frame"""
        return self._frame.update_idletasks()
    
    # Alle anderen Attribute/Methoden auf Frame delegieren
    def __getattr__(self, name):
        return getattr(self._frame, name)


class EingabemaskeWrapper(Eingabemaske):
    """
    Wrapper um die Eingabemaske für Frame-Integration.
    Nutzt MockRoot um Window-Methoden abzufangen.
    """
    
    def __init__(self, parent: tk.Frame, db: Optional[datenbank_holz_class] = None):
        """
        Args:
            parent: Eltern-Frame (statt root-Fenster)
            db: Optional vorhandene DB-Instanz
        """
        logger.info(f"🔧 EingabemaskeWrapper.__init__ gestartet, parent={parent}")
        
        # Mock-Root erstellen, der auf parent delegiert
        mock_root = MockRoot(parent)
        logger.info(f"🔧 MockRoot erstellt: {mock_root}")
        
        # Originalen __init__ aufrufen mit Mock-Root
        logger.info("🔧 Rufe Eingabemaske.__init__ auf...")
        super().__init__(mock_root)
        logger.info("🔧 Eingabemaske.__init__ abgeschlossen")
        
        # Datenbank überschreiben falls mitgegeben
        if db:
            self.db = db
        
        # Debug: Prüfe, ob Widgets erstellt wurden
        children_count = len(list(parent.winfo_children()))
        logger.info(f"✅ EingabemaskeWrapper initialisiert, {children_count} Widgets in parent")
        
        # Force update
        parent.update_idletasks()
        logger.info("✅ update_idletasks() aufgerufen")
    
    def cleanup(self):
        """Cleanup-Methode für Modul-System"""
        # Schnittkraftfenster schließen falls offen
        if hasattr(self, 'feebb') and self.feebb:
            try:
                self.feebb.close_schnittkraftfenster()
            except:
                pass
        
        logger.debug("EingabemaskeWrapper cleanup abgeschlossen")
