'''Datenbankabfrage und -verarbeitung zur Weitergabe an Unterprogramme'''

import pandas as pd
from dataclasses import dataclass
import os

# Definition der Dataclasses


@dataclass
class Materialdaten:
    gruppe: str
    typ: str
    festigkeitsklasse: str
    fmyk: float              # Biegung
    fc90k: float             # Druck rechtwinklig
    fvk: float               # Schub
    emodul: float            # E-Modul (Biegung 0°)
    roh: float               # charakteristische Rohdichte rk
    roh_mean: float          # mittlere Rohdichte
    gamma_m: float = 1.3     # Standardwert, wenn nicht angegeben


@dataclass
class KmodWerte:
    typ: str
    nkl: int
    kmod: dict  # {"ständig": ..., "lang": ..., ...}
    kdef: float


@dataclass
class SiBeiwerte:
    kategorie: str
    psi0: float
    psi1: float
    psi2: float
    kled: str

# Excel-Datenbank einlesen


class Datenbank_holz_class:
    def __init__(self):
        basispfad = os.path.dirname(os.path.abspath(__file__))
        excelpfad = os.path.join(basispfad, "datenbank_dlt.xlsx")
        self.materialien = {}       # (Gruppe, Typ, Klasse) → Materialdaten
        self.kmod_werte = {}        # (Typ, NKL) → KmodWerte
        self.si_beiwerte = {}       # Kategorie → SiBeiwerte

        self.lade_materialien(excelpfad)
        self.lade_kmod(excelpfad)
        self.lade_si_beiwerte(excelpfad)

    # Lade Sicherheitsbeiwerte

    def lade_si_beiwerte(self, pfad):
        df = pd.read_excel(pfad, sheet_name="si_beiwerte")

        for _, row in df.iterrows():
            self.si_beiwerte[row["Kategorie"]] = SiBeiwerte(
                kategorie=row["Kategorie"],
                psi0=row["psi0"],
                psi1=row["psi1"],
                psi2=row["psi2"],
                kled=row["KLED"]
            )

    # Lade NKL-Kmod-Werte
    def lade_kmod(self, pfad):
        df = pd.read_excel(pfad, sheet_name="nkl_kmod")

        for _, row in df.iterrows():
            typ = row["Typ"]
            nkl = int(row["NKL"])

            kmod_map = {
                "ständig": row["ständig"],
                "lang": row["lang"],
                "mittel": row["mittel"],
                "kurz": row["kurz"],
                "kurz/sehr kurz": row["kurz/sehr kurz"],
                "sehr kurz": row["sehr kurz"]
            }

            self.kmod_werte[(typ, nkl)] = KmodWerte(
                typ=typ,
                nkl=nkl,
                kmod=kmod_map,
                kdef=row["kdef"]
            )

    # Lade Materialdaten
    def lade_materialien(self, pfad):
        df = pd.read_excel(pfad, sheet_name="materials")

        for _, row in df.iterrows():
            gruppe = row["Materialgruppe"]
            typ = row["Typ"]
            # als string (auch „t = 18“ etc.)
            klasse = str(row["Festigkeitsklasse"])

            if pd.isna(gruppe) or pd.isna(typ) or pd.isna(klasse):
                continue    # Überspringe Zeilen mit fehlenden Werten

            key = (gruppe, typ, klasse)

            self.materialien[key] = Materialdaten(
                gruppe=gruppe,
                typ=typ,
                festigkeitsklasse=klasse,
                fmyk=row["Biegung"],
                fc90k=row["Druck rechtwinklig zur Faserrichtung"],
                fvk=row["Schub"],
                emodul=row["Elastizitätsmodul Biegung 0° - Mittelwert"],
                roh=row["Rohdichte"],
                roh_mean=row["Rohdichte - Mittelwert"],
                gamma_m=row.get("γM", 1.3)  # optional (falls später ergänzt)
            )
    # Allgemeine Zugriffsmethoden
    # Zugriffsmethode Materialien

    def get_material(self, gruppe: str, typ: str, festigkeitsklasse: str) -> Materialdaten | None:
        key = (gruppe, typ, str(festigkeitsklasse))
        return self.materialien.get(key)

    # Zugriffsmethode Kmod-Werte
    def get_kmod(self, typ: str, nkl: int) -> KmodWerte | None:
        key = (typ, nkl)
        return self.kmod_werte.get(key)

    # Zugriffsmethode Sicherheitsbeiwerte
    def get_si_beiwerte(self, kategorie: str) -> SiBeiwerte | None:
        return self.si_beiwerte.get(kategorie)

    # Zugriffsmethode Materialgruppen
    def get_materialgruppen(self) -> list[str]:
        return sorted(set(gruppe for gruppe, _, _ in self.materialien))

    # Zugriffsmethode Materialtypen
    def get_typen(self, gruppe: str) -> list[str]:
        return sorted(set(typ for g, typ, _ in self.materialien if g == gruppe))

    # Zugriffsmethode Festigkeitsklassen
    def get_festigkeitsklassen(self, gruppe: str, typ: str) -> list[str]:
        return sorted(set(fk for g, t, fk in self.materialien if g == gruppe and t == typ))


# if __name__ == "__main__":
#     db = Datenbank()

#     print("\n✅ Datenbank erfolgreich geladen!\n")

#     # --- Test: Materialdaten ---
#     print("🔍 Beispiel-Material:")
#     key = ("Balken", "Nadelholz", "C24")
#     if key in db.materialien:
#         print("Materialdaten gefunden:", db.materialien[key])
#     else:
#         print("❌ Materialdaten fehlen:", key)

#     # --- Test: Kmod-Werte ---
#     print("\n🔍 Beispiel-Kmod:")
#     key = ("Nadelholz", 1)
#     if key in db.kmod_werte:
#         print("Kmod-Daten gefunden:", db.kmod_werte[key])
#     else:
#         print("❌ Kmod-Daten fehlen:", key)

#     # --- Test: si_beiwerte ---
#     print("\n🔍 Beispiel-Sicherheitsbeiwerte:")
#     key = "Nutzlast Kat. A: Wohnraum"
#     if key in db.si_beiwerte:
#         print("Si-Beiwerte gefunden:", db.si_beiwerte[key])
#     else:
#         print("❌ Si-Beiwerte fehlen:", key)

#     # --- Test: Zugriffsmethoden ---
#     print("\n✅ Zugriffsmethoden-Test")

#     mat = db.get_material("Balken", "Nadelholz", "C24")
#     print("Material:", mat)

#     kmod = db.get_kmod("Nadelholz", 2)
#     print("Kmod:", kmod)

#     psi = db.get_si_beiwerte("Nutzlast Kat. A: Wohnraum")
#     print("Sicherheitsbeiwerte:", psi)

#     # Gruppentest
#     print("\nMaterialgruppen:", db.get_materialgruppen())
#     print("Typen für 'Balken':", db.get_typen("Balken"))
#     print("Festigkeitsklassen für 'Balken', 'Nadelholz':",
#           db.get_festigkeitsklassen("Balken", "Nadelholz"))
