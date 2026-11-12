"""Akıllı Temizle V2.3 — yakınlaştırma, kaydırma ve güvenli alan seçimi."""
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from PIL import Image, ImageTk
import fitz
from motor import clean, mode_for, diagnose, inspect_page, clean_selected


class App:
    def __init__(self, root):
        self.root = root
        self.src = None
        self.out = None
        self.page = 0
        self.photos = []
        self.zoom = 1.0
        self.render_info = None
        self.drag_start = None
        self.selection_rectangle = None
        self.pan_start = None
        self.pan_offset = [0, 0]
        root.title('Akıllı Temizle V2.3 | Güvenli PDF Temizleme')
        root.geometry('1180x780')
        root.minsize(1000, 560)
        root.configure(bg='#f3f6fc')

        bar = ttk.Frame(root, padding=12)
        bar.pack(fill='x')
        self.color_button(bar, '📂 PDF Aç', self.choose, '#1769E0').pack(side='left')
        self.mode = tk.StringVar(value='otomatik')
        ttk.Label(bar, text='  Yöntem:').pack(side='left')
        ttk.Combobox(bar, textvariable=self.mode, values=['otomatik', 'filigran'],
                     width=12, state='readonly').pack(side='left', padx=6)
        self.color_button(bar, '✓ Temizle ve Kaydet', self.process, '#079568').pack(side='left', padx=8)
        self.color_button(bar, 'PDF Teşhisi', self.diagnostics, '#7048D8').pack(side='left', padx=4)
        self.color_button(bar, 'Toplu Temizle', self.batch, '#D86B15').pack(side='left', padx=4)
        self.color_button(bar, 'Manuel Seçim', self.manual, '#C43870').pack(side='left', padx=4)

        self.status = tk.StringVar(value='Bir PDF seçin. Orijinal dosya değiştirilmez.')
        ttk.Label(root, textvariable=self.status, padding=(12, 4)).pack(anchor='w')
        controls = ttk.Frame(root, padding=(12, 4))
        controls.pack(fill='x')
        self.color_button(controls, '◀ Önceki', lambda: self.change(-1), '#455A78').pack(side='left')
        self.pg = ttk.Label(controls, text='Sayfa: —')
        self.pg.pack(side='left', padx=16)
        self.color_button(controls, 'Sonraki ▶', lambda: self.change(1), '#455A78').pack(side='left')
        self.color_button(controls, '− Uzaklaştır', lambda: self.set_zoom(-0.25), '#566B85').pack(side='left', padx=(20, 4))
        self.zoom_label = ttk.Label(controls, text='%100')
        self.zoom_label.pack(side='left', padx=6)
        self.color_button(controls, '+ Yakınlaştır', lambda: self.set_zoom(0.25), '#1769E0').pack(side='left', padx=4)
        self.color_button(controls, 'Ekrana Sığdır', self.reset_zoom, '#455A78').pack(side='left', padx=4)
        self.select_mode = tk.BooleanVar(value=False)
        ttk.Checkbutton(controls, text='Fareyle Watermark seç', variable=self.select_mode).pack(side='left', padx=12)

        ttk.Label(root, text='Kaydırmak için sayfayı fareyle sürükleyin. Filigran seçmek için kutucuğu işaretleyin.', padding=(12, 2)).pack(anchor='w')
        frame = ttk.Frame(root, padding=5)
        frame.pack(fill='both', expand=True)
        self.panels = []
        for title in ('Orijinal PDF', 'Temizlenmiş PDF'):
            pane = ttk.Frame(frame)
            pane.pack(side='left', fill='both', expand=True, padx=2)
            ttk.Label(pane, text=title, font=('Arial', 12, 'bold')).pack()
            canvas = tk.Canvas(pane, bg='#e9edf1', highlightthickness=0)
            canvas.pack(fill='both', expand=True, pady=6)
            canvas.bind('<Configure>', lambda _event: self.show())
            canvas.bind('<ButtonPress-1>', self.start_selection)
            canvas.bind('<B1-Motion>', self.drag_selection)
            canvas.bind('<ButtonRelease-1>', self.end_selection)
            canvas.bind('<MouseWheel>', self.mouse_zoom)
            self.panels.append(canvas)
        ttk.Label(root, text=('Güvenli mod: Yalnızca PDF Watermark açıklamaları kaldırılır. '
                              'Diğer filigran türleri değiştirilmez.'),
                  foreground='#a04a00', padding=10).pack(anchor='w')

    @staticmethod
    def color_button(parent, text, command, color):
        """Windows üzerinde de gerçek arka plan rengi gösteren Tk düğmesi."""
        return tk.Button(
            parent, text=text, command=command, bg=color, fg='white',
            activebackground=color, activeforeground='white',
            font=('Segoe UI', 10, 'bold'), relief='flat', bd=0,
            padx=12, pady=9, cursor='hand2', highlightthickness=0)

    def choose(self):
        filename = filedialog.askopenfilename(title='PDF seç', filetypes=[('PDF', '*.pdf')])
        if not filename:
            return
        try:
            with fitz.open(filename) as doc:
                if doc.needs_pass:
                    raise ValueError('Şifreli PDF desteklenmiyor.')
                count, detected = len(doc), mode_for(doc)
            self.src, self.out, self.page = Path(filename), None, 0
            self.pan_offset = [0, 0]
            self.zoom = 1.0
            self.zoom_label.config(text='%100')
            self.status.set(f'{self.src.name} · {count} sayfa · Algılanan yöntem: {detected}')
            self.show()
        except Exception as exc:
            messagebox.showerror('Dosya açılamadı', str(exc))

    def process(self):
        if self.src is None:
            messagebox.showwarning('PDF seçin', 'Önce PDF açın.')
            return
        destination = filedialog.asksaveasfilename(
            title='Yeni temizlenmiş PDF', defaultextension='.pdf',
            initialfile=self.src.stem + '_temizlenmis.pdf', filetypes=[('PDF', '*.pdf')])
        if not destination:
            return
        try:
            self.root.config(cursor='watch')
            self.root.update_idletasks()
            report = clean(self.src, Path(destination), self.mode.get())
            self.out = Path(destination)
            self.status.set(f"Kaydedildi: {self.out.name} · {report['mod']} · "
                            f"{report['silinen_filigran']} filigran kaldırıldı")
            self.show()
            messagebox.showinfo('İşlem tamamlandı',
                                'PDF ve JSON raporu kaydedildi. Sayfaları karşılaştırarak kontrol edin.')
        except Exception as exc:
            messagebox.showerror('İşlem yapılamadı', str(exc))
        finally:
            self.root.config(cursor='')

    def diagnostics(self):
        if self.src is None:
            messagebox.showwarning('PDF seçin', 'Önce PDF açın.')
            return
        try:
            info = diagnose(self.src)
            messagebox.showinfo('PDF Teşhisi',
                                f"Dosya: {info['dosya']}\nPyMuPDF: {info['pymupdf']}\n"
                                f"Sayfa: {info['sayfa']}\nWatermark: {info['watermark_sayisi']}\n"
                                f"SHA256: {info['sha256']}")
        except Exception as exc:
            messagebox.showerror('Teşhis hatası', str(exc))

    def batch(self):
        paths = filedialog.askopenfilenames(title='PDF dosyalarını seçin', filetypes=[('PDF', '*.pdf')])
        if not paths:
            return
        folder = filedialog.askdirectory(title='Çıktı klasörünü seçin')
        if not folder:
            return
        successes, errors = [], []
        self.root.config(cursor='watch')
        try:
            for index, name in enumerate(paths, 1):
                src = Path(name)
                self.status.set(f'Toplu işlem {index}/{len(paths)}: {src.name}')
                self.root.update_idletasks()
                dest = Path(folder) / (src.stem + '_temizlenmis.pdf')
                try:
                    result = clean(src, dest, 'otomatik')
                    successes.append(f"{src.name}: {result['silinen_filigran']} filigran")
                except Exception as exc:
                    errors.append(f'{src.name}: {exc}')
        finally:
            self.root.config(cursor='')
        self.status.set(f'Toplu işlem: {len(successes)} başarılı, {len(errors)} başarısız.')
        messagebox.showinfo('Toplu işlem sonucu',
                            f'Başarılı: {len(successes)}\nBaşarısız: {len(errors)}\n\n' +
                            '\n'.join(successes[:8] + errors[:8]))

    def manual(self):
        if self.src is None:
            messagebox.showwarning('PDF seçin', 'Önce PDF açın.')
            return
        try:
            data = inspect_page(self.src, self.page)
        except Exception as exc:
            messagebox.showerror('İnceleme hatası', str(exc))
            return
        window = tk.Toplevel(self.root)
        window.title(f'Manuel Watermark seçimi — Sayfa {self.page + 1}')
        window.geometry('680x410')
        ttk.Label(window, text='Yalnızca doğrulanmış Watermark açıklamaları silinebilir.',
                  padding=10).pack(anchor='w')
        lb = tk.Listbox(window, selectmode='extended', width=90, height=10)
        lb.pack(fill='both', expand=True, padx=12)
        marks = data['watermarklar']
        for mark in marks:
            lb.insert('end', f"Watermark · xref={mark['xref']} · konum={mark['konum']}")
        ttk.Label(window, text='Metin adayları (silinmez): ' +
                  (', '.join(data['metin_adaylari']) or 'Yok'),
                  padding=10, wraplength=630).pack(anchor='w')

        def apply():
            indices = lb.curselection()
            if not indices:
                messagebox.showwarning('Seçim yok', 'Listeden bir Watermark seçin.', parent=window)
                return
            dest = filedialog.asksaveasfilename(
                parent=window, title='Yeni PDF kaydet', defaultextension='.pdf',
                initialfile=self.src.stem + '_manuel_temiz.pdf', filetypes=[('PDF', '*.pdf')])
            if not dest:
                return
            try:
                report = clean_selected(self.src, dest,
                                        {self.page: [marks[i]['xref'] for i in indices]})
                self.out = Path(dest)
                self.show()
                self.status.set(f"Manuel temizleme: {report['silinen_filigran']} Watermark kaldırıldı.")
                messagebox.showinfo('Tamamlandı', 'Çıktı kaydedildi. Önizlemeden kontrol edin.',
                                    parent=window)
                window.destroy()
            except Exception as exc:
                messagebox.showerror('İşlem başarısız', str(exc), parent=window)
        ttk.Button(window, text='Seçilen Watermark öğelerini kaldır ve farklı kaydet',
                   command=apply).pack(pady=10)

    def set_zoom(self, amount):
        self.zoom = max(0.5, min(3.0, round(self.zoom + amount, 2)))
        self.zoom_label.config(text=f'%{round(self.zoom * 100)}')
        self.pan_offset = [0, 0]
        self.show()

    def reset_zoom(self):
        self.zoom = 1.0
        self.zoom_label.config(text='%100')
        self.pan_offset = [0, 0]
        self.show()

    def mouse_zoom(self, event):
        if self.src is not None:
            self.set_zoom(0.25 if event.delta > 0 else -0.25)

    def start_selection(self, event):
        if self.src is None:
            return
        if not self.select_mode.get():
            self.pan_start = (event.x, event.y)
            event.widget.config(cursor='fleur')
            return
        if event.widget is not self.panels[0]:
            return
        self.drag_start = (event.x, event.y)
        canvas = self.panels[0]
        if self.selection_rectangle is not None:
            canvas.delete(self.selection_rectangle)
        self.selection_rectangle = canvas.create_rectangle(
            event.x, event.y, event.x, event.y, outline='#E03535', width=2, dash=(5, 3))

    def drag_selection(self, event):
        if self.pan_start is not None:
            dx, dy = event.x - self.pan_start[0], event.y - self.pan_start[1]
            self.pan_start = (event.x, event.y)
            self.pan_offset[0] += dx
            self.pan_offset[1] += dy
            for canvas in self.panels:
                canvas.move('page_image', dx, dy)
            if self.render_info is not None:
                ox, oy, scale = self.render_info
                self.render_info = (ox + dx, oy + dy, scale)
            return
        if self.drag_start is None or self.selection_rectangle is None:
            return
        x, y = self.drag_start
        self.panels[0].coords(self.selection_rectangle, x, y, event.x, event.y)

    def end_selection(self, event):
        if self.pan_start is not None:
            self.pan_start = None
            event.widget.config(cursor='')
            return
        if self.drag_start is None:
            return
        x0, y0 = self.drag_start
        self.drag_start = None
        if self.selection_rectangle is not None:
            self.panels[0].delete(self.selection_rectangle)
            self.selection_rectangle = None
        info = self.render_info
        if not info or abs(event.x - x0) < 5 or abs(event.y - y0) < 5:
            return
        ox, oy, scale = info
        region = fitz.Rect((min(x0, event.x)-ox)/scale,
                           (min(y0, event.y)-oy)/scale,
                           (max(x0, event.x)-ox)/scale,
                           (max(y0, event.y)-oy)/scale)
        try:
            data = inspect_page(self.src, self.page)
            matches = [m for m in data['watermarklar']
                       if fitz.Rect(m['konum']).intersects(region)]
            if not matches:
                messagebox.showinfo('Watermark bulunamadı',
                                    'Seçilen alanda doğrulanmış PDF Watermark açıklaması yok. Hiçbir içerik silinmedi.')
                return
            if not messagebox.askyesno('Seçimi onaylayın',
                    f'{len(matches)} doğrulanmış Watermark açıklaması bulundu.\n'
                    'Yalnızca bu açıklamalar kaldırılsın mı?'):
                return
            dest = filedialog.asksaveasfilename(
                title='Seçilen Watermark öğelerini farklı kaydet',
                defaultextension='.pdf',
                initialfile=self.src.stem + '_secim_temiz.pdf',
                filetypes=[('PDF', '*.pdf')])
            if not dest:
                return
            report = clean_selected(
                self.src, Path(dest), {self.page: [m['xref'] for m in matches]})
            self.out = Path(dest)
            self.status.set(f"Alan seçimi: {report['silinen_filigran']} Watermark kaldırıldı.")
            self.show()
            messagebox.showinfo('Tamamlandı', 'Yeni PDF kaydedildi. Orijinal dosya korunmuştur.')
        except Exception as exc:
            messagebox.showerror('Seçim hatası', str(exc))

    def change(self, amount):
        if self.src is None:
            return
        with fitz.open(self.src) as doc:
            self.page = max(0, min(len(doc) - 1, self.page + amount))
        self.pan_offset = [0, 0]
        self.show()

    def show(self):
        if self.src is None:
            return
        try:
            with fitz.open(self.src) as doc:
                self.pg.config(text=f'Sayfa {self.page + 1} / {len(doc)}')
            self.photos = []
            self.render_info = None
            for canvas, path in zip(self.panels, (self.src, self.out)):
                canvas.delete('all')
                if path is None:
                    canvas.create_text(max(80, canvas.winfo_width() // 2), 100,
                                       text='Henüz temizlenmiş çıktı yok', fill='#555')
                    continue
                with fitz.open(path) as doc:
                    page = doc[self.page]
                    cw = max(canvas.winfo_width() - 18, 300)
                    ch = max(canvas.winfo_height() - 18, 300)
                    scale = min(cw / page.rect.width, ch / page.rect.height, 1.8) * self.zoom
                    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                im = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
                photo = ImageTk.PhotoImage(im)
                self.photos.append(photo)
                center_x = canvas.winfo_width() // 2 + self.pan_offset[0]
                center_y = canvas.winfo_height() // 2 + self.pan_offset[1]
                canvas.create_image(center_x, center_y, image=photo, anchor='center', tags='page_image')
                if canvas is self.panels[0]:
                    self.render_info = (center_x - pix.width / 2,
                                        center_y - pix.height / 2, scale)
        except Exception as exc:
            self.status.set('Önizleme hatası: ' + str(exc))


if __name__ == '__main__':
    root = tk.Tk()
    App(root)
    root.mainloop()
