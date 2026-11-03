"""Central Turkish UI vocabulary. Stable keys allow future locale dictionaries."""
TR = {
    "nav.import": "CSV İçe Aktar", "nav.reports": "Raporlar", "nav.projects": "Projeler",
    "project.details": "Proje ayrıntıları", "project.create": "Yeni Proje Oluştur",
    "project.title": "Projeler", "project.subtitle": "Bağımsız veritabanları, kataloglar ve raporlarla satış çalışma alanlarınızı yönetin.",
    "project.name": "Proje adı", "project.products": "Ürün kataloğu CSV", "project.stores": "Mağaza kataloğu CSV",
    "project.choose": "CSV seç", "project.activate": "Projeye geç",
    "project.active": "Aktif proje", "project.template": "Sales ETL Template",
    "project.notice": "Oluştur düğmesi, seçtiğiniz katalogların projeye özel kopyalarını ve boş bir satış veritabanını oluşturur. Başka projelerden satış kopyalanmaz.",
    "project.created": "Proje oluşturuldu. Boş veritabanı hazır; CSV İçe Aktar sayfasından satış yükleyebilirsiniz.",
    "project.creating": "Proje hazırlanıyor…",
    "import.choose": "CSV dosyası seç", "import.start": "İşlemi başlat", "import.outputs": "Çıktıları aç",
    "reports.apply": "Filtreleri uygula", "reports.export": "CSV kaydet", "reports.open": "Klasörü aç",
}


def tr(key):
    return TR[key]
