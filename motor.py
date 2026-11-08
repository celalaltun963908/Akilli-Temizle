"""Akıllı Temizle v1.2 - çok görüntülü PDF sayfaları için güvenli deneme motoru.

Not: Görüntü yöntemi sayfaları rasterleştirir; seçilebilir metin korunmaz.
"""
from pathlib import Path
import json
import os
import re
import tempfile
from io import BytesIO

import fitz
import numpy as np
from PIL import Image

SIGS = (b'75.629997 Tf', b'2.7063293 -1.5625')


def mode_for(doc):
    # Çok görüntülü, metin katmanı bulunmayan PDF'ler görüntü yöntemiyle işlenebilir.
    if all(p.get_images(full=True) and not p.get_text().strip() for p in doc):
        return 'goruntu'
    return 'nesne'


def _clean_page_pixels(page, scale=2.0):
    # PDF'yi tek bir görüntü nesnesinden değil, TÜM sayfa içeriğinden üret.
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), colorspace=fitz.csRGB, alpha=False)
    pixels = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3).copy()
    r = pixels[:, :, 0].astype(np.int16)
    g = pixels[:, :, 1].astype(np.int16)
    b = pixels[:, :, 2].astype(np.int16)
    pale_blue = (r >= 190) & (g >= r - 2) & (b >= g - 2) & ((b - r) >= 1) & ((b - r) <= 48) & ((g - r) <= 35)
    pale_gray = (r >= 225) & (np.abs(r - g) <= 5) & (np.abs(g - b) <= 5)
    mask = pale_blue | pale_gray
    pixels[mask] = 255
    buf = BytesIO()
    Image.fromarray(pixels, 'RGB').save(buf, format='PNG', optimize=True)
    return buf.getvalue(), int(mask.sum())


def clean(source, target, mode='otomatik'):
    source, target = Path(source), Path(target)
    if not source.is_file():
        raise FileNotFoundError(source)
    if source.resolve() == target.resolve() or target.exists():
        raise FileExistsError('Orijinal veya mevcut çıktı üzerine yazılmaz.')
    if mode not in ('otomatik', 'goruntu', 'nesne'):
        raise ValueError('Geçersiz mod')
    doc = fitz.open(source)
    resultdoc = None
    try:
        if doc.needs_pass:
            raise ValueError('Şifreli PDF desteklenmiyor.')
        if not doc.is_pdf or len(doc) == 0:
            raise ValueError('Geçerli bir PDF gerekli.')
        if mode == 'otomatik':
            mode = mode_for(doc)
        results = []
        if mode == 'goruntu':
            resultdoc = fitz.open()
            for i, page in enumerate(doc):
                png, count = _clean_page_pixels(page)
                out = resultdoc.new_page(width=page.rect.width, height=page.rect.height)
                out.insert_image(out.rect, stream=png)
                results.append({'sayfa': i + 1, 'durum': 'islem_yapildi', 'degisen_piksel': count})
        else:
            resultdoc = doc
            for i, page in enumerate(doc):
                contents = page.get_contents()
                if len(contents) != 1:
                    results.append({'sayfa': i + 1, 'durum': 'atlandi'})
                    continue
                stream = doc.xref_stream(contents[0])
                candidates = []
                for item in page.get_xobjects():
                    xref, name = item[:2]
                    try:
                        if '/Subtype /Form' in doc.xref_object(xref) and all(sig in doc.xref_stream(xref) for sig in SIGS):
                            candidates.append(name)
                    except Exception:
                        pass
                if len(candidates) != 1:
                    results.append({'sayfa': i + 1, 'durum': 'atlandi'})
                    continue
                pattern = (rb'\nq\s+0 0 2481\.25 3509 re\s+W\* n\s+q\s+1 0 0 1 226 1087 cm\s+0 0 0 RG 0 0 0 rg\s+/G\d+ gs\s+/' + re.escape(candidates[0].encode()) + rb' Do\s+Q\s+Q\s*$')
                new, count = re.subn(pattern, b'\n', stream)
                if count == 1:
                    doc.update_stream(contents[0], new)
                    results.append({'sayfa': i + 1, 'durum': 'temizlendi'})
                else:
                    results.append({'sayfa': i + 1, 'durum': 'atlandi'})
            if not any(r['durum'] == 'temizlendi' for r in results):
                raise ValueError('Güvenli nesne temizleme kalıbı bulunamadı. Görüntü yöntemini deneyin.')
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(suffix='.pdf', dir=target.parent)
