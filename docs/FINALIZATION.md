# Finalization — 2026-11-02

**Technical Setup acceptance passed; distribution remains on hold for licensing.**

The existing 2026-11-01 Matplotlib QtAgg Setup was reused without rebuilding.
Clean per-user installation and upgrade from the actual 2026-10-30 V2.5 Setup
passed in isolated application/data folders on the current Windows host.
Installed payload hashes match the portable manifest. Old Qt Charts, Virtual
Keyboard, QML/Quick and PDF binaries are absent after upgrade. Frozen GUI/worker
tests cover synthetic CSV processing, reports (nine chart cases and empty state),
repeat import, backup/restore, reopening, V2.4 compatibility and data preservation
across upgrade/uninstall. Native customer EXE startup/lifecycle mutex passed.
Existing user shortcuts were backed up and restored byte-for-byte.

Source regression record: 103 tests passed before finalization; the updated
curated source including its synthetic example passes 104 tests. Example totals:
6 transactions, 14 units, 174.25 estimated revenue. No real customer data used.

Limits: this is not a fresh Windows VM; native file dialogs and physical DPI
were not manually exercised. Screenshots and the retained QUICK_START.pdf are
historical; current QUICK_START.md instructions and example totals were checked.
The Setup remains unsigned. No GitHub push was performed. Existing source and
delivery folders were fully ZIP-backed-up and byte-verified before updating.

145 clean-payload DLL/PYD entries and 65 notice files were inventoried.
The old-version upgrade retains three allowed OpenGL-family files (148 total);
see upgrade-retained-native.json and the license status for that distinction. See
FINAL_LICENSE_STATUS.md, native-license-inventory.csv and package-audit.json.
Missing exact library sources, complete native notices/provenance and unverified
replacement/contractual conditions remain open. No application license was
invented and no commercial redistribution clearance is claimed.

Setup SHA-256: f24b87dbb696556b71d76179444840ffa66c10da92c49ac3f1e009c3eabb1e20
