from __future__ import annotations

import argparse
import re
from pathlib import Path

from pypdf import PdfReader


def safe_title(path: Path, reader: PdfReader) -> str:
    metadata = reader.metadata or {}
    title = str(metadata.get("/Title") or "").strip()
    return title if title and title.lower() != "none" else path.stem.replace("_", " ")


def normalize_text(text: str) -> str:
    text = text.replace("\u00ad", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"(?<=\w)-\n(?=\w)", "", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def convert_pdf(source: Path, destination: Path) -> None:
    reader = PdfReader(source)
    destination.parent.mkdir(parents=True, exist_ok=True)

    parts = [
        f"# {safe_title(source, reader)}",
        "",
        f"- Source: `{source.as_posix()}`",
        f"- Pages: {len(reader.pages)}",
        "- Conversion: text extraction with pypdf; page boundaries are preserved.",
        "",
    ]
    for page_number, page in enumerate(reader.pages, start=1):
        text = normalize_text(page.extract_text() or "")
        parts.extend(
            [
                f"## Page {page_number}",
                "",
                text or "_No extractable text on this page._",
                "",
            ]
        )

    destination.write_text("\n".join(parts), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert local PDF files to page-oriented Markdown.")
    parser.add_argument("input", type=Path, help="PDF file or directory containing PDF files")
    parser.add_argument("output", type=Path, help="Output Markdown file or directory")
    args = parser.parse_args()

    sources = [args.input] if args.input.is_file() else sorted(args.input.glob("*.pdf"))
    if not sources:
        raise SystemExit(f"No PDF files found in {args.input}")

    for source in sources:
        destination = args.output if len(sources) == 1 and args.output.suffix else args.output / f"{source.stem}.md"
        print(f"Converting {source} -> {destination}")
        convert_pdf(source, destination)


if __name__ == "__main__":
    main()
