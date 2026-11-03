"""Project definitions; new pipelines can be registered without changing the UI."""
from dataclasses import dataclass
from pathlib import Path
from paths import BASE_DIR
from runtime import FROZEN


@dataclass(frozen=True)
class Project:
    key: str
    name: str
    root: Path
    description: str
    database_relative: str = "data/database/sales.db"
    output_relative: str = "data/processed/desktop_runs"
    pipeline_root: Path | None = None
    managed: bool = False
    template: str = "sales_etl_v1"

    @property
    def database(self):
        return self.root / self.database_relative

    @property
    def output_root(self):
        return self.root / self.output_relative

    @property
    def entrypoint(self):
        return (self.pipeline_root or self.root) / "src/main.py"

    @property
    def reference_dir(self):
        return self.root / "data/raw"

    @property
    def incoming_dir(self):
        return self.root / "data/incoming"

    @property
    def quarantine_dir(self):
        return self.root / "data/quarantine"


PROJECTS = (
    Project("toy-sales", "Toy Sales", BASE_DIR,
            "Oyuncak satışları • Doğrulama, artımlı yükleme ve satış raporları"),
    Project("toy-sales-demo", "Toy Sales Demo", BASE_DIR,
            "Demo ortamı • Gerçek satış veritabanından bağımsız",
            "data/database/customer_demo.db", "data/processed/customer_demo"),
)
if FROZEN:
    PROJECTS = ()  # Customer packages never register developer databases.
