# Retail Data Studio V2.5 — Kurulum ve veri güvenliği

`RetailDataStudio-Setup-v2.5.exe` dosyasını çalıştırın. Varsayılan kurulum yalnızca
geçerli Windows kullanıcısı içindir; yönetici yetkisi, Python veya VS Code gerekmez.
Başlat menüsünde Retail Data Studio oluşur. Masaüstü kısayolu isteğe bağlıdır.
Kurulumun sonunda uygulamayı başlatabilirsiniz.

Program konumu: `%LOCALAPPDATA%\Programs\RetailDataStudio`

Proje konumu değişmedi:
`%LOCALAPPDATA%\RetailDataStudio\RetailDataStudio\data\projects`

Program dosyalarını bu proje dizinine kurmayın. Kurulum bu dizinle örtüşen hedefleri
reddeder. Açık GUI veya worker varsa güncelleme/kaldırma uygulamanın kapanmasını
ister; ETL işlemleri zorla sonlandırılmaz. Kullanıcı tarafından ayrıca ayarlanmış
`RDS_DATA_HOME` varsa önceki sürümle aynı ayarı kullanın.

## Güncelleme ve kaldırma

Güncellemeden önce Projects → Backup Project ile yedek alın, etkin işlemleri
tamamlayıp uygulamayı kapatın. Yeni Setup dosyasını aynı Windows hesabıyla çalıştırın.
Sabit AppId ve kurulum dizini önceki kurulumun güncellenmesini sağlar.

Windows Ayarlar → Uygulamalar üzerinden Retail Data Studio'yu kaldırabilirsiniz.
Kaldırıcı yalnızca kurduğu program dosyaları ve kısayolları kaldırır; projeleri,
SQLite veritabanlarını ve yedekleri otomatik silmez. Kullanıcı verilerini taşıyan,
sıfırlayan veya silen bir kurulum/kaldırma betiği yoktur.

V2.5 veritabanı şeması ve proje schema_version=1 değişmedi. V2.4 projeleri doğrudan
açılır; yedek format_version=1 korunur. application_version alanı yeni yedeklerde
2.5 olur. Restore yeni bir UUID üretir ve mevcut projelerin üzerine yazmaz.
Bu sürümde migration çalıştırılmaz. İleride şema değişirse uygulama önce SQLite
backup API ile yedek almalı, transaction içinde sürümlü migration yapmalı ve
integrity_check başarısızsa yayımlamamalıdır; migration uygulanmadan eski şema
dosyaları yerinde korunmalıdır.

## Backup & Restore

Projects → projeyi seç → Backup Project → kapsamı onayla → yeni `.rdsbackup`
dosyasını proje klasörü dışında kaydet. Restore Project → yedeği seç → farklı
bir ad gir → Reports ekranında verileri kontrol et.

| İçerik | Yedekte |
|---|---|
| SQLite satış kayıtları (backup API snapshot) | Evet |
| Ürün/mağaza katalogları | Evet |
| Proje ayarları, restore metadata, sürüm ve SHA-256 manifesti | Evet |
| İşlem geçmişi, loglar, girdi CSV'leri, karantina | Hayır |
| Eski raporlar ve dışa aktarımlar | Hayır |

Arşiv: `manifest.json`, `project.json`, `data/database/sales.db`,
`data/raw/products.csv`, `data/raw/stores.csv`. Raporlar yeniden üretilebilir.
Yedek tam çalışma klasörü kopyası veya şifreli arşiv değildir.

## Arayüz ve manuel kabul

Sidebar ve rapor dropdown'ları açıkça tanımlanmış normal/hover/selected/focused/
disabled renklerini kullanır. Yerel Windows seçim paleti popup metnini geçersiz
kılamaz. Uzun adlar ortadan kısaltılır, tam ad tooltip'te tutulur.

Windows üzerinde %100/%125/%150 Qt ölçeğinde render kontrolleri yapılmıştır.
Fiziksel monitörün Windows ölçek ayarı bu otomasyonla değiştirilmez. Müşteri
ortamında bu üç ölçekte gerçek dropdown açılması, klavye/hover/focus davranışı,
Türkçe karakterler ve tooltip görünürlüğü ayrıca kontrol edilmelidir.
Native Windows dosya seçicileri için de manuel Backup/Restore kabulü gereklidir.

Bu dağıtım kod imzalama sertifikası sağlanmadığı için imzasızdır. Windows
SmartScreen/kurum politikaları uyarı gösterebilir. Sertifika ve üretim imzalama
işlemi bu çalışma kapsamında temin edilmez.

## Derleme yöntemi

Inno Setup 7.1.1: tek Setup EXE, per-user kurulum, isteğe bağlı kısayollar ve
Windows kaldırma kaydı sağladığı için seçildi. Derleyici resmi kaynaktan alındı
ve Pyrsys B.V. Authenticode imzası doğrulandı.

- https://jrsoftware.org/isdl.php
- https://jrsoftware.org/ishelp/topic_setup_privilegesrequired.htm
- https://jrsoftware.org/ishelp/topic_setup_uninstallable.htm

PyInstaller çıktısı ayrı `dist/RetailDataStudio-V2.5-RC1-20261030` konumundadır.
Derleme: `RetailDataStudio.spec`, kurulum: `installer/RetailDataStudio.iss`.
ISCC'ye `/DBundleDir=<doğrulanmış paket>` ve `/DReleaseDir=<yeni çıktı klasörü>` verin.
Eski portable paketlerin üzerine çıktı üretmeyin.
