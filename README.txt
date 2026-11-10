AKILLI TEMIZLE v1.7 — UCRETSIZ / REKLAMSIZ

Yenilikler:
- Pencere basliginda v1.7 surumu
- PDF Teshisi: dosya yolu, SHA256, PyMuPDF surumu, Watermark sayisi
- Toplu Temizle: birden fazla PDF icin ayri cikti ve JSON raporu
- Orijinal PDF uzerine yazmaz; var olan ciktiyi de degistirmez.

Sinir: yalnizca PDF /Watermark aciklamalarini kaldirir.
Diger filigran tiplerinde dosyayi degistirmez.

GitHub: motor.py, arayuz.py, requirements.txt ve tests/test_motor.py dosyalarini
ilgili konumlara yukleyin. .github/workflows/windows-exe.yml dosyasini da
istege bagli guncelleyin. Eski EXE kisayolu yeni surume otomatik gecmez.

Windows EXE derlemesi burada yapilmadi. GitHub Actions ile olusturulabilir.
