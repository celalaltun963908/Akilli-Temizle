"""Akıllı Temizle V2.4 — güvenli PDF Watermark açıklaması temizleme."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import tempfile
import fitz


def _watermarks(page):
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
                'pymupdf': fitz.VersionBind, 'sayfa': len(doc),
                'watermark_sayisi': sum(counts), 'sayfa_bazinda': counts,
                'algilanan_yontem': 'filigran' if any(counts) else 'tespit_yok',
                'goruntu_sayisi': sum(len(p.get_images(full=True)) for p in doc),
                'cizim_sayisi': sum(len(p.get_drawings()) for p in doc),
                'uyari': 'Görüntü ve çizimler incelenir; gömülü filigranlar otomatik silinmez.'}


def _check_paths(source, target):
    source, target = Path(source), Path(target)
    if not source.is_file():
        raise FileNotFoundError(source)
    if source.resolve() == target.resolve() or target.exists():
        raise FileExistsError('Orijinal veya mevcut çıktı üzerine yazılamaz.')
    report_path = target.with_suffix('.json')
    if report_path.exists():
        raise FileExistsError('Rapor zaten mevcut: ' + str(report_path))
    target.parent.mkdir(parents=True, exist_ok=True)
    return source, target, report_path


def _snapshot(doc):
    return [p.get_text() for p in doc]


def _visual_snapshot(doc):
    """Watermark açıklaması dışındaki görüntü ve çizim yapılarını sayar."""
    return [(tuple(round(float(x), 3) for x in p.rect),
             len(p.get_images(full=True)), len(p.get_drawings())) for p in doc]


def _verify_visual(check, expected):
    actual = _visual_snapshot(check)
    if actual != expected:
        raise RuntimeError('Görsel yapı doğrulaması başarısız. Çıktı oluşturulmadı.')


def _verify_text(check, expected):
    if len(check) != len(expected):
        raise RuntimeError(f'Sayfa sayısı değişti: {len(expected)} -> {len(check)}.')
    for i, page in enumerate(check):
        actual = page.get_text()
        if actual != expected[i]:
            import difflib
            matcher = difflib.SequenceMatcher(None, expected[i], actual, autojunk=False)
            op, a, b, c, d = next((x for x in matcher.get_opcodes() if x[0] != 'equal'),
                                   ('equal', 0, 0, 0, 0))
            left = expected[i][max(0, a-35):min(len(expected[i]), b+35)]
            right = actual[max(0, c-35):min(len(actual), d+35)]
            raise RuntimeError(
                f'Metin doğrulaması başarısız: sayfa {i+1}, fark türü {op}; '
                f'önce={left!r}; sonra={right!r}. '
                'Çıktı oluşturulmadı. Bu farkın zararsız olduğu varsayılmadı.')


def _write_output(tmp, target, report_path, report):
    # Existing target is never overwritten; failure also removes a partial output.
    created = False
    try:
        with open(target, 'xb') as out, open(tmp, 'rb') as inp:
            created = True
            shutil.copyfileobj(inp, out)
        with open(report_path, 'x', encoding='utf-8') as out:
            json.dump(report, out, ensure_ascii=False, indent=2)
    except Exception:
        if created:
            target.unlink(missing_ok=True)
        raise


def clean(source, target, mode='otomatik'):
    source, target, report_path = _check_paths(source, target)
    if mode not in ('otomatik', 'filigran'):
        raise ValueError('Yalnızca PDF Watermark açıklamaları desteklenir.')
    fd, tmp = tempfile.mkstemp(suffix='.pdf', dir=target.parent)
    os.close(fd)
    try:
        with fitz.open(source) as doc:
            if doc.needs_pass:
                raise ValueError('Şifreli PDF desteklenmiyor.')
            counts = [len(_watermarks(p)) for p in doc]
            if not any(counts):
                details = diagnose(source)
                raise ValueError('Watermark açıklaması bulunamadı. PDF değiştirilmedi. '
                                 f"PyMuPDF={details['pymupdf']}, SHA256={details['sha256'][:16]}..., "
                                 f"dosya={details['dosya']}")
            for page in doc:
                for mark in _watermarks(page):
                    page.delete_annot(mark)
            # Compare the saved PDF against the post-removal document state.
            # Annotation text may legitimately disappear when a watermark is removed.
            expected = _snapshot(doc)
            expected_visual = _visual_snapshot(doc)
            doc.save(tmp, garbage=4, deflate=True)
        with fitz.open(tmp) as check:
            _verify_text(check, expected)
            _verify_visual(check, expected_visual)
            if any(_watermarks(p) for p in check):
                raise RuntimeError('Watermark açıklaması kaldı; çıktı oluşturulmadı.')
        report = {'surum': '2.4', 'mod': 'filigran', 'sayfa': len(counts),
                  'silinen_filigran': sum(counts), 'sayfa_bazinda': counts,
                  'kayit_sonrasi_metin_dogrulandi': True,
                  'kayit_sonrasi_gorsel_yapi_dogrulandi': True,
                  'uyari': 'Filigran silindikten sonraki metin kaydedilen PDF ile karşılaştırıldı; görsel yapının sayısal kontrolü yapılmıştır; sayfalar yine de gözle karşılaştırılmalıdır.'}
        _write_output(tmp, target, report_path, report)
        return report
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


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
        words = page.get_text('words')
        hints = ('filigran', 'watermark', 'taslak', 'örnektir', 'sample', 'draft')
        candidates = sorted({str(w[4]) for w in words
                             if any(h in str(w[4]).casefold() for h in hints)})
        return {'sayfa': page_number + 1, 'watermarklar': marks,
                'metin_adaylari': candidates,
                'uyari': 'Metin adayları ve grafikler yalnızca inceleme amaçlıdır; silinmez.'}


def clean_selected(source, target, selected):
    """selected: {zero_based_page_number: [watermark_annotation_xref, ...]}"""
    source, target, report_path = _check_paths(source, target)
    if not selected or not any(selected.values()):
        raise ValueError('Silinecek Watermark açıklaması seçilmedi.')
    fd, tmp = tempfile.mkstemp(suffix='.pdf', dir=target.parent)
    os.close(fd)
    try:
        with fitz.open(source) as doc:
            if doc.needs_pass:
                raise ValueError('Şifreli PDF desteklenmiyor.')
            before_counts = [len(_watermarks(p)) for p in doc]
            counts = [0] * len(doc)
            for page_index, xrefs in selected.items():
                index = int(page_index)
                if not 0 <= index < len(doc):
                    raise ValueError('Sayfa numarası geçersiz.')
                page = doc[index]
                available = {a.xref: a for a in _watermarks(page)}
                for xref in set(map(int, xrefs)):
                    if xref not in available:
                        raise ValueError(f'Seçilen öğe Watermark değil: {xref}')
                    page.delete_annot(available[xref])
                    counts[index] += 1
            if not any(counts):
                raise ValueError('Silinecek öğe bulunamadı.')
            expected = _snapshot(doc)
            expected_visual = _visual_snapshot(doc)
            doc.save(tmp, garbage=4, deflate=True)
        with fitz.open(tmp) as check:
            _verify_text(check, expected)
            _verify_visual(check, expected_visual)
            for i, page in enumerate(check):
                actual_count = len(_watermarks(page))
                expected_count = before_counts[i] - counts[i]
                if actual_count != expected_count:
                    raise RuntimeError(
                        f'Filigran sayısı doğrulanamadı: sayfa {i+1}; '
                        f'beklenen={expected_count}, bulunan={actual_count}.')
        report = {'surum': '2.4', 'mod': 'manuel-watermark', 'sayfa': len(counts),
                  'silinen_filigran': sum(counts), 'sayfa_bazinda': counts,
                  'kayit_sonrasi_metin_dogrulandi': True,
                  'kayit_sonrasi_gorsel_yapi_dogrulandi': True,
                  'uyari': 'Filigran silindikten sonraki metin kaydedilen PDF ile karşılaştırıldı; görsel yapının sayısal kontrolü yapılmıştır; sayfalar yine de gözle karşılaştırılmalıdır.'}
        _write_output(tmp, target, report_path, report)
        return report
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _watermarks_in_source(source, page_index):
    with fitz.open(source) as doc:
        return [a.xref for a in _watermarks(doc[page_index])]
