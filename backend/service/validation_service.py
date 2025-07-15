from typing import List, Dict


def validate_input(snapshot: Dict) -> List[str]:
    """
    Validiert den Eingabe-Snapshot und gibt eine Liste von Fehlermeldungen zurück.
    """
    errors: List[str] = []

    # Prüfe Sprungmaß nur bei Eingabe
    sprung = snapshot.get("sprungmass")
    if sprung not in (None, ""):
        try:
            val = float(sprung)
            if val < 0:
                errors.append("Sprungmaß darf nicht negativ sein.")
        except (TypeError, ValueError):
            errors.append("Sprungmaß ist ungültig.")

    # Prüfe Lasten nur wenn Wert gesetzt
    for i, lf in enumerate(snapshot.get("lasten", []), start=1):
        wert = lf.get("wert")
        if wert not in (None, ""):
            try:
                w = float(wert)
                if w <= 0:
                    errors.append(f"Wert für Lastfall {i} muss >0 sein.")
            except (TypeError, ValueError):
                errors.append(f"Wert für Lastfall {i} ist ungültig.")

    # # Prüfe Querschnitt
    # qs = snapshot.get("querschnitt")
    # if not qs or not qs.get("E"):
    #     errors.append("Querschnittdaten fehlen.")

    # # Prüfe Spannweiten
    # spans = snapshot.get("spannweiten", {})
    # if not spans:
    #     errors.append("Spannweiten fehlen.")

    return errors
