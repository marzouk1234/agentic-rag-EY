from pathlib import Path

from pypdf import PdfReader

BASE_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def list_pdf_files(raw_dir: Path) -> list[Path]:
    return sorted(
        (
            path
            for path in raw_dir.iterdir()
            if path.is_file() and path.suffix.lower() == ".pdf"
        ),
        key=lambda path: path.name.lower(),
    )


import re


def extract_text_from_pdf(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    full_text = []

    for page_number, page in enumerate(reader.pages, start=1):
        # Use layout mode to preserve word spaces in complex PDF layouts/fonts
        text = page.extract_text(extraction_mode="layout")

        if text and text.strip():
            # Clean up null bytes from ligature conversion errors
            text = text.replace("\u0000", "")
            # Collapse consecutive horizontal spaces
            text = re.sub(r'[ \t]+', ' ', text)
            # Collapse consecutive newlines
            text = re.sub(r'\n\s*\n+', '\n\n', text)
            # Remove leading/trailing spaces from each line
            text = "\n".join(line.strip() for line in text.splitlines())
            
            full_text.append(f"\n\n--- Page {page_number} ---\n{text}")

    return "\n".join(full_text).strip()


def ingest_pdfs() -> None:
    pdf_files = list_pdf_files(RAW_DIR)

    if not pdf_files:
        print("Aucun PDF trouve dans data/raw")
        return

    print(f"{len(pdf_files)} PDF trouves")

    extracted_count = 0
    empty_count = 0
    error_count = 0

    for pdf_file in pdf_files:
        print(f"Traitement : {pdf_file.name}")

        try:
            text = extract_text_from_pdf(pdf_file)

            if not text:
                empty_count += 1
                print(f"Avertissement : aucun texte extrait pour {pdf_file.name}")
                continue

            output_file = PROCESSED_DIR / f"{pdf_file.stem}.txt"
            output_file.write_text(text, encoding="utf-8")
            extracted_count += 1

            print(f"Texte sauvegarde : {output_file.name}")

        except Exception as exc:
            error_count += 1
            print(f"ERREUR : {pdf_file.name}")
            print(exc)

    print("Ingestion terminee")
    print(f"Textes extraits : {extracted_count}")
    print(f"PDF sans texte exploitable : {empty_count}")
    print(f"PDF en erreur : {error_count}")


if __name__ == "__main__":
    ingest_pdfs()
