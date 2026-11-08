AKILLI TEMIZLE v1.0 - WINDOWS 10 64 BIT DERLEME PAKETI

Bu ZIP bir EXE DEGILDIR. Kaynak kodu ve Windows EXE olusturma tarifi icerir.
Windows bilgisayarinizda Python kurulu olmasina gerek kalmadan GitHub Actions
ile bulutta EXE derleyebilirsiniz. Bunun icin GitHub hesabi ve internet gerekir.

GITHUB UZERINDEN EXE OLUSTURMA
1. GitHub'da yeni, tercihen PRIVATE bir repository olusturun.
2. ZIP'in ICINDEKI tum dosyalari, .github klasoru dahil, repository kokune yukleyin.
   Not: GitHub web arayuzunde gizli klasor yuklemek zor olabilir; bu durumda
   .github/workflows/windows-exe.yml dosyasini GitHub web arayuzunden olusturun.
3. Actions sekmesinde 'Windows 10 compatible EXE (x64)' is akisina gidin.
4. Run workflow tusuna basin.
5. Islem basarili olursa run sayfasinin Artifacts bolumunden
   'AkilliTemizle-Windows-x64' ZIP'ini indirin.
6. ZIP icindeki AkilliTemizle.exe dosyasini Windows 10 64 bit PC'de acin.

UYARILAR
- Bu ortamda Windows EXE derlenmedi veya Windows 10'da test edilmedi.
- GitHub Actions Windows Server 2022 ortaminda derler; Windows 10 uyumlulugu
  ayrica gercek Windows 10 cihazda test edilmelidir.
- Sadece guvendiginiz kodlari calistirin. Dosyalarinizi GitHub'a yuklemeniz
  gerekmez; PDF temizleme islemi uygulama icinde yerel calisir.
- Nesne modu yalnizca belirli COOLMATEMATIK filigran yapisini destekler.
- Goruntu modu acik renkli cizgileri de silebilir. Ciktilari tek tek kontrol edin.
- Kaynak dosya ve var olan cikti dosyalari degistirilmez.
- Uygulama ucretsiz ve reklamsizdir; GitHub hizmetinin kendi kosullari ayridir.
