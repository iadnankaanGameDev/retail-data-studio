"""End-to-end check of the public example using temporary project data only."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from project_manager import create_project
from reporting import query_report, ReportFilter, export_report
from project_backup import backup_project, restore_project

ROOT = Path(__file__).resolve().parents[1]

def test_public_example(tmp_path):
    examples = ROOT / "examples"
    project = create_project("Synthetic showcase", examples / "products.csv",
                             examples / "stores.csv", tmp_path / "projects")
    source = project.incoming_dir / "sales_sample.csv"
    shutil.copy2(examples / source.name, source)
    for attempt, expected in ((1, 6), (2, 0)):
        output = project.output_root / str(attempt)
        result = subprocess.run([sys.executable, str(project.entrypoint), source.name,
            "--incoming-dir", str(project.incoming_dir), "--reference-dir", str(project.reference_dir),
            "--db-path", str(project.database), "--output-dir", str(output),
            "--quarantine-dir", str(project.quarantine_dir / str(attempt)),
            "--log-dir", str(output / "logs")], cwd=tmp_path, capture_output=True,
            text=True, encoding="utf-8", errors="replace")
        assert result.returncode == 0, result.stdout + result.stderr
        summary = json.loads((output / "sales_sample_load_summary.json").read_text(encoding="utf-8"))
        assert summary["new_records"] == expected
        assert (output / "store_daily_summary.csv").is_file()
    report = query_report(project, ReportFilter())
    assert report.totals == {"Transactions": 6, "Units_Sold": 14, "Estimated Revenue": 174.25}
    before = project.database.read_bytes()
    archive = tmp_path / "example.rdsbackup"
    backup_project(project, archive)
    restored = restore_project(archive, "Restored showcase", tmp_path / "projects")
    assert restored.key != project.key
    assert query_report(restored, ReportFilter()).totals == report.totals
    assert project.database.read_bytes() == before
