"""Akıllı Temizle v1.7: PDF Watermark annotation removal and diagnostics."""
from pathlib import Path
import hashlib
import json
import os
import tempfile
import fitz


def _watermarks(page):
    # PDF annotation subtype 25 is Watermark in PyMuPDF.
    return [a for a in (page.annots() or [])
            if a.type[0] == 25 or str(a.type[1]).casefold() == 'watermark']


def mode_for(doc):
    return 'filigran' if any(_watermarks(p) for p in doc) else 'tespit_yok'


def diagnose(source):
    source = Path(source)
    with fitz.open(source) as doc:
        counts = [len(_watermarks(p)) for p in doc]
        return {'dosya': str(source.resolve()),
                'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                'pymupdf': fitz.VersionBind,
                'sayfa': len(doc),
                'watermark_sayisi': sum(counts),
                'sayfa_bazinda': counts,
                'algilanan_yontem': 'filigran' if any(counts) else 'tespit_yok'}


def clean(source, target, mode='otomatik'):
    source, target = Path(source), Path(target)
    if not source.is_file():
        raise FileNotFoundError(source)
    if source.resolve() == target.resolve() or target.exists():
        raise FileExistsError('Orijinal dosya veya mevcut çıktı üzerine yazılamaz.')
    if mode not in ('otomatik', 'filigran'):
        raise ValueError('Yalnızca PDF Watermark açıklamaları desteklenir.')
    report_path = target.with_suffix('.json')
    if report_path.exists():
        raise FileExistsError('Rapor zaten mevcut: ' + str(report_path))
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(suffix='.pdf', dir=target.parent)
    os.close(fd)
    try:
        with fitz.open(source) as doc:
            if doc.needs_pass:
                raise ValueError('Şifreli PDF desteklenmiyor.')
            counts = []
            for page in doc:
                marks = _watermarks(page)
                counts.append(len(marks))
                for mark in marks:
                    page.delete_annot(mark)
            if not any(counts):
                details = diagnose(source)
                raise ValueError('Watermark açıklaması bulunamadı. PDF değiştirilmedi. '
                                 f"PyMuPDF={details['pymupdf']}, SHA256={details['sha256'][:16]}..., "
                                 f"dosya={details['dosya']}")
            expected_text = [p.get_text() for p in doc]
            doc.save(tmp, garbage=4, deflate=True)
        with fitz.open(tmp) as check:
            if len(check) != len(expected_text) or any(p.get_text() != t for p, t in zip(check, expected_text)):
                raise RuntimeError('Metin veya sayfa doğrulaması başarısız.')
            if any(_watermarks(p) for p in check):
                raise RuntimeError('Watermark açıklaması kaldı.')
        # Create the output exclusively; never replace an existing PDF.
        with open(target, 'xb') as dest, open(tmp, 'rb') as src:
            import shutil
            shutil.copyfileobj(src, dest)
        report = {'surum': '1.7', 'mod': 'filigran', 'sayfa': len(counts),
                  'silinen_filigran': sum(counts), 'sayfa_bazinda': counts,
                  'metin_korundu': True,
                  'uyari': 'Görsel içerik ayrıca kontrol edilmelidir.'}
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        return report
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

# v1.8: inspection is read-only. Only confirmed Watermark annotations can be deleted.
def inspect_page(source, page_number):
    with fitz.open(source) as doc:
        if doc.needs_pass:
            raise ValueError('Şifreli PDF desteklenmiyor.')
        if not 0 <= page_number < len(doc):
            raise IndexError('Sayfa numarası geçersiz.')
        page = doc[page_number]
        marks = [{'xref': a.xref, 'tur': str(a.type[1]),
                  'konum': tuple(round(float(v), 1) for v in a.rect)}
                 for a in _watermarks(page)]
        # Read-only candidates. Never auto-delete text or graphics.
        words = page.get_text('words')
        hints = ('filigran', 'watermark', 'taslak', 'örnektir', 'sample', 'draft')
        candidates = sorted({str(w[4]) for w in words if any(h in str(w[4]).casefold() for h in hints)})
        return {'sayfa': page_number + 1, 'watermarklar': marks,
                'metin_adaylari': candidates,
                'uyari': 'Metin adayları ve grafikler yalnızca inceleme amaçlıdır; silinmez.'}


def clean_selected(source, target, selected):
    """selected: {zero_based_page_number: [watermark_annotation_xref, ...]}"""
    source, target = Path(source), Path(target)
    if not source.is_file():
        raise FileNotFoundError(source)
    if source.resolve() == target.resolve() or target.exists():
        raise FileExistsError('Orijinal veya mevcut çıktı üzerine yazılamaz.')
    report_path = target.with_suffix('.json')
    if report_path.exists():
        raise FileExistsError('Rapor zaten mevcut.')
    if not selected or not any(selected.values()):
        raise ValueError('Silinecek Watermark açıklaması seçilmedi.')
    fd, tmp = tempfile.mkstemp(suffix='.pdf', dir=target.parent)
    os.close(fd)
    try:
        with fitz.open(source) as doc:
            if doc.needs_pass:
                raise ValueError('Şifreli PDF desteklenmiyor.')
            expected = [p.get_text() for p in doc]
            counts = [0] * len(doc)
            for page_index, xrefs in selected.items():
                if not 0 <= int(page_index) < len(doc):
                    raise ValueError('Sayfa numarası geçersiz.')
                page = doc[int(page_index)]
                available = {a.xref: a for a in _watermarks(page)}
                for xref in set(map(int, xrefs)):
                    if xref not in available:
                        raise ValueError(f'Seçilen öğe Watermark değil: {xref}')
                    page.delete_annot(available[xref]); counts[int(page_index)] += 1
            if not any(counts):
                raise ValueError('Silinecek öğe bulunamadı.')
            doc.save(tmp, garbage=4, deflate=True)
        with fitz.open(tmp) as check:
            if len(check) != len(expected) or [p.get_text() for p in check] != expected:
                raise RuntimeError('Metin doğrulaması başarısız.')
            for i, xrefs in selected.items():
                remaining = {a.xref for a in _watermarks(check[int(i)])}
                # Rewritten xrefs may change after garbage collection; count verified below.
                if len(_watermarks(check[int(i)])) != len(_watermarks_in_source(source, int(i))) - counts[int(i)]:
                    raise RuntimeError('Filigran sayısı doğrulanamadı.')
        with open(target, 'xb') as out, open(tmp, 'rb') as inp:
            import shutil
            shutil.copyfileobj(inp, out)
        report = {'surum': '1.8', 'mod': 'manuel-watermark', 'sayfa': len(counts),
                  'silinen_filigran': sum(counts), 'sayfa_bazinda': counts,
                  'metin_korundu': True, 'uyari': 'Görsel içerik kullanıcı tarafından kontrol edilmelidir.'}
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        return report
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _watermarks_in_source(source, page_index):
    with fitz.open(source) as doc:
        return [a.xref for a in _watermarks(doc[page_index])]
