"""
Entry Point für Statikprogramm v2.0
Neue modulare Architektur mit Projekt- und Positions-Management.
"""

import sys
import logging
from pathlib import Path

# Projekt-Root zum Python-Path hinzufügen
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Logging konfigurieren
logging.basicConfig(
    level=logging.DEBUG,  # DEBUG für Entwicklung, INFO für Produktion
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)

# Matplotlib/PIL Logging reduzieren
logging.getLogger("PIL.PngImagePlugin").setLevel(logging.WARNING)
logging.getLogger("matplotlib.font_manager").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def register_modules():
    """Registriert alle verfügbaren Module"""
    from frontend.modules.module_registry import get_registry
    from frontend.modules.modul_durchlauftraeger import ModulDurchlauftraeger
    # from frontend.modules.modul_durchlauftraeger_simple import ModulDurchlauftraegerSimple
    
    registry = get_registry()
    
    # Durchlaufträger-Modul (vollständig mit Eingabemaske)
    registry.register_module(
        ModulDurchlauftraeger,
        enabled=True,
        order=1,
        category="Berechnungen"
    )
    
    # Weitere Module können hier hinzugefügt werden:
    # registry.register_module(ModulBrandschutz, enabled=False, order=2)
    # registry.register_module(ModulAuflager, enabled=False, order=3)
    
    logger.info(f"{len(registry.get_all_modules())} Module registriert")


def main():
    """Hauptfunktion"""
    print("=" * 60)
    print("🏗️  STATIKPROGRAMM V2.0")
    print("=" * 60)
    print()
    
    try:
        # Module registrieren
        register_modules()
        
        # Hauptfenster starten
        from frontend.gui.main_window import start_application
        start_application()
        
    except Exception as e:
        logger.error(f"Fataler Fehler: {e}", exc_info=True)
        import tkinter.messagebox as mb
        mb.showerror("Fehler", f"Anwendung konnte nicht gestartet werden:\n{e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
