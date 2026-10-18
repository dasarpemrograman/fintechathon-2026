from pathlib import Path
import unittest
from packages.adapters.documents import extract, candidates

ROOT = Path(__file__).resolve().parents[1] / "fixtures/demo/documents"


class DocumentExtractionTests(unittest.TestCase):
    def test_actual_text_native_pdf_and_scanned_sources(self):
        for name, media in [
            ("quotation.txt", "text/plain"),
            ("quotation.pdf", "application/pdf"),
            ("scan.png", "image/png"),
            ("scanned.pdf", "application/pdf"),
        ]:
            with self.subTest(name=name):
                pages = extract((ROOT / name).read_bytes(), media)
                facts = candidates(pages)
                self.assertTrue(
                    any(f["value"].get("decimal") == "350.00" for f in facts),
                    (name, facts),
                )
                self.assertTrue(all(f["locator"] and f["original_text"] for f in facts))
                if name in {"scan.png", "scanned.pdf"}:
                    self.assertTrue(
                        all("OCR word boxes:" in f["locator"] for f in facts)
                    )
                if name == "scanned.pdf":
                    self.assertTrue(
                        all(f["locator"].startswith("PDF page 1;") for f in facts)
                    )

    def test_chinese_original_script_and_ambiguity_are_preserved(self):
        facts = candidates(
            extract((ROOT / "ambiguous-zh.txt").read_bytes(), "text/plain")
        )
        self.assertTrue(facts)
        self.assertTrue(
            any("¥" in f["original_text"] or "30" in f["original_text"] for f in facts)
        )
        self.assertTrue(all(f["value"]["status"] == "unreviewed" for f in facts))

    def test_indonesian_and_chinese_ocr_retain_original_language_and_regions(self):
        for language, expected in [("id", "Harga"), ("zh", "价格")]:
            with self.subTest(language=language):
                pages = extract(
                    (ROOT / ("scan-" + language + ".png")).read_bytes(), "image/png"
                )
                self.assertIn(expected, pages[0]["text"])
                facts = candidates(pages)
                self.assertTrue(any(f["value"]["decimal"] == "350.00" for f in facts))
                self.assertTrue(all(f["original_language"] == language for f in facts))
                self.assertTrue(all("OCR word boxes:" in f["locator"] for f in facts))
                self.assertTrue(
                    all(f["value"]["status"] == "unreviewed" for f in facts)
                )
                if language == "zh":
                    self.assertTrue(
                        any(f["field_path"] == "/extracted/ambiguity" for f in facts)
                    )

    def test_indonesian_gold_spans_and_net_anchor(self):
        pages = extract((ROOT / "quotation-id.txt").read_bytes(), "text/plain")
        facts = candidates(pages)
        self.assertEqual(
            [f["original_text"] for f in facts], ["IDR 5500000", "10 kg", "Net 30"]
        )
        self.assertTrue(all(f["original_language"] == "id" for f in facts))
        self.assertIn("anchor", facts[-1]["value"]["reason"])
