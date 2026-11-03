# Retail Data Studio

A Windows desktop application for repeatable retail sales imports, isolated SQLite projects and practical reporting. Version 2.5 uses Python 3.12, pandas, PySide6 / Qt Widgets and Matplotlib QtAgg. Packaging uses PyInstaller and Inno Setup.

**Commercial redistribution has not received final license clearance.** See [license status](docs/FINAL_LICENSE_STATUS.md). No application source-code license has been selected. EXE and Setup files are not part of this source repository.

## Features

- Validate sales CSV files against product and store catalogs; separate rejected rows.
- Import incrementally by Sale_ID: skip identical records and report conflicting values.
- Keep separate projects with their own catalogs, SQLite database and outputs.
- Filter reports by date, store and category; aggregate by period and export CSV.
- Back up a project to `.rdsbackup` and restore it as a new project with a new ID.

This application supports the **Sales ETL schema below**. It is not a general-purpose ETL tool for arbitrary CSV layouts.

## Run from source

Use Windows 10/11 x64 and Python 3.12. In this repository's directory:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe scripts/run_studio.py
```

Alternatively, run `setup.bat`, then `run_gui.bat`. The source launcher exposes managed projects without opening legacy development database profiles. Source projects are stored in the ignored `data/projects/` directory. Keep your own backups outside a project's directory. Existing local data is not example data and must not be committed.

## CSV schema

Use UTF-8 CSV files with comma separators and these headers:

| File | Required columns | Optional descriptive columns |
| --- | --- | --- |
| `products.csv` | `Product_ID,Product_Category,Product_Price,Product_Cost` | `Product_Name` |
| `stores.csv` | `Store_ID,Store_Name` | `Store_Location` |
| Sales CSV | `Sale_ID,Date,Store_ID,Product_ID,Units` | — |

IDs are positive integers; catalog IDs must be unique. Sales must reference existing products and stores. Units must be positive whole numbers. Dates use `YYYY-MM-DD`. Prices use a period decimal separator and may have a `$` prefix. Use one currency per project.

Estimated revenue is units multiplied by the **current catalog price**. It is not a record of receipts, taxes, discounts or accounting revenue.

## Try the synthetic examples

1. Open **Projeler** and create a project using `examples/products.csv` and `examples/stores.csv`.
2. Open **CSV İçe Aktar**, select `examples/sales_sample.csv`, and start processing.
3. Open **Raporlar**, select **Tüm zamanlar**, and apply the filters.
4. Expect **6 transactions, 14 units and 174.25 estimated revenue**.
5. Import the same sales file again: **0 new records** should be added.
6. Export a report; use **Backup Project**, then **Restore Project** with a new name and compare the totals.

All example names, IDs and values are synthetic. The interface primarily uses Turkish navigation with English Backup/Restore labels. See [Quick Start](docs/QUICK_START.md).

## Backup and restore

A backup includes a consistent SQLite snapshot, catalogs, project configuration, version metadata and integrity hashes. Restore creates a separate project and does not overwrite the original. Input CSVs, logs, quarantine, operation history and previous report exports are excluded. Reports can be regenerated; backups are not encrypted. See [backup scope](docs/BACKUP_RESTORE_V24.md).

## Development and packaging

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

The tests use synthetic temporary projects. A focused end-to-end example check is:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_synthetic_example.py -q
```

For a future local Windows build, install `requirements-build.txt` and run `build_portable.bat`. See [packaging](docs/PACKAGING.md). Build outputs, virtual environments, private data and local acceptance evidence are excluded by `.gitignore`. The existing accepted Setup is kept separately in the customer delivery folder; do not commit executable distributions to GitHub.

## Limitations and licensing

This is a local desktop application, not a multi-user server or accounting system. There is no automatic cloud sync or application updater. Native Windows dialogs and physical display scaling have a separate manual verification scope.

The Qt/PySide6 LGPL source and notice supplement is prepared, but remaining build-source, library-replacement evidence and legal conditions are documented in [the closure report](docs/LICENSE_CLOSURE.md). No commercial Qt entitlement is assumed. The owner must decide the license and publication rights for their own source code before a public release. No GitHub push has been performed.
