"""Akıllı Temizle v0.7: two conservative, sample-tested PDF cleaning paths."""
from pathlib import Path
from io import BytesIO
import json, os, re, tempfile
import fitz
import numpy as np
from PIL import Image

SIGS=(b'75.629997 Tf',b'2.7063293 -1.5625')

def mode_for(doc):
    if all(len(p.get_images(full=True))==1 and not p.get_text().strip() for p in doc):
        return 'goruntu'
    return 'nesne'

def clean(source, target, mode='otomatik'):
    source,target=Path(source),Path(target)
    if not source.is_file(): raise FileNotFoundError(source)
    if source.resolve()==target.resolve() or target.exists(): raise FileExistsError('Orijinal veya mevcut çıktı üzerine yazılmaz.')
    doc=fitz.open(source)
    if doc.needs_pass: doc.close();raise ValueError('Şifreli PDF desteklenmiyor.')
    if mode=='otomatik':mode=mode_for(doc)
    results=[]
    try:
        if mode=='nesne':
            for i,page in enumerate(doc):
                contents=page.get_contents()
                if len(contents)!=1:
                    results.append({'sayfa':i+1,'durum':'atlandi'});continue
                stream=doc.xref_stream(contents[0]); candidates=[]
                for item in page.get_xobjects():
                    xref,name=item[:2]
                    try:
                        if '/Subtype /Form' in doc.xref_object(xref) and all(s in doc.xref_stream(xref) for s in SIGS):candidates.append(name)
                    except Exception:pass
                if len(candidates)!=1:
                    results.append({'sayfa':i+1,'durum':'atlandi'});continue
                pattern=(rb'\nq\s+0 0 2481\.25 3509 re\s+W\* n\s+q\s+1 0 0 1 226 1087 cm\s+0 0 0 RG 0 0 0 rg\s+/G\d+ gs\s+/'+re.escape(candidates[0].encode())+rb' Do\s+Q\s+Q\s*$')
                new,count=re.subn(pattern,b'\n',stream)
                if count==1:
                    doc.update_stream(contents[0],new);results.append({'sayfa':i+1,'durum':'temizlendi'})
                else:results.append({'sayfa':i+1,'durum':'atlandi'})
            if not any(r['durum']=='temizlendi' for r in results):raise ValueError('Güvenli nesne temizleme kalıbı bulunamadı.')
            resultdoc=doc
        elif mode=='goruntu':
            if not all(len(p.get_images(full=True))==1 and not p.get_text().strip() for p in doc):raise ValueError('Görüntü modu yalnızca tek görüntülü sayfalarda desteklenir.')
            resultdoc=fitz.open()
            for i,p in enumerate(doc):
                pix=fitz.Pixmap(doc,p.get_images(full=True)[0][0])
                if pix.n not in (3,4):raise ValueError(f'{i+1}. sayfa: desteklenmeyen renk formatı')
                a=np.frombuffer(pix.samples,dtype=np.uint8).reshape(pix.height,pix.width,pix.n)[:,:,:3].copy()
                r=a[:,:,0].astype(np.int16);g=a[:,:,1].astype(np.int16);b=a[:,:,2].astype(np.int16)
                pale_blue=(r>=190)&(g>=r-2)&(b>=g-2)&((b-r)>=1)&((b-r)<=48)&((g-r)<=35)
                pale_gray=(r>=225)&(abs(r-g)<=5)&(abs(g-b)<=5)
                mask=pale_blue|pale_gray
                a[mask]=255
                bio=BytesIO();Image.fromarray(a).save(bio,'PNG',optimize=True)
                q=resultdoc.new_page(width=p.rect.width,height=p.rect.height)
                q.insert_image(q.rect,stream=bio.getvalue())
                results.append({'sayfa':i+1,'durum':'islem_yapildi','degisen_piksel':int(mask.sum())})
        else:raise ValueError('Geçersiz mod')
        target.parent.mkdir(parents=True,exist_ok=True)
        fd,tmp=tempfile.mkstemp(suffix='.pdf',dir=target.parent);os.close(fd)
        try:
            resultdoc.save(tmp,garbage=4,deflate=True)
            with fitz.open(tmp) as check:
                if len(check)!=len(doc):raise RuntimeError('Sayfa sayısı değişti')
                if mode=='nesne':
                    for i in range(len(doc)):
                        # compare original content text excluding the watermark token
                        with fitz.open(source) as orig:
                            a=orig[i].get_text().replace('COOLMATEMATİK','').strip()
                        b=check[i].get_text().replace('COOLMATEMATİK','').strip()
                        if a!=b:raise RuntimeError(f'{i+1}. sayfada metin değişti')
            os.replace(tmp,target)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)
        report={'surum':'0.9','kaynak':source.name,'cikti':target.name,'mod':mode,'sayfa':len(doc),'islemler':results,'uyari':'Görüntü modunda açık renkli soru detayları da etkilenebilir; görsel kontrol gereklidir.'}
        target.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        return report
    finally:
        if 'resultdoc' in locals() and resultdoc is not doc:resultdoc.close()
        doc.close()

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('source');parser.add_argument('target');parser.add_argument('--mode',choices=['otomatik','goruntu','nesne'],default='otomatik');args=parser.parse_args()
    print(json.dumps(clean(args.source,args.target,args.mode),ensure_ascii=False,indent=2))
