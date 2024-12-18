import time
import sys

def parse_adif_record(record):
    """
    Parse un enregistrement ADIF (une string contenant un QSO complet)
    et retourne un tuple (year, band, call).
    """
    # Exemple de record:
    # "<CALL:5>F5ABC <QSO_DATE:8>20231012 <BAND:3>20m <EOR>"
    # Nous allons rechercher les champs par split ou via une méthode plus robuste.
    # Une méthode simple consiste à rechercher par exemple "<CALL:", "<BAND:", "<QSO_DATE:" etc.
    # Pour plus de robustesse, on peut utiliser un parsing par expressions régulières.
    
    import re
    
    # Regex pour extraire les champs
    call_match = re.search(r"<CALL:\d+>([^ <]+)", record, re.IGNORECASE)
    band_match = re.search(r"<BAND:\d+>([^ <]+)", record, re.IGNORECASE)
    date_match = re.search(r"<QSO_DATE:\d+>(\d{4})", record, re.IGNORECASE)
    # On extrait juste l'année (les 4 premiers caractères du QSO_DATE suffisent)
    
    call = call_match.group(1).upper() if call_match else None
    band = band_match.group(1).lower() if band_match else None
    year = date_match.group(1) if date_match else None

    return year, band, call


def main():
    filename = "test.adif"  # A adapter
    
    start_time = time.time()

    # Structure de données:
    # data = {year: {band: set_of_calls}}
    from collections import defaultdict
    data = defaultdict(lambda: defaultdict(set))

    # Lecture du fichier ligne par ligne
    # Accumulation des lignes jusqu'au EOR
    current_record_lines = []
    with open(filename, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if line:
                current_record_lines.append(line)
                # Si on détecte <EOR>, on traite l'enregistrement
                if "<EOR>" in line.upper():
                    record = " ".join(current_record_lines)
                    # Parse l'enregistrement
                    year, band, call = parse_adif_record(record)
                    if year and band and call:
                        data[year][band].add(call)
                    current_record_lines = []

    end_time = time.time()
    processing_time = end_time - start_time

    # Affichage du temps de traitement
    print(f"Temps total de traitement: {processing_time:.4f} secondes")

    # Affichage du nombre de contacts uniques par année et par bande
    for year in sorted(data.keys()):
        print(f"Année {year}:")
        for band in sorted(data[year].keys()):
            print(f"  Bande {band}: {len(data[year][band])} unique callsigns")

    # Taille en mémoire du dictionnaire
    size_in_bytes = sys.getsizeof(data)
    print(f"Taille du dictionnaire en mémoire: {size_in_bytes} octets")

    annee_test = "2023"
    bande_test = "6m"
    call_test = "F4BKV"

    if call_test in data[annee_test][bande_test]:
        print(f"L'indicatif {call_test} est déjà présent pour l'année {annee_test} et la bande {bande_test}.")
    else:
        print(f"L'indicatif {call_test} n'est pas présent pour l'année {annee_test} et la bande {bande_test}.")

    # Méthode pour vérifier si un indicatif est présent sur l'ensemble des années
    # Il suffit de parcourir toutes les années et bandes:
    call_present_global = any(call_test in band_set for year_bands in data.values() for band_set in year_bands.values())
    if call_present_global:
        print(f"L'indicatif {call_test} est présent sur au moins une année.")
    else:
        print(f"L'indicatif {call_test} n'est présent sur aucune année.")


if __name__ == "__main__":
    main()
