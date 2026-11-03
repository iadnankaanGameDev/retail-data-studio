# Günlük satış simülasyonu

Bu veri seti tamamen sentetiktir. Gerçek müşteri hareketlerini temsil etmez.
Mevcut ürün/mağaza kataloglarından yalnızca kimlik, kategori, konum ve fiyat
bilgileri okunmuştur; mevcut satış geçmişi üretimde kullanılmamıştır.

## Dosyalar ve beklenen sonuçlar

Konum: `data/demo_batches/daily_sales_simulation/`

| Yükleme sırası / dosya | Satış kaydı | Adet | Estimated Revenue (USD) |
| --- | ---: | ---: | ---: |
| sales_history_seed.csv | 4053 | 7142 | 105134.58 |
| sales_2026-10-20.csv | 51 | 86 | 1312.14 |
| sales_2026-10-21.csv | 57 | 97 | 1440.03 |
| sales_2026-10-22.csv | 49 | 82 | 1209.18 |
| sales_2026-10-23.csv | 50 | 90 | 1401.10 |
| sales_2026-10-24.csv | 68 | 123 | 1781.77 |
| sales_2026-10-25.csv | 67 | 115 | 1813.85 |
| sales_2026-10-26.csv | 58 | 99 | 1476.01 |
| **Tümü** | **4453** | **7834** | **115568.66** |

Geçmiş dosyası 1 Ağustos–19 Ekim 2026 arasındaki 80 günü kapsar. Sonraki yedi
dosya yalnız kendi gününü içerir. Toplam 87 gün vardır; her gün 36–73 satış
kaydı bulunur. 50 mağaza, 35 ürün ve 5 kategorinin tamamı temsil edilir.

Kontrol CSV'leri uygulamaya satış dosyası olarak yüklenmez:

- `expected_results.csv`: sekiz dosyanın ayrı tarih aralıkları ve toplamları.
- `expected_totals.csv`: tüm dosyalar yüklendikten sonraki toplamlar ve aktif mağaza sayısı.
- `expected_after_each_load.csv`: her yüklemeden sonraki kümülatif KPI değerleri.
- `expected_daily.csv`, `expected_weekly.csv`, `expected_monthly.csv`,
  `expected_quarterly.csv`: bütün veri setinin dönem özetleri.
- `expected_stores.csv`, `expected_categories.csv`: bütün veri setinin mağaza/kategori özetleri.
- `manifest.json`: seed, kaynak katalog SHA-256 değerleri ve çıktı dosyası hash'leri.
- `validation_report.json`: dosyalardan yeniden hesaplanan doğrulama sonuçları.

CSV sütunu `Estimated_Revenue`, Reports ekranındaki `Estimated Revenue`
değerine karşılık gelir. Hesaplama güncel katalog fiyatı × satılan adettir;
tarihsel fiyat, net kâr veya gerçek muhasebe geliri değildir. Hesaplar kuruş
tam sayılarıyla yapılır ve bağımsız Decimal hesaplarıyla karşılaştırılır.

Haftalar pazartesi başlar. Haftalık ilk etiket **2026-07-27** olabilir;
bu grupta yalnız 1–2 Ağustos satışları vardır. Üç aylık etiket **2026-07-01**,
Q3 başlangıcını belirtir; Temmuz satışı üretilmemiştir. Q3 toplamı 3106 kayıt,
5477 adet, 80678.23 USD; kısmi Q4 toplamı 1347 kayıt, 2357 adet, 34890.43 USD'dir.

## Uygulamada kullanım

1. Proje klasöründe `run_gui.bat` çalıştırın.
2. **Projeler** sayfasından **Retail Sales Simulation** adlı yeni bir
   **Sales ETL Template** projesi oluşturun.
3. Ürün için `data/raw/products.csv`, mağaza için `data/raw/stores.csv` seçin.
   Project Manager katalogların projeye özel kopyalarını ve boş bir veritabanını
   oluşturur. Aktif projenin **Retail Sales Simulation** olduğunu kontrol edin.
4. **CSV İçe Aktar** sayfasından `sales_history_seed.csv` dosyasını seçip
   **İşlemi başlat** düğmesine basın. Beklenen: Accepted=4053, Rejected=0,
   New records=4053, Already present=0.
5. 20, 21, 22, 23, 24, 25, 26 Ekim dosyalarını bu sırayla yükleyin. İlk kez
   yüklenen her dosyada New records dosyanın kayıt sayısı, Rejected=0 ve
   Already present=0 olmalıdır.
6. Her yüklemeden sonra **Raporlar** sayfasında tarih **Tüm zamanlar**, mağaza
   ve kategori **Tümü** seçiliyken **Filtreleri uygula** düğmesine basın.
   KPI'ları `expected_after_each_load.csv` ile karşılaştırın. Örneğin 20 Ekim
   yüklendikten sonra 4104 kayıt, 7228 adet ve 106446.72 USD beklenir.
7. Tüm dosyalar bittikten sonra **aynı 26 Ekim dosyasını değiştirmeden tekrar
   yükleyin**. Beklenen: Accepted=58, Rejected=0, New records=0,
   Already present=58. Toplamlar 4453 / 7834 / 115568.66 olarak kalmalıdır.
   Farklı içerikle aynı Sale_ID kullanılması mükerrer değil çakışma testidir;
   bu veri setindeki günlük dosyalar birbirleriyle çakışmaz.
8. Gruplamayı günlük, haftalık, aylık ve üç aylık olarak değiştirip dönem
   tablolarını ilgili `expected_*.csv` ile karşılaştırın. Sabit karşılaştırma
   için **Tüm zamanlar** veya özel **2026-08-01–2026-10-26** aralığını kullanın.
   **Bu ay / Son 7 gün** gibi seçenekler bilgisayarın bugünkü tarihine bağlıdır.
9. Tek mağaza veya kategori seçip KPI'ları `expected_stores.csv` veya
   `expected_categories.csv` içindeki ilgili satırla karşılaştırın. Bu dosyalar
   tüm tarih aralığına aittir; ek tarih filtresi veya mağaza+kategori birleşimi
   için doğrudan toplam olarak kullanılmamalıdır. Gerekirse **CSV kaydet** ile
   Reports çıktısını dışarı alın.

Bu görev sırasında uygulamada proje oluşturulmamış ve hiçbir veri tabanına
satış yüklenmemiştir. Yukarıdaki işlemler kullanıcı tarafından yapılacak test
senaryosudur. Gerçek Toy Sales veya Toy Sales Demo profiline yükleme yapmayın.

## Yeniden üretme ve yalnız doğrulama

```powershell
.\.venv\Scripts\python.exe scripts\generate_daily_sales_demo.py
.\.venv\Scripts\python.exe scripts\generate_daily_sales_demo.py --validate-only
```

Üretici yalnız Python standart kütüphanesine ihtiyaç duyar. Varsayılan seed
**20261026**, ilk Sale_ID **202608010001**'dir. Aynı betik, Python sürümü,
kataloglar ve seed ile dosyalar byte düzeyinde aynıdır. Sıralı kimlikler sekiz
dosyanın tamamında benzersizdir; mevcut başka veritabanlarıyla benzersizlik
iddiası yoktur, bu nedenle boş bağımsız proje kullanılır.

Model varsayımları: mağaza konumu ve sabit rastgele ağırlıklar satış hacmini,
ürün ağırlıkları ve fiyat seviyesi satış sıklığını etkiler. Cumartesi için
1.32, pazar için 1.20 hedef hacim çarpanı uygulanır; günlük gürültü ve hafif
zaman eğilimi vardır. Adetler çoğunlukla 1–2, daha seyrek 3–6'dır. Bunlar
gerçek işletme verisinden kalibre edilmiş oranlar değildir. Üretilen seride
hafta içi ortalama 47.72, hafta sonu ortalama 59.31 kayıt bulunur.

`--seed`, `--reference-dir` ve `--output-dir` seçenekleri mevcuttur.
Farklı seed/katalog kullanıldığında kontrol toplamları değişir; bu rehberdeki
sabit örnekler varsayılan üretime aittir. Yükleme yaptıktan sonra aynı projeye
farklı seed ile üretilmiş aynı kimlikleri yüklemeyin; yeni proje kullanın.
Kaynak fiyatı değişirse Estimated Revenue karşılaştırması da değişir.

Var olan çıktıların hash'leri önceki manifest ile uyuşuyorsa tekrar üretime
izin verilir. Üreticiye ait olmayan veya elle değiştirilmiş hedef dosyalar
üzerine yazılmaz. Böyle bir durumda farklı, boş bir çıktı klasörü seçin.
`--validate-only` hiçbir dosya yazmaz ve katalog/çıktı hash'lerini de kontrol eder.

Dosya bazlı test komutu (veritabanı oluşturmaz veya yüklemez):

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_daily_sales_demo.py
```
