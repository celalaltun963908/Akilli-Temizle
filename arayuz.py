"""Akıllı Temizle v1.7 - local preview GUI; run with python arayuz.py."""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from PIL import Image, ImageTk
import fitz
from motor import clean, mode_for, diagnose

class App:
    def __init__(self, root):
        self.root=root; root.title('Akıllı Temizle v1.7 | Güvenli Temizleme'); root.geometry('1100x770')
        self.src=None; self.out=None; self.page=0; self.photos=[]
        bar=ttk.Frame(root,padding=12);bar.pack(fill='x')
        ttk.Button(bar,text='PDF Aç',command=self.choose).pack(side='left')
        self.mode=tk.StringVar(value='otomatik')
        ttk.Label(bar,text='  Yöntem:').pack(side='left')
        ttk.Combobox(bar,textvariable=self.mode,values=['otomatik','filigran'],width=12,state='readonly').pack(side='left',padx=6)
        ttk.Button(bar,text='Temizle ve Kaydet',command=self.process).pack(side='left',padx=8)
        ttk.Button(bar,text='PDF Teşhisi',command=self.diagnostics).pack(side='left',padx=4)
        ttk.Button(bar,text='Toplu Temizle',command=self.batch).pack(side='left',padx=4)
        self.status=tk.StringVar(value='Bir PDF seçin. Orijinal dosya değişmez.')
        ttk.Label(root,textvariable=self.status,padding=(12,4)).pack(anchor='w')
        controls=ttk.Frame(root,padding=(12,4));controls.pack(fill='x')
        ttk.Button(controls,text='◀ Önceki',command=lambda:self.change(-1)).pack(side='left')
        self.pg=ttk.Label(controls,text='Sayfa: —');self.pg.pack(side='left',padx=16)
        ttk.Button(controls,text='Sonraki ▶',command=lambda:self.change(1)).pack(side='left')
        frame=ttk.Frame(root,padding=10);frame.pack(fill='both',expand=True)
        self.panels=[]
        for title in ('Orijinal PDF','Temizlenmiş PDF'):
            pane=ttk.Frame(frame);pane.pack(side='left',fill='both',expand=True,padx=5)
            ttk.Label(pane,text=title,font=('Arial',12,'bold')).pack()
            canvas=tk.Canvas(pane,bg='#e9edf1',highlightthickness=0)
            canvas.pack(fill='both',expand=True,pady=6)
            canvas.bind('<Configure>',lambda _e:self.show())
            self.panels.append(canvas)
        ttk.Label(root,text='Güvenli mod: yalnızca PDF Watermark açıklamaları kaldırılır. Diğer filigranlar değiştirilmez.',foreground='#a04a00',padding=10).pack(anchor='w')
    def choose(self):
        f=filedialog.askopenfilename(title='PDF seç',filetypes=[('PDF','*.pdf')]);
        if not f:return
        try:
            with fitz.open(f) as d:
                if d.needs_pass:raise ValueError('Şifreli PDF desteklenmiyor.')
                count=len(d); detected=mode_for(d)
            self.src=Path(f);self.out=None;self.page=0
            self.status.set(f'{self.src.name} · {count} sayfa · Algılanan yöntem: {detected}')
            self.show()
        except Exception as e:messagebox.showerror('Dosya açılamadı',str(e))
    def process(self):
        if not self.src:messagebox.showwarning('PDF seçin','Önce PDF açın.');return
        dest=filedialog.asksaveasfilename(title='Yeni temizlenmiş PDF',defaultextension='.pdf',initialfile=self.src.stem+'_temizlenmis.pdf',filetypes=[('PDF','*.pdf')]);
        if not dest:return
        try:
            self.root.config(cursor='watch');self.root.update_idletasks()
            report=clean(self.src,Path(dest),self.mode.get())
            self.out=Path(dest);self.status.set(f"Kaydedildi: {self.out.name} · {report['mod']} · {report['sayfa']} sayfa")
            self.show()
            messagebox.showinfo('İşlem tamamlandı','Çıktı oluşturuldu. İki görünümü sayfa sayfa karşılaştırın.\nAyrıca JSON işlem raporu kaydedildi.')
        except Exception as e:messagebox.showerror('İşlem yapılamadı',str(e))
        finally:self.root.config(cursor='')
    def diagnostics(self):
        if not self.src:
            messagebox.showwarning('PDF seçin','Önce PDF açın.'); return
        try:
            import json
            info=diagnose(self.src)
            messagebox.showinfo('PDF Teşhisi',
                f"Dosya: {info['dosya']}\nPyMuPDF: {info['pymupdf']}\n"
                f"Sayfa: {info['sayfa']}\nWatermark: {info['watermark_sayisi']}\n"
                f"SHA256: {info['sha256']}")
        except Exception as e: messagebox.showerror('Teşhis hatası',str(e))

    def batch(self):
        paths=filedialog.askopenfilenames(title='Toplu temizlenecek PDF dosyalarını seçin',filetypes=[('PDF','*.pdf')])
        if not paths: return
        folder=filedialog.askdirectory(title='Çıktıların kaydedileceği klasörü seçin')
        if not folder: return
        output_dir=Path(folder)
        successes=[]; errors=[]
        self.root.config(cursor='watch')
        try:
            for index, src in enumerate(paths,1):
                src=Path(src)
                self.status.set(f'Toplu işlem {index}/{len(paths)}: {src.name}')
                self.root.update_idletasks()
                dest=output_dir/(src.stem+'_temizlenmis.pdf')
                try:
                    result=clean(src,dest,'otomatik')
                    successes.append(f"{src.name}: {result['silinen_filigran']} filigran")
                except Exception as e:
                    errors.append(f'{src.name}: {e}')
        finally:
            self.root.config(cursor='')
        self.status.set(f'Toplu işlem: {len(successes)} başarılı, {len(errors)} başarısız.')
        summary='\n'.join(successes[:8]+errors[:8])
        messagebox.showinfo('Toplu işlem sonucu',f'Başarılı: {len(successes)}\nBaşarısız: {len(errors)}\n\n{summary}')

    def change(self,n):
        if not self.src:return
        with fitz.open(self.src) as d:self.page=max(0,min(len(d)-1,self.page+n))
        self.show()
    def show(self):
        if not self.src:return
        try:
            with fitz.open(self.src) as d:self.pg.config(text=f'Sayfa {self.page+1} / {len(d)}')
            self.photos=[]
            for canvas,path in zip(self.panels,(self.src,self.out)):
                canvas.delete('all')
                if not path:
                    canvas.create_text(max(80,canvas.winfo_width()//2),100,text='Henüz temizlenmiş çıktı yok',fill='#555');continue
                with fitz.open(path) as d:
                    page=d[self.page]
                    cw=max(canvas.winfo_width()-18,300);ch=max(canvas.winfo_height()-18,300)
                    scale=min(cw/page.rect.width,ch/page.rect.height,1.8)
                    pix=page.get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False)
                im=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
                photo=ImageTk.PhotoImage(im);self.photos.append(photo)
                canvas.create_image(canvas.winfo_width()//2,canvas.winfo_height()//2,image=photo,anchor='center')
        except Exception as e:self.status.set('Önizleme hatası: '+str(e))

if __name__=='__main__':
    root=tk.Tk();App(root);root.mainloop()
