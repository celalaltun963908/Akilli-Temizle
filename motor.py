"""Akıllı Temizle v1.5: güvenli filigran açıklaması kaldırma."""
from pathlib import Path
import json, os, tempfile
import fitz

def mode_for(doc):
    return 'filigran' if any(any(a.type[1] == 'Watermark' for a in (p.annots() or [])) for p in doc) else 'tespit_yok'

def clean(source, target, mode='otomatik'):
    source, target = Path(source), Path(target)
    if not source.is_file(): raise FileNotFoundError(source)
    if source.resolve() == target.resolve() or target.exists():
        raise FileExistsError('Orijinal dosya veya mevcut çıktı üzerine yazılamaz.')
    if mode not in ('otomatik', 'filigran'):
        raise ValueError('v1.4 güvenli sürümü yalnızca Watermark açıklamalarını kaldırır. Diğer yöntemler devre dışı.')
    report_path = target.with_suffix('.json')
    if report_path.exists():
        raise FileExistsError('Mevcut JSON raporunun üzerine yazılamaz: ' + str(report_path))
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(suffix='.pdf', dir=target.parent)
    os.close(fd)
    try:
        with fitz.open(source) as doc:
            if doc.needs_pass: raise ValueError('Şifreli PDF desteklenmiyor.')
            
            counts = []
            for p in doc:
                marks = [a for a in (p.annots() or []) if a.type[1] == 'Watermark']
                counts.append(len(marks))
                for a in marks: p.delete_annot(a)
            if not any(counts):
                raise ValueError('Watermark açıklaması bulunamadı. PDF değiştirilmedi; başka yöntem doğrulanmalı.')
            expected_text = [p.get_text() for p in doc]
            doc.save(tmp, garbage=4, deflate=True)
        with fitz.open(tmp) as check:
            if len(check) != len(expected_text) or any(p.get_text() != t for p,t in zip(check,expected_text)):
                raise RuntimeError('Metin veya sayfa doğrulaması başarısız; çıktı oluşturulmadı.')
            if any(any(a.type[1] == 'Watermark' for a in (p.annots() or [])) for p in check):
                raise RuntimeError('Filigran açıklaması kaldı; çıktı oluşturulmadı.')
        os.replace(tmp,target)
        report={'surum':'1.5','mod':'filigran','sayfa':len(counts),
                'silinen_filigran':sum(counts),'sayfa_bazinda':counts,
                'metin_korundu':True,'uyari':'Diğer filigran türleri desteklenmez; görselleri kullanıcı kontrol etmelidir.'}
        target.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        return report
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
