'''Datenbankabfrage und -verarbeitung zur Weitergabe an Unterprogramme'''

import pandas as pd
from dataclasses import dataclass
import sys
import os
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..')))
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
class Kmod:
    typ: str
    nkl: int
    kmod_typ: dict  # {"ständig": ..., "lang": ..., ...}
    kdef: float


@dataclass
class SiBeiwerte:
    kategorie: str
    psi0: float
    psi1: float
    psi2: float
    kled: str
    lastfall: str

# Excel-Datenbank einlesen


class datenbank_holz_class:
    def __init__(self):
        basispfad = os.path.dirname(os.path.abspath(__file__))
        excelpfad = os.path.join(basispfad, "datenbank_dlt.xlsx")
        # (Gruppe, Typ, Klasse) → Materialdaten
        self.materialien = {}
        self.kmod = {}                      # (Typ, NKL) → KmodWerte
        self.si_beiwerte = {}               # Kategorie → SiBeiwerte
        self.kategorien_reihenfolge = []    # Reihenfolge der Lastkategorien

        self.lade_materialien(excelpfad)
        self.lade_kmod(excelpfad)
        self.lade_si_beiwerte(excelpfad)

    # Lade Sicherheitsbeiwerte

    def lade_si_beiwerte(self, pfad):
        df = pd.read_excel(pfad, sheet_name="si_beiwerte")

        self.lastfall_reihenfolge = []
        self.kategorien_pro_lastfall = {}

        for _, row in df.iterrows():
            kategorie = row["Kategorie"]
            lastfall = row["Lastfall"]

            self.si_beiwerte[kategorie] = SiBeiwerte(
                kategorie=kategorie,
                psi0=row["psi0"],
                psi1=row["psi1"],
                psi2=row["psi2"],
                kled=row["KLED"],
                lastfall=row["Lastfall"]
            )
            # Reihenfolge merken
            if lastfall not in self.lastfall_reihenfolge:
                self.lastfall_reihenfolge.append(lastfall)

            # Gruppierung aufbauen
            if lastfall not in self.kategorien_pro_lastfall:
                self.kategorien_pro_lastfall[lastfall] = []

            if kategorie not in self.kategorien_pro_lastfall[lastfall]:
                self.kategorien_pro_lastfall[lastfall].append(kategorie)

    # Lade NKL-Kmod-Werte

    def lade_kmod(self, pfad):
        df = pd.read_excel(pfad, sheet_name="nkl_kmod")

        for _, row in df.iterrows():
            typ = row["Typ"]
            nkl = int(row["NKL"])

            kmod_typ = {
                "ständig": row["ständig"],
                "lang": row["lang"],
                "mittel": row["mittel"],
                "kurz": row["kurz"],
                "kurz/sehr kurz": row["kurz/sehr kurz"],
                "sehr kurz": row["sehr kurz"]
            }

            self.kmod[(typ, nkl)] = Kmod(
                typ=typ,
                nkl=nkl,
                kmod_typ=kmod_typ,
                kdef=row["kdef"]
            )

    # Lade Materialdaten
    def lade_materialien(self, pfad):
        df = pd.read_excel(pfad, sheet_name="materials")

        self.typ_reihenfolge = {}
        self.festigkeitsklasse_reihenfolge = {}

        for _, row in df.iterrows():
            gruppe = row["Materialgruppe"]
            typ = row["Typ"]
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

            # Typ Reihenfolge erfassen
            if gruppe not in self.typ_reihenfolge:
                self.typ_reihenfolge[gruppe] = []

            if typ not in self.typ_reihenfolge[gruppe]:
                self.typ_reihenfolge[gruppe].append(typ)

            # Festigkeitsklasse Reihenfolge erfassen
            key_klass = (gruppe, typ)
            if key_klass not in self.festigkeitsklasse_reihenfolge:
                self.festigkeitsklasse_reihenfolge[key_klass] = []

            if klasse not in self.festigkeitsklasse_reihenfolge[key_klass]:
                self.festigkeitsklasse_reihenfolge[key_klass].append(klasse)

    def get_bemessungsdaten(self, gruppe, typ, klasse, nkl, kmod_typ):
        mat = self.get_material(gruppe, typ, klasse)
        kmod_entry = self.get_kmod(typ, nkl)

        if not mat or not kmod_entry:
            return {"fmyk": None, "fvk": None, "E": None, "roh": None, "gamma_m": None, "kmod": None, "kdef": None}

        return {
            "fmyk": mat.fmyk,
            "fvk": mat.fvk,
            "E": mat.emodul,
            "roh": mat.roh,
            "gamma_m": mat.gamma_m,
            "kmod": kmod_entry.kmod_typ.get(kmod_typ, None),
            "kdef": kmod_entry.kdef
        }

    # Allgemeine Zugriffsmethoden
    # Zugriffsmethode Materialien
    def get_material(self, gruppe: str, typ: str, festigkeitsklasse: str) -> Materialdaten | None:
        key = (gruppe, typ, str(festigkeitsklasse))
        return self.materialien.get(key)

    def get_emodul(self, gruppe: str, typ: str, festigkeitsklasse: str) -> float | None:
        key = (gruppe, typ, str(festigkeitsklasse))
        daten = self.materialien.get(key)
        if daten:
            # oder daten["E"], je nachdem wie deine Struktur aussieht
            return daten.emodul
        return None

    # Zugriffsmethode Kmod-Werte

    def get_kmod(self, typ: str, nkl: int) -> Kmod | None:
        return self.kmod.get((typ, nkl), None)

    def get_kmod_und_kdef(self, typ: str, nkl: int, kmod_typ: str) -> tuple[float, float]:
        eintrag = self.get_kmod(typ, nkl)
        if eintrag:
            kmod = eintrag.kmod.get(kmod_typ, None)
            kdef = eintrag.kdef
            return kmod, kdef
        return None, None

    # Zugriffsmethode Sicherheitsbeiwerte

    def get_si_beiwerte(self, kategorie: str) -> SiBeiwerte | None:
        return self.si_beiwerte.get(kategorie)

    # Zugriffsmethode Lastfälle
    def get_sortierte_lastfaelle(self) -> list[str]:
        return self.lastfall_reihenfolge

    # Zugriffsmethode Lastkategorien
    def get_kategorien_fuer_lastfall(self, lastfall: str) -> list[str]:
        return self.kategorien_pro_lastfall.get(lastfall, [])

    # Zugriffsmethode Materialgruppen
    def get_materialgruppen(self) -> list[str]:
        return sorted(set(gruppe for gruppe, _, _ in self.materialien))

    # Zugriffsmethode Materialtypen
    def get_typen(self, gruppe: str) -> list[str]:
        return self.typ_reihenfolge.get(gruppe, [])

    # Zugriffsmethode Festigkeitsklassen
    def get_festigkeitsklassen(self, gruppe: str, typ: str) -> list[str]:
        return self.festigkeitsklasse_reihenfolge.get((gruppe, typ), [])


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
