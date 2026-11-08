import unittest, tempfile
from pathlib import Path
import fitz
from motor import clean,mode_for
class Tests(unittest.TestCase):
    def test_reject_unsupported(self):
        with tempfile.TemporaryDirectory() as t:
            a=Path(t)/'a.pdf';b=Path(t)/'b.pdf'
            with fitz.open() as d:
                d.new_page().insert_text((50,50),'Ornek metin')
                d.save(a)
            with self.assertRaises(ValueError):clean(a,b,'nesne')
            self.assertFalse(b.exists())
    def test_never_overwrite(self):
        with tempfile.TemporaryDirectory() as t:
            a=Path(t)/'a.pdf'
            with fitz.open() as d:
                d.new_page().insert_text((50,50),'Ornek metin')
                d.save(a)
            with self.assertRaises(FileExistsError):clean(a,a)
    def test_image_mode_preserves_page_count(self):
        with tempfile.TemporaryDirectory() as t:
            a=Path(t)/'a.pdf';b=Path(t)/'b.pdf'
            with fitz.open() as d:
                p=d.new_page(width=100,height=100)
                p.insert_image(p.rect,stream=fitz.Pixmap(fitz.csRGB,fitz.IRect(0,0,20,20),0).tobytes('png'))
                d.save(a)
            report=clean(a,b,'goruntu')
            with fitz.open(b) as d:self.assertEqual(len(d),1)
            self.assertEqual(report['sayfa'],1)
if __name__=='__main__':unittest.main()
