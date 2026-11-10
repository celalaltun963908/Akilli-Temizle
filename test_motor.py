from pathlib import Path
import fitz
import pytest
from motor import clean, mode_for


def make_pdf(path, with_watermark=True):
    with fitz.open() as doc:
        page = doc.new_page()
        page.insert_text((72, 72), 'Math: x^2 + y^2 = 25')
        page.draw_line((72, 90), (150, 90))
        if with_watermark:
            annot = page.add_freetext_annot(fitz.Rect(100, 200, 300, 250), 'SAMPLE')
            # PDF annotation type is FreeText, not Watermark: test a real Watermark annotation
            page.delete_annot(annot)
            xref = doc.get_new_xref()
            doc.update_object(xref, '<< /Type /Annot /Subtype /Watermark /Rect [100 200 300 250] /F 4 >>')
            doc.xref_set_key(page.xref, 'Annots', f'[{xref} 0 R]')
        doc.save(path)


def test_watermark_removal(tmp_path):
    source, target = tmp_path/'in.pdf', tmp_path/'out.pdf'
    make_pdf(source)
    with fitz.open(source) as doc:
        before = doc[0].get_text()
        assert mode_for(doc) == 'filigran'
    result = clean(source, target)
    assert result['silinen_filigran'] == 1
    with fitz.open(target) as doc:
        assert doc[0].get_text() == before
        assert mode_for(doc) == 'tespit_yok'


def test_no_watermark_does_not_write(tmp_path):
    source, target = tmp_path/'in.pdf', tmp_path/'out.pdf'
    make_pdf(source, False)
    with pytest.raises(ValueError):
        clean(source, target)
    assert not target.exists()


def test_no_overwrite(tmp_path):
    source, target = tmp_path/'in.pdf', tmp_path/'out.pdf'
    make_pdf(source)
    target.write_bytes(b'existing')
    with pytest.raises(FileExistsError):
        clean(source, target)

from motor import inspect_page, clean_selected

def test_manual_selection(tmp_path):
    source, target = tmp_path/'source.pdf', tmp_path/'manual.pdf'
    make_pdf(source)
    data = inspect_page(source, 0)
    assert len(data['watermarklar']) == 1
    result = clean_selected(source, target, {0: [data['watermarklar'][0]['xref']]})
    assert result['silinen_filigran'] == 1
    with fitz.open(target) as doc:
        assert mode_for(doc) == 'tespit_yok'
        assert 'Math:' in doc[0].get_text()

def test_manual_reject_non_watermark(tmp_path):
    source, target = tmp_path/'source.pdf', tmp_path/'manual.pdf'
    make_pdf(source)
    with pytest.raises(ValueError):
        clean_selected(source, target, {0: [999999]})
    assert not target.exists()
