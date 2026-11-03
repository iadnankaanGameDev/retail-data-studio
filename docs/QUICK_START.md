# Quick start
The current desktop UI uses Turkish navigation with English Backup/Restore labels.

1. Run the V2.5 Setup on Windows 10/11 x64. No Python is needed for the installer.
2. Open Retail Data Studio from the Start menu.
3. Open **Projeler** (Projects), enter a name, select `products.csv` and `stores.csv`
   from the synthetic examples, and click **Yeni Proje Oluştur** (Create project).
4. Use **CSV İçe Aktar** (CSV Import), choose `sales_sample.csv`, then **İşlemi başlat**.
5. Open **Raporlar** (Reports), choose **Tüm zamanlar** (All time), then
   **Filtreleri uygula**. Expect 6 transactions, 14 units and 174.25 estimated revenue.
6. **CSV kaydet** exports reports. **Klasörü aç** opens the export folder.
7. In Projects select the managed project and use **Backup Project**. Read the
   scope confirmation and save the `.rdsbackup` outside the project folder.
8. **Restore Project** opens a backup and asks for a project name. It creates a
   new project ID and does not overwrite the original. Reimport adds zero new rows.

Installed projects: `%LOCALAPPDATA%\RetailDataStudio\RetailDataStudio\data\projects`.
Uninstalling keeps project data. Source runs store projects in this checkout's
ignored `data/projects` directory. Backups contain a SQLite snapshot, catalogs,
settings and integrity metadata. Input CSVs, logs, quarantine, operation history
and previous report exports are excluded. Backups are not encrypted.
