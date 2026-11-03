"""Deterministic synthetic CSV simulation. Never connects to a database.

Only this generator's named outputs may be written. Existing files must match
the previous manifest's hashes before regeneration is allowed.
"""
import argparse
from collections import Counter, defaultdict
import csv
from datetime import date, timedelta
from decimal import Decimal
import hashlib
import io
import json
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data/demo_batches/daily_sales_simulation"
START = date(2026, 8, 1)
HISTORY_END = date(2026, 10, 19)
END = date(2026, 10, 26)
SEED = 20261026
FIRST_ID = 202608010001
COLUMNS = ["Sale_ID", "Date", "Store_ID", "Product_ID", "Units"]
SUMMARY = ["Transactions", "Units_Sold", "Estimated_Revenue"]
VERSION = "daily-sales-simulation-v1"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_csv(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames, list(reader)


def money(cents):
    return f"{cents // 100}.{cents % 100:02d}"


def cents(value):
    amount = Decimal(value.replace("$", "").replace(",", "").strip())
    require(amount.is_finite() and amount >= 0 and amount * 100 == (amount * 100).to_integral_value(),
            f"Invalid catalogue price: {value}")
    return int(amount * 100)


def catalogs(reference_dir):
    product_path = reference_dir / "products.csv"
    store_path = reference_dir / "stores.csv"
    product_columns, products = read_csv(product_path)
    store_columns, stores = read_csv(store_path)
    require(set(["Product_ID", "Product_Category", "Product_Price"]).issubset(product_columns or []), "Missing product columns")
    require(set(["Store_ID", "Store_Name"]).issubset(store_columns or []), "Missing store columns")
    require(products and stores, "Empty reference catalogue")
    for rows, key in ((products, "Product_ID"), (stores, "Store_ID")):
        ids = [int(row[key]) for row in rows]
        require(all(value > 0 for value in ids) and len(set(ids)) == len(ids), f"Invalid or duplicate {key}")
    products = {int(row["Product_ID"]): {**row, "price_cents": cents(row["Product_Price"])} for row in products}
    stores = {int(row["Store_ID"]): row for row in stores}
    require(all(row["Product_Category"].strip() for row in products.values()), "Empty category")
    return dict(sorted(products.items())), dict(sorted(stores.items())), {
        "products.csv": sha(product_path.read_bytes()), "stores.csv": sha(store_path.read_bytes())}


def batches():
    result = [("sales_history_seed.csv", START, HISTORY_END)]
    day = HISTORY_END + timedelta(days=1)
    while day <= END:
        result.append((f"sales_{day}.csv", day, day))
        day += timedelta(days=1)
    return result


def generate(products, stores, seed=SEED):
    rng = random.Random(seed)
    product_ids, store_ids = list(products), list(stores)
    product_weights = [rng.lognormvariate(0, .6) * (1500 / max(100, products[p]["price_cents"])) ** .35
                       for p in product_ids]
    location_weights = {"Downtown": 1.4, "Commercial": 1.15, "Residential": .85, "Airport": .65}
    store_weights = [rng.lognormvariate(0, .55) * location_weights.get(stores[s].get("Store_Location"), 1)
                     for s in store_ids]
    result = {filename: [] for filename, _, _ in batches()}
    sale_id, day = FIRST_ID, START
    while day <= END:
        weekday = day.weekday()
        weekend_factor = 1.32 if weekday == 5 else 1.20 if weekday == 6 else 1.0
        count = max(30, min(80, round(46 * weekend_factor + (day - START).days * .035 + rng.gauss(0, 6))))
        filename = "sales_history_seed.csv" if day <= HISTORY_END else f"sales_{day}.csv"
        for _ in range(count):
            store_id = rng.choices(store_ids, weights=store_weights)[0]
            product_id = rng.choices(product_ids, weights=product_weights)[0]
            weights = [47, 30, 15, 6, 2] if weekday >= 5 else [56, 28, 10, 4, 2]
            units = rng.choices([1, 2, 3, 4, 5], weights=weights)[0]
            if products[product_id]["price_cents"] < 800 and rng.random() < .12:
                units += 1
            result[filename].append(dict(zip(COLUMNS, [sale_id, day.isoformat(), store_id, product_id, units])))
            sale_id += 1
        day += timedelta(days=1)
    return result


def csv_bytes(columns, rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8-sig")


def summarize(rows, products):
    return {"Transactions": len(rows), "Units_Sold": sum(int(row["Units"]) for row in rows),
            "Estimated_Revenue": money(sum(int(row["Units"]) * products[int(row["Product_ID"])]["price_cents"] for row in rows))}


def grouped(rows, products, keys, key_function):
    groups = defaultdict(list)
    for row in rows:
        groups[key_function(row)].append(row)
    return [{**dict(zip(keys, key)), **summarize(group, products)} for key, group in sorted(groups.items())]


def build_outputs(data, products, stores):
    files = {name: csv_bytes(COLUMNS, rows) for name, rows in data.items()}
    all_rows = [row for rows in data.values() for row in rows]
    expected, cumulative, loaded = [], [], []
    for filename, start, end in batches():
        expected.append({"Filename": filename, "Start_Date": start.isoformat(), "End_Date": end.isoformat(),
                         **summarize(data[filename], products)})
        loaded.extend(data[filename])
        cumulative.append({"After_Filename": filename, **summarize(loaded, products),
                           "Active_Stores": len({row["Store_ID"] for row in loaded})})
    files["expected_results.csv"] = csv_bytes(["Filename", "Start_Date", "End_Date"] + SUMMARY, expected)
    files["expected_totals.csv"] = csv_bytes(["Start_Date", "End_Date"] + SUMMARY + ["Active_Stores"],
        [{"Start_Date": str(START), "End_Date": str(END), **summarize(all_rows, products),
          "Active_Stores": len({row["Store_ID"] for row in all_rows})}])
    files["expected_after_each_load.csv"] = csv_bytes(["After_Filename"] + SUMMARY + ["Active_Stores"], cumulative)
    def period(row, frequency):
        day = date.fromisoformat(row["Date"])
        if frequency == "weekly":
            day -= timedelta(days=day.weekday())
        elif frequency == "monthly":
            day = day.replace(day=1)
        elif frequency == "quarterly":
            day = day.replace(month=((day.month - 1) // 3) * 3 + 1, day=1)
        return (day.isoformat(),)
    for frequency in ("daily", "weekly", "monthly", "quarterly"):
        files[f"expected_{frequency}.csv"] = csv_bytes(["Period"] + SUMMARY,
            grouped(all_rows, products, ["Period"], lambda row: period(row, frequency)))
    files["expected_stores.csv"] = csv_bytes(["Store_ID", "Store_Name"] + SUMMARY,
        grouped(all_rows, products, ["Store_ID", "Store_Name"], lambda row: (row["Store_ID"], stores[row["Store_ID"]]["Store_Name"])))
    files["expected_categories.csv"] = csv_bytes(["Product_Category"] + SUMMARY,
        grouped(all_rows, products, ["Product_Category"], lambda row: (products[row["Product_ID"]]["Product_Category"],)))
    return files


def validate(output_dir, products, stores):
    """Reopen CSVs and reconcile all rollups using independent Decimal arithmetic."""
    all_rows, per_file, seen, days = [], [], set(), Counter()
    for filename, start, end in batches():
        columns, rows = read_csv(output_dir / filename)
        require(columns == COLUMNS, f"Incorrect columns: {filename}")
        require(rows, f"Empty batch: {filename}")
        for row in rows:
            require(all(value is not None and value != "" for value in row.values()), f"Missing field: {filename}")
            current = date.fromisoformat(row["Date"])
            require(row["Date"] == current.isoformat() and start <= current <= end, f"Date out of range: {filename}")
            for key in ("Sale_ID", "Store_ID", "Product_ID", "Units"):
                require(row[key].isdigit() and int(row[key]) > 0, f"Invalid {key}")
            sale_id = int(row["Sale_ID"])
            require(sale_id not in seen, "Duplicate Sale_ID across batches")
            seen.add(sale_id)
            require(int(row["Store_ID"]) in stores and int(row["Product_ID"]) in products, "Invalid reference")
            days[current] += 1
        all_rows.extend(rows)
        per_file.append((filename, rows))
    require(set(days) == {START + timedelta(days=i) for i in range((END - START).days + 1)}, "Missing sale day")
    require(all(30 <= count <= 80 for count in days.values()), "Daily count outside 30–80")
    def independent(group):
        total = sum((Decimal(row["Units"]) * Decimal(products[int(row["Product_ID"])]["Product_Price"].replace("$", "").replace(",", "").strip()) for row in group), Decimal(0))
        return len(group), sum(int(row["Units"]) for row in group), total
    def equal(row, group):
        require((int(row["Transactions"]), int(row["Units_Sold"]), Decimal(row["Estimated_Revenue"])) == independent(group), "Expected summary mismatch")
    _, expected = read_csv(output_dir / "expected_results.csv")
    require(len(expected) == 8, "Incorrect batch summaries")
    cumulative = []
    _, after = read_csv(output_dir / "expected_after_each_load.csv")
    require(len(after) == 8, "Incorrect cumulative summaries")
    for index, (filename, rows) in enumerate(per_file):
        require(expected[index]["Filename"] == filename, "Incorrect file ordering")
        require((expected[index]["Start_Date"], expected[index]["End_Date"]) ==
                (min(row["Date"] for row in rows), max(row["Date"] for row in rows)), "Incorrect batch dates")
        equal(expected[index], rows)
        cumulative.extend(rows)
        require(after[index]["After_Filename"] == filename, "Incorrect cumulative order")
        equal(after[index], cumulative)
        require(int(after[index]["Active_Stores"]) == len({row["Store_ID"] for row in cumulative}), "Active stores mismatch")
    _, totals = read_csv(output_dir / "expected_totals.csv")
    require(len(totals) == 1, "Expected exactly one total row")
    require((totals[0]["Start_Date"], totals[0]["End_Date"]) == (str(START), str(END)), "Incorrect total dates")
    equal(totals[0], all_rows)
    require(int(totals[0]["Active_Stores"]) == len({row["Store_ID"] for row in all_rows}), "Total active stores mismatch")
    # Independent calendar keys, including Monday weeks crossing month/quarter boundaries.
    for frequency in ("daily", "weekly", "monthly", "quarterly", "stores", "categories"):
        groups = defaultdict(list)
        for row in all_rows:
            day = date.fromisoformat(row["Date"])
            key = (row["Date"] if frequency == "daily" else
                   date.fromordinal(day.toordinal() - day.weekday()).isoformat() if frequency == "weekly" else
                   f"{day.year:04d}-{day.month:02d}-01" if frequency == "monthly" else
                   f"{day.year:04d}-{[1, 4, 7, 10][(day.month - 1) // 3]:02d}-01" if frequency == "quarterly" else
                   row["Store_ID"] if frequency == "stores" else products[int(row["Product_ID"])]["Product_Category"])
            groups[key].append(row)
        _, summaries = read_csv(output_dir / f"expected_{frequency}.csv")
        key_column = "Store_ID" if frequency == "stores" else "Product_Category" if frequency == "categories" else "Period"
        require(len(summaries) == len(groups) and {row[key_column] for row in summaries} == set(groups), "Grouping keys mismatch")
        for summary in summaries:
            equal(summary, groups[summary[key_column]])
    weekdays = [count for day, count in days.items() if day.weekday() < 5]
    weekends = [count for day, count in days.items() if day.weekday() >= 5]
    counts, units, revenue = independent(all_rows)
    return {"status": "PASS", "sales_files": 8, "days": len(days), "transactions": counts,
            "units_sold": units, "estimated_revenue_usd": str(revenue.quantize(Decimal('.01'))),
            "daily_transactions_min": min(days.values()), "daily_transactions_max": max(days.values()),
            "weekday_mean": round(sum(weekdays) / len(weekdays), 2), "weekend_mean": round(sum(weekends) / len(weekends), 2),
            "represented_stores": len({row["Store_ID"] for row in all_rows}),
            "represented_products": len({row["Product_ID"] for row in all_rows}),
            "represented_categories": len({products[int(row["Product_ID"])]["Product_Category"] for row in all_rows}),
            "checks": ["exact_columns", "globally_unique_ids", "date_ranges_and_coverage", "valid_references",
                       "positive_integer_units", "no_missing_values", "per_file_and_cumulative_totals",
                       "daily_weekly_monthly_quarterly_totals", "store_and_category_totals"],
            "database_loading": "NOT PERFORMED"}


def write_dataset(output_dir=DEFAULT_OUTPUT, reference_dir=ROOT / "data/raw", seed=SEED):
    output_dir, reference_dir = Path(output_dir).resolve(), Path(reference_dir).resolve()
    products, stores, source_hashes = catalogs(reference_dir)
    files = build_outputs(generate(products, stores, seed), products, stores)
    manifest_path = output_dir / "manifest.json"
    previous = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    require(not previous or previous.get("generator") == VERSION, "Output folder is owned by another generator")
    # Refuse unknown/modified targets. Never overwrite user CSVs or follow output symlinks.
    targets = list(files) + ["validation_report.json", "manifest.json"]
    for name in targets:
        target = output_dir / name
        require(not target.is_symlink() and target.resolve().parent == output_dir, "Output path escapes dataset folder")
        if target.exists() and name != "manifest.json":
            require(name in previous.get("files", {}) and sha(target.read_bytes()) == previous["files"][name],
                    f"Refusing to overwrite unowned/modified output: {name}")
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (output_dir / name).write_bytes(content)
    report = validate(output_dir, products, stores)
    report_bytes = (json.dumps(report, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    (output_dir / "validation_report.json").write_bytes(report_bytes)
    files["validation_report.json"] = report_bytes
    manifest = {"generator": VERSION, "synthetic": True, "seed": seed, "first_sale_id": FIRST_ID,
                "start": str(START), "end": str(END), "source_sha256": source_hashes,
                "currency": "USD", "revenue_basis": "Units x current catalogue Product_Price",
                "files": {name: sha(content) for name, content in files.items()}}
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--reference-dir", type=Path, default=ROOT / "data/raw")
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--validate-only", action="store_true", help="Check existing files without writing any file")
    args = parser.parse_args()
    if args.validate_only:
        products, stores, source_hashes = catalogs(args.reference_dir)
        manifest = json.loads((args.output_dir / "manifest.json").read_text(encoding="utf-8"))
        require(manifest["source_sha256"] == source_hashes, "Reference catalogues changed since generation")
        report = validate(args.output_dir, products, stores)
        for name, expected_hash in manifest["files"].items():
            require(Path(name).name == name, "Unsafe manifest filename")
            require(sha((args.output_dir / name).read_bytes()) == expected_hash, f"File changed: {name}")
    else:
        report = write_dataset(args.output_dir, args.reference_dir, args.seed)
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
