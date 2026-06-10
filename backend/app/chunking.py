from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter

BASE_DIR = Path(__file__).resolve().parents[2]

PROCESSED_DIR = BASE_DIR / "data" / "processed"
CHUNK_DIR = BASE_DIR / "data" / "chunks"

CHUNK_DIR.mkdir(parents=True, exist_ok=True)

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)


def chunk_documents():

    txt_files = list(PROCESSED_DIR.glob("*.txt"))

    print(f"{len(txt_files)} fichiers trouvés")

    for txt_file in txt_files:

        text = txt_file.read_text(
            encoding="utf-8",
            errors="ignore"
        )

        chunks = splitter.split_text(text)

        output_file = CHUNK_DIR / f"{txt_file.stem}.txt"

        with open(output_file, "w", encoding="utf-8") as f:

            for i, chunk in enumerate(chunks):

                f.write(
                    f"\n===== CHUNK {i} =====\n"
                )

                f.write(chunk)
                f.write("\n")

        print(
            f"{txt_file.name} -> {len(chunks)} chunks"
        )


if __name__ == "__main__":
    chunk_documents()