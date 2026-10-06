import openpyxl
from pathlib import Path


def load_excel_rows(excel_path):
    """
    Charge les lignes d'un fichier Excel sous forme structurée.

    Chaque ligne non vide devient un dictionnaire :
        {
            "row": numéro de ligne,
            "distance": valeur,
            "nom": valeur,
            "adresse": valeur,
            "telephone": valeur,
            "prestations": valeur
        }
    """

    excel_path = Path(excel_path)

    if not excel_path.exists():
        raise FileNotFoundError(
            f"Fichier Excel introuvable : {excel_path}"
        )

    workbook = openpyxl.load_workbook(
        excel_path,
        data_only=False
    )

    results = []

    for worksheet in workbook.worksheets:

        for row_number, row in enumerate(
            worksheet.iter_rows(),
            start=1
        ):

            values = {
                cell.column_letter: cell.value
                for cell in row
                if cell.value is not None
            }

            if not values:
                continue

            # Les colonnes de notre fichier de test :
            # B = distance
            # C = nom
            # D = adresse
            # E = téléphone
            # F = prestations

            distance = values.get("B")

            results.append({
                "sheet": worksheet.title,
                "row": row_number,
                "distance": distance,
                "nom": values.get("C"),
                "adresse": values.get("D"),
                "telephone": values.get("E"),
                "prestations": values.get("F"),
            })

    return results


def distance_km(value):
    """
    Convertit une valeur comme '59km' en nombre 59.0.
    Retourne None si la valeur n'est pas exploitable.
    """

    if value is None:
        return None

    text = str(value).strip().lower()
    text = text.replace("km", "").strip()

    try:
        return float(text.replace(",", "."))
    except ValueError:
        return None


def filter_by_distance(rows, max_km, inclusive=False):
    """
    Filtre les établissements selon leur distance.

    Par défaut :
        distance < max_km

    Avec inclusive=True :
        distance <= max_km
    """

    results = []

    for row in rows:

        distance = distance_km(row["distance"])

        if distance is None:
            continue

        if inclusive:
            match = distance <= max_km
        else:
            match = distance < max_km

        if match:
            item = row.copy()
            item["distance_km"] = distance
            results.append(item)

    return results


def search_prestations(rows, keyword):
    """
    Recherche exacte d'un mot ou d'une expression
    dans les prestations.

    La recherche est insensible à la casse.
    """

    keyword = keyword.strip().lower()

    if not keyword:
        return []

    results = []

    for row in rows:

        prestations = row.get("prestations")

        if not prestations:
            continue

        if keyword in str(prestations).lower():
            results.append(row)

    return results