Akıllı Temizle v1.5 — ücretsiz, çevrimdışı Windows PDF uygulaması

Gereksinimler: Python 3.12
Yerelde: pip install -r requirements.txt pytest
Test: python -m pytest -q tests
Başlat: python arayuz.py

Windows EXE (GitHub Actions):
1. ZIP içindeki dosyaları GitHub deponuzun KÖK dizinine yükleyin.
   .github/workflows/windows-exe.yml dosyasının gizli klasör yapısını koruyun.
2. GitHub > Actions > Windows EXE > Run workflow.
3. Yeşil tamamlanırsa ilgili çalıştırmanın Artifacts bölümünden
   AkilliTemizle-v1.5-Windows ZIP dosyasını indirin.
4. ZIP içindeki AkilliTemizle.exe dosyasını Windows bilgisayarında çalıştırın.

Yalnızca PDF /Watermark açıklamaları kaldırılır. Diğer türler için hata verir.
Orijinal PDF üzerine yazılmaz. Metin doğrulanır; görselleri ayrıca kontrol edin.
GitHub üzerinde EXE derlemesi bu paket hazırlanırken ÇALIŞTIRILMADI.
