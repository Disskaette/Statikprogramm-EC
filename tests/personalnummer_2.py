import pandas as pd
import tkinter as tk
from tkinter import filedialog


def lade_datei(titel):
    root = tk.Tk()
    root.withdraw()
    return filedialog.askopenfilename(title=titel, filetypes=[("Excel files", "*.xlsx *.xls")])


def speichere_datei_neu(df):
    root = tk.Tk()
    root.withdraw()
    pfad = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[(
        "Excel files", "*.xlsx")], title="Speicherort für Ergebnisdatei auswählen")
    if pfad:
        df.to_excel(pfad, index=False)
        print(f"Ergebnis gespeichert unter: {pfad}")


def finde_spalte(df, suchbegriff):
    for spalte in df.columns:
        if suchbegriff.lower() in spalte.lower():
            return spalte
    raise ValueError(f"Spalte mit Begriff '{suchbegriff}' nicht gefunden.")


def personalnummern_abgleichen():
    print("Datei mit allen Mitarbeitern (korrekte Daten) wählen...")
    pfad_alle = lade_datei("Alle Mitarbeiter (5-stellig)")
    print("Datei mit gesammelten Daten (evtl. fehlerhaft) wählen...")
    pfad_gesammelt = lade_datei("Gesammelte Daten")

    df_alle = pd.read_excel(pfad_alle, dtype=str)
    df_gesammelt = pd.read_excel(pfad_gesammelt, dtype=str)

    spalte_pnr_alle = finde_spalte(df_alle, "personalnummer")
    spalte_vn_alle = finde_spalte(df_alle, "vorname")
    spalte_nn_alle = finde_spalte(df_alle, "nachname")

    spalte_pnr_ges = finde_spalte(df_gesammelt, "personalnummer")
    spalte_vn_ges = finde_spalte(df_gesammelt, "vorname")
    spalte_nn_ges = finde_spalte(df_gesammelt, "nachname")

    df_alle[spalte_pnr_alle] = df_alle[spalte_pnr_alle].str.zfill(5)
    df_gesammelt[spalte_pnr_ges] = df_gesammelt[spalte_pnr_ges].str.zfill(5)

    df_alle["full_name"] = df_alle[spalte_vn_alle].str.lower(
    ).str.strip() + " " + df_alle[spalte_nn_alle].str.lower().str.strip()
    df_gesammelt["full_name"] = df_gesammelt[spalte_vn_ges].str.lower(
    ).str.strip() + " " + df_gesammelt[spalte_nn_ges].str.lower().str.strip()

    df_gesammelt["Doppelt"] = df_gesammelt.duplicated(
        subset=[spalte_pnr_ges, "full_name"], keep=False)

    bereits_erfasst = set()
    meldungen = []

    for _, row in df_gesammelt.iterrows():
        pnr = row[spalte_pnr_ges]
        name = row["full_name"]

        if (pnr, name) in bereits_erfasst:
            continue
        bereits_erfasst.add((pnr, name))

        doppel = df_gesammelt[(df_gesammelt[spalte_pnr_ges] == pnr) & (
            df_gesammelt["full_name"] == name)]["Doppelt"].any()
        pnr_match = df_alle[df_alle[spalte_pnr_alle] == pnr]
        name_match = df_alle[df_alle["full_name"] == name]

        korrekt = ""

        if pnr_match.empty and name_match.empty:
            meldung = "In gesammelter Liste, aber nicht in offizieller Liste"
        elif pnr_match.empty:
            meldung = "Name vorhanden, aber Personalnummer stimmt nicht"
            korrekt_eintrag = name_match.iloc[0]
            korrekt = f"{korrekt_eintrag[spalte_pnr_alle]} - {korrekt_eintrag[spalte_vn_alle]} {korrekt_eintrag[spalte_nn_alle]}"
        elif name_match.empty:
            meldung = "Personalnummer vorhanden, aber Name stimmt nicht"
            korrekt_eintrag = pnr_match.iloc[0]
            korrekt = f"{korrekt_eintrag[spalte_pnr_alle]} - {korrekt_eintrag[spalte_vn_alle]} {korrekt_eintrag[spalte_nn_alle]}"
        else:
            meldung = "OK"

        if doppel:
            meldung = "Doppelt in gesammelter Liste"

        if meldung != "OK":
            eintrag = {
                "Personalnummer": pnr,
                "Vorname": row[spalte_vn_ges],
                "Nachname": row[spalte_nn_ges],
                "Problem": meldung
            }
            if "stimmt nicht" in meldung:
                eintrag["Korrekte Zuordnung"] = korrekt
            meldungen.append(eintrag)

    full_names_ges = set(df_gesammelt["full_name"])
    pnr_ges = set(df_gesammelt[spalte_pnr_ges])

    for _, row in df_alle.iterrows():
        pnr = row[spalte_pnr_alle]
        name = row["full_name"]
        if name not in full_names_ges and pnr not in pnr_ges:
            meldungen.append({
                "Personalnummer": pnr,
                "Vorname": row[spalte_vn_alle],
                "Nachname": row[spalte_nn_alle],
                "Problem": "Fehlt komplett in der gesammelten Liste"
            })

    df_result = pd.DataFrame(meldungen)

    # Sortierung nach gewünschter Reihenfolge, zusätzliche Sortierung innerhalb letzter Gruppe nach Personalnummer
    sortierung = [
        "Doppelt in gesammelter Liste",
        "Personalnummer vorhanden, aber Name stimmt nicht",
        "Name vorhanden, aber Personalnummer stimmt nicht",
        "In gesammelter Liste, aber nicht in offizieller Liste",
        "Fehlt komplett in der gesammelten Liste"
    ]
    df_result["Sortierung"] = df_result["Problem"].apply(
        lambda x: sortierung.index(x) if x in sortierung else 99)
    df_result["PNR_SORT"] = df_result["Personalnummer"].astype(str)
    df_result.sort_values(by=["Sortierung", "PNR_SORT"], inplace=True)
    df_result.drop(columns=["Sortierung", "PNR_SORT"], inplace=True)

    speichere_datei_neu(df_result)


if __name__ == "__main__":
    personalnummern_abgleichen()
