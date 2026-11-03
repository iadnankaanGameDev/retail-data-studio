"""Read-only reporting, independent of Qt and the ETL entry points."""
from calendar import monthrange
from contextlib import closing
from dataclasses import asdict, dataclass
from datetime import date, timedelta, datetime
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import sqlite3
from uuid import uuid4
from filesystem import fs_path, readonly_uri, display_path

import pandas as pd


PRESETS = ("Son 7 gün", "Bu ay", "Son 3 ay", "Son 12 ay", "Bu yıl",
           "Tüm zamanlar", "Özel tarih aralığı")
GROUPINGS = {"Günlük": "D", "Haftalık": "W-SUN", "Aylık": "M",
             "Üç aylık": "Q-DEC", "Yıllık": "Y-DEC"}
METRICS = ["Transactions", "Units_Sold", "Estimated Revenue"]


def date_range(preset, today=None):
    """Inclusive calendar ranges; rolling months end today, not at month end."""
    today = today or date.today()
    if preset == "Tüm zamanlar":
        return None, None
    if preset == "Son 7 gün":
        return today - timedelta(days=6), today
    if preset == "Bu ay":
        return today.replace(day=1), today
    if preset == "Bu yıl":
        return today.replace(month=1, day=1), today
    if preset in ("Son 3 ay", "Son 12 ay"):
        months = 3 if preset == "Son 3 ay" else 12
        index = today.year * 12 + today.month - 1 - months
        year, month = divmod(index, 12)
        start = date(year, month + 1, min(today.day, monthrange(year, month + 1)[1]))
        return start + timedelta(days=1), today
    raise ValueError("Bilinmeyen tarih filtresi")


@dataclass(frozen=True)
class ReportFilter:
    start: date | None = None
    end: date | None = None
    grouping: str = "Aylık"
    store_id: int | None = None
    category: str | None = None

    def validate(self):
        if self.start and self.end and self.start > self.end:
            raise ValueError("Başlangıç tarihi bitiş tarihinden sonra olamaz.")
        if self.grouping not in GROUPINGS:
            raise ValueError("Geçersiz gruplama")


@dataclass
class ReportResult:
    project_key: str
    project_name: str
    database: str
    filters: ReportFilter
    generated_at: str
    totals: dict
    periods: pd.DataFrame
    categories: pd.DataFrame
    stores: pd.DataFrame
    store_options: list
    category_options: list


def open_readonly(database):
    # mode=ro also prevents SQLite from silently creating a missing database.
    connection = sqlite3.connect(readonly_uri(database), uri=True)
    connection.execute("PRAGMA query_only = ON")
    return connection


def price_cents(value):
    try:
        price = Decimal(str(value).replace("$", "").replace(",", "").strip())
        if not price.is_finite() or price < 0 or price * 100 != (price * 100).to_integral_value():
            raise ValueError("Ürün fiyatı negatif, eksik veya kuruş hassasiyetine uygun değil.")
        return int(price * 100)
    except InvalidOperation as exc:
        raise ValueError(f"Geçersiz ürün fiyatı: {value}") from exc


def catalog(project):
    raw = fs_path(project.reference_dir)
    products = pd.read_csv(raw / "products.csv", dtype={"Product_Price": "string"})
    stores = pd.read_csv(raw / "stores.csv")
    for frame, required, key in (
        (products, ["Product_ID", "Product_Category", "Product_Price"], "Product_ID"),
        (stores, ["Store_ID", "Store_Name"], "Store_ID"),
    ):
        if not set(required).issubset(frame.columns):
            raise ValueError(f"Katalog kolonları eksik: {', '.join(required)}")
        if frame[required].isna().any().any() or frame[key].duplicated().any():
            raise ValueError(f"Katalogda eksik değer veya mükerrer {key} var.")
    products = products[["Product_ID", "Product_Category", "Product_Price"]].copy()
    products["Price_Cents"] = products["Product_Price"].map(price_cents)
    return products, stores[["Store_ID", "Store_Name"]]


def summarize(frame, keys):
    if frame.empty:
        return pd.DataFrame(columns=keys + METRICS)
    result = frame.groupby(keys, as_index=False, sort=True).agg(
        Transactions=("Transactions", "sum"), Units_Sold=("Units_Sold", "sum"),
        Revenue_Cents=("Revenue_Cents", "sum"))
    result["Estimated Revenue"] = result.pop("Revenue_Cents") / 100
    return result


def query_report(project, filters):
    filters.validate()
    if not fs_path(project.database).is_file():
        raise FileNotFoundError(f"Veritabanı bulunamadı: {project.database}. Otomatik oluşturulmaz.")
    products, stores = catalog(project)
    clauses, params = [], []
    for boundary, operator in ((filters.start, ">="), (filters.end, "<=")):
        if boundary:
            clauses.append(f"Date {operator} ?")
            params.append(boundary.isoformat())
    if filters.store_id is not None:
        clauses.append("Store_ID = ?")
        params.append(filters.store_id)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    with closing(open_readonly(project.database)) as connection:
        sales = pd.read_sql_query(
            "SELECT Date, Store_ID, Product_ID, COUNT(*) AS Transactions, "
            "SUM(Units) AS Units_Sold FROM sales" + where +
            " GROUP BY Date, Store_ID, Product_ID", connection, params=params)
    store_options = [(int(row.Store_ID), str(row.Store_Name))
                     for row in stores.sort_values("Store_Name").itertuples()]
    category_options = sorted(products["Product_Category"].astype(str).unique().tolist())
    sales = sales.merge(products, on="Product_ID", how="left", validate="many_to_one")
    sales = sales.merge(stores, on="Store_ID", how="left", validate="many_to_one")
    if sales[["Price_Cents", "Product_Category", "Store_Name"]].isna().any().any():
        raise ValueError("Satışlarda katalogla eşleşmeyen ürün/mağaza var; eksik gelir raporlanmadı.")
    if filters.category is not None:
        sales = sales.loc[sales["Product_Category"] == filters.category].copy()
    # Integer cents avoid floating point accumulation in financial totals.
    sales["Revenue_Cents"] = sales["Units_Sold"] * sales["Price_Cents"]
    if not sales.empty:
        dates = pd.to_datetime(sales["Date"], format="%Y-%m-%d", errors="raise")
        sales["Period"] = dates.dt.to_period(GROUPINGS[filters.grouping]).dt.start_time.dt.strftime("%Y-%m-%d")
    else:
        sales["Period"] = pd.Series(dtype="str")
    totals = {"Transactions": int(sales["Transactions"].sum()),
              "Units_Sold": int(sales["Units_Sold"].sum()),
              "Estimated Revenue": int(sales["Revenue_Cents"].sum()) / 100}
    return ReportResult(
        project.key, project.name, str(project.database), filters,
        datetime.now().astimezone().isoformat(timespec="seconds"), totals,
        summarize(sales, ["Period"]), summarize(sales, ["Product_Category"]),
        summarize(sales, ["Store_ID", "Store_Name"]), store_options, category_options)


def export_report(result, output_root):
    """Export the displayed snapshot, never silently rerun a different query."""
    folder = fs_path(output_root) / "reports" / (
        datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid4().hex[:8])
    folder.mkdir(parents=True, exist_ok=False)
    frames = {"totals": pd.DataFrame([result.totals]), "periods": result.periods,
              "categories": result.categories, "stores": result.stores}
    for name, frame in frames.items():
        # Prevent catalogue labels from becoming spreadsheet formulas on open.
        safe = frame.copy()
        for column in safe.select_dtypes(include=["object", "string"]).columns:
            safe[column] = safe[column].map(
                lambda value: "'" + value if isinstance(value, str) and
                value.lstrip().startswith(("=", "+", "-", "@")) else value)
        safe.to_csv(folder / f"{name}.csv", index=False, encoding="utf-8-sig", float_format="%.2f")
    metadata = {"project": result.project_name, "project_key": result.project_key,
                "database": result.database, "filters": asdict(result.filters),
                "generated_at": result.generated_at,
                "revenue_basis": "Estimated Revenue = Units × current catalogue Product_Price (USD)",
                "period_labels": "Period start; weeks start Monday; only periods with sales"}
    (folder / "filters.json").write_text(json.dumps(metadata, default=str, ensure_ascii=False, indent=2), encoding="utf-8")
    return display_path(folder)
