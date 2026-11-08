import unittest
import tempfile
from pathlib import Path

import fitz
from motor import clean


class Tests(unittest.TestCase):

    def test_reject_unsupported(self):
        with tempfile.TemporaryDirectory() as t:
            a = Path(t) / "a.pdf"
            b = Path(t) / "b.pdf"

            with fitz.open() as d:
                d.new_page()
                d.save(a)

            with self.assertRaises(ValueError):
                clean(a, b, "nesne")

    def test_never_overwrite(self):
        with tempfile.TemporaryDirectory() as t:
            a = Path(t) / "a.pdf"

            with fitz.open() as d:
                d.new_page()
                d.save(a)

            with self.assertRaises(FileExistsError):
                clean(a, a)

    def test_preserve_page_count(self):
        with tempfile.TemporaryDirectory() as t:
            a = Path(t) / "a.pdf"
            b = Path(t) / "b.pdf"

            with fitz.open() as d:
                d.new_page()
                d.new_page()
                d.save(a)

            try:
                clean(a, b, "goruntu")
            except ValueError:
                return

            with fitz.open(b) as d:
                self.assertEqual(len(d), 2)


if __name__ == "__main__":
    unittest.main()
