"""One-time, non-destructive import of an existing local WILD WITHIN SQLite database.
Existing cloud rows are not overwritten; duplicate IDs/unique rows are skipped.
"""
import os, sqlite3, sys
import psycopg
from psycopg import sql

TABLES = ["habits", "experiments", "logs", "experiment_logs", "free_time_plans"]

def main():
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python tools/import_sqlite_to_cloud.py "D:\\path\\to\\wild_within.db"')
    source = sys.argv[1]
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url: raise SystemExit("Set DATABASE_URL to your Render PostgreSQL external connection string first.")
    if not os.path.isfile(source): raise SystemExit(f"SQLite source not found: {source}")
    src = sqlite3.connect(f"file:{source}?mode=ro", uri=True); src.row_factory = sqlite3.Row
    dst = psycopg.connect(url)
    try:
        with dst.transaction():
            for table in TABLES:
                exists = src.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
                if not exists: continue
                cols = [r[1] for r in src.execute(f'PRAGMA table_info("{table}")').fetchall()]
                if not cols: continue
                for row in src.execute(f'SELECT * FROM "{table}"').fetchall():
                    names = sql.SQL(',').join(map(sql.Identifier, cols))
                    placeholders = sql.SQL(',').join(sql.Placeholder() for _ in cols)
                    query = sql.SQL("INSERT INTO {} ({}) VALUES ({}) ON CONFLICT DO NOTHING").format(sql.Identifier(table), names, placeholders)
                    dst.execute(query, tuple(row[c] for c in cols))
            # Advance sequences after importing preserved numeric IDs.
            for table in TABLES:
                dst.execute("SELECT setval(pg_get_serial_sequence(%s, 'id'), GREATEST(COALESCE((SELECT MAX(id) FROM " + table + "), 1), 1), true)", (table,))
        print("Import completed without overwriting existing cloud rows. Verify counts before deleting any old database.")
    finally:
        src.close(); dst.close()
if __name__ == '__main__': main()
