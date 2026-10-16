"""Isolated document processor; stdin paths are assigned by the trusted parent."""

import json, os, subprocess, sys
from tempfile import TemporaryDirectory
from pathlib import Path


def extract(path, media):
    if media == "text/plain":
        return [
            {
                "page": 1,
                "text": Path(path).read_text(encoding="utf-8"),
                "locator": "UTF-8 document",
            }
        ]
    if media == "application/pdf":
        from pypdf import PdfReader

        reader = PdfReader(path)
        if len(reader.pages) > 100:
            raise ValueError("PDF exceeds configured 100-page processing limit")
        result = []
        for index, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if not text.strip():
                with TemporaryDirectory() as directory:
                    prefix = Path(directory) / "page"
                    subprocess.run(
                        [
                            "pdftoppm",
                            "-f",
                            str(index + 1),
                            "-l",
                            str(index + 1),
                            "-scale-to",
                            "1800",
                            "-singlefile",
                            "-png",
                            str(path),
                            str(prefix),
                        ],
                        capture_output=True,
                        check=True,
                        timeout=15,
                    )
                    scanned = extract(str(prefix) + ".png", "image/png")[0]
                    text = scanned["text"]
            result.append(
                {
                    "page": index + 1,
                    "text": text,
                    "locator": "PDF page " + str(index + 1),
                }
            )
        return result
    from PIL import Image

    Image.MAX_IMAGE_PIXELS = 20_000_000
    with Image.open(path) as image:
        image.verify()
    args = [
        "tesseract",
        str(path),
        "stdout",
        "-l",
        "eng+ind+chi_sim",
        "-c",
        "tessedit_create_tsv=1",
    ]
    output = subprocess.run(
        args, capture_output=True, text=True, check=True, timeout=20
    ).stdout
    if not output.startswith("level\tpage_num"):
        raise ValueError("OCR processor did not return its declared TSV format")
    rows = []
    for line in output.splitlines()[1:]:
        columns = line.split("\t", 11)
        if len(columns) == 12 and columns[11].strip():
            rows.append(columns)
    text = " ".join(r[11] for r in rows)
    return [
        {
            "page": 1,
            "text": text,
            "locator": "OCR word boxes: " + ";".join(",".join(r[6:10]) for r in rows),
        }
    ]


if __name__ == "__main__":
    try:
        print(
            json.dumps({"pages": extract(sys.argv[1], sys.argv[2])}, ensure_ascii=False)
        )
    except Exception as error:
        print(json.dumps({"error": type(error).__name__ + ": " + str(error)[:300]}))
        sys.exit(1)
