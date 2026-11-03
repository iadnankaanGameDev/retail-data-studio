# Architecture
| Area | Modules |
| --- | --- |
| Validation and orchestration | main.py, process_incoming.py |
| SQLite and incremental load | init_db.py, load_sales.py |
| Batch reports / interactive queries | generate_reports.py, reporting.py |
| Desktop and presentation | desktop.py, ui_components.py, combo_box.py, texts.py |
| Projects and restore | projects.py, project_manager.py, projects_view.py, project_backup.py |
| Runtime and filesystem | paths.py, runtime.py, filesystem.py, worker_entry.py |
| Report interface | reports_view.py, report_chart.py (Matplotlib QtAgg) |

The managed project layout has project.json plus data/database, data/raw,
data/incoming, data/processed and data/quarantine. Source runs and packaged runs
have distinct data roots. SQLite schema and backup format are version 1.

All src files match the audited V2.5 development source. Publication-specific
changes are confined to documentation, examples, tests, launch/build helpers and
the spec's virtual-environment allowlist. The source launcher avoids registering
legacy developer database profiles; it does not change ETL or reporting.
