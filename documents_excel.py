import openpyxl
from pathlib import Path


def extract_excel(excel_path):
    """
    Extrait le contenu d'un fichier Excel (.xlsx).

    Retourne :
        {
            "type": "excel",
            "sheets": int,
            "text": str
        }

    La structure des feuilles, lignes et colonnes est conservée
    afin de fournir un contexte exploitable par un LLM.
    """

    excel_path = Path(excel_path)

    if not excel_path.exists():
        raise FileNotFoundError(
            f"Fichier Excel introuvable : {excel_path}"
        )

    # ---------------------------------------------------------
    # Chargement du classeur
    # ---------------------------------------------------------

    workbook = openpyxl.load_workbook(
        excel_path,
        data_only=False
    )

    extracted_sheets = []

    # ---------------------------------------------------------
    # Parcours des feuilles
    # ---------------------------------------------------------

    for worksheet in workbook.worksheets:

        lines = [
            f"=== Feuille : {worksheet.title} ==="
        ]

        # -----------------------------------------------------
        # Parcours des lignes
        # -----------------------------------------------------

        for row_number, row in enumerate(
            worksheet.iter_rows(),
            start=1
        ):

            values = []

            for cell in row:

                if cell.value is None:
                    continue

                value = str(cell.value).strip()

                if not value:
                    continue

                values.append(
                    f"{cell.column_letter}: {value}"
                )

            # Ignorer complètement les lignes vides
            if not values:
                continue

            lines.append(
                f"Ligne {row_number}:"
            )

            lines.extend(
                f"  {value}"
                for value in values
            )

        extracted_sheets.append(
            "\n".join(lines)
        )

    text = "\n\n".join(extracted_sheets)

    return {
        "type": "excel",
        "sheets": len(workbook.worksheets),
        "text": text
    }