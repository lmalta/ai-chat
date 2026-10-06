from pathlib import Path

from documents import extract_pdf
from documents_excel import extract_excel


SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".xlsx",
}


def load_document(document_path):
    """
    Charge un document et utilise l'extracteur adapté.

    Formats actuellement supportés :
        - PDF
        - XLSX

    Retourne un dictionnaire standardisé.
    """

    document_path = Path(document_path)

    if not document_path.exists():
        raise FileNotFoundError(
            f"Document introuvable : {document_path}"
        )

    extension = document_path.suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Format non supporté : {extension}"
        )

    if extension == ".pdf":
        result = extract_pdf(document_path)

        return {
            "filename": document_path.name,
            "extension": extension,
            "type": result["type"],
            "pages": result["pages"],
            "text": result["text"],
        }

    if extension == ".xlsx":
        result = extract_excel(document_path)

        return {
            "filename": document_path.name,
            "extension": extension,
            "type": result["type"],
            "sheets": result["sheets"],
            "text": result["text"],
        }

    raise ValueError(
        f"Extracteur non disponible pour : {extension}"
    )