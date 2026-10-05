import os
import subprocess
import tempfile
from pathlib import Path


def extract_pdf(pdf_path):
    """
    Extrait le texte d'un PDF.

    Retourne :
        {
            "type": "text" ou "ocr",
            "pages": int,
            "text": str
        }

    Méthode :
    1. Tentative d'extraction directe avec pdftotext.
    2. Si aucun texte n'est trouvé, OCR avec Tesseract.
    """

    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF introuvable : {pdf_path}")

    # ---------------------------------------------------------
    # Nombre de pages
    # ---------------------------------------------------------

    info = subprocess.run(
        [
            "pdfinfo",
            str(pdf_path)
        ],
        check=True,
        capture_output=True,
        text=True
    )

    pages = None

    for line in info.stdout.splitlines():
        if line.startswith("Pages:"):
            pages = int(line.split(":", 1)[1].strip())
            break

    if pages is None:
        raise RuntimeError(
            "Impossible de déterminer le nombre de pages."
        )

    # ---------------------------------------------------------
    # 1. Tentative d'extraction directe
    # ---------------------------------------------------------

    with tempfile.NamedTemporaryFile(
        suffix=".txt",
        delete=False
    ) as tmp:
        text_path = tmp.name

    try:
        subprocess.run(
            [
                "pdftotext",
                str(pdf_path),
                text_path
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        text = Path(text_path).read_text(
            encoding="utf-8",
            errors="replace"
        ).strip()

    finally:
        if os.path.exists(text_path):
            os.remove(text_path)

    # ---------------------------------------------------------
    # PDF contenant déjà du texte
    # ---------------------------------------------------------

    if text:
        return {
            "type": "text",
            "pages": pages,
            "text": text
        }

    # ---------------------------------------------------------
    # 2. PDF scanné → OCR
    # ---------------------------------------------------------

    with tempfile.TemporaryDirectory() as temp_dir:

        prefix = os.path.join(temp_dir, "page")

        subprocess.run(
            [
                "pdftoppm",
                "-png",
                "-r",
                "300",
                str(pdf_path),
                prefix
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        page_files = sorted(
            Path(temp_dir).glob("page-*.png")
        )

        if not page_files:
            raise RuntimeError(
                "Impossible de convertir les pages du PDF."
            )

        extracted_pages = []

        for page in page_files:

            result = subprocess.run(
                [
                    "tesseract",
                    str(page),
                    "stdout",
                    "-l",
                    "fra"
                ],
                check=True,
                capture_output=True,
                text=True
            )

            page_text = result.stdout.strip()

            if page_text:
                extracted_pages.append(page_text)

        text = "\n\n".join(extracted_pages)

        return {
            "type": "ocr",
            "pages": pages,
            "text": text
        }