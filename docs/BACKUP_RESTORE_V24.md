# Backup compatibility
V2.5 retains backup format_version=1 and project schema_version=1. No schema
migration is performed. A restored project receives a new UUID. Existing projects
are not overwritten. SQLite backup API produces a consistent snapshot.

Archive entries: manifest.json, project.json, data/database/sales.db,
data/raw/products.csv, data/raw/stores.csv. SHA-256 and exact entry validation,
path traversal/symlink rejection and SQLite integrity_check protect restore.
Sales and catalogs are included. Input files, logs, quarantine, operation history
and old exports are excluded; reports can be regenerated. This is not a full
working-directory backup and it is not encrypted.
