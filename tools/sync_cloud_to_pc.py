"""Download a safe, authenticated snapshot of cloud records into a local SQLite mirror.
Run from Windows Task Scheduler every 5 minutes (or any desired interval).
"""
import json, os, shutil, sqlite3, sys, tempfile
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

APP_URL = os.environ.get("WILD_WITHIN_URL", "").rstrip("/")
TOKEN = os.environ.get("SYNC_TOKEN", "")
DB_PATH = Path(os.environ.get("WILD_WITHIN_LOCAL_MIRROR", r"D:\WILD_WITHIN_DATA\wild_within_cloud_mirror.db"))
TABLES = ["habits", "logs", "experiments", "experiment_logs", "free_time_plans"]
SCHEMA = {
"habits": "id INTEGER PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL DEFAULT 'Growth', description TEXT NOT NULL DEFAULT '', target_minutes INTEGER NOT NULL DEFAULT 15, reminder_time TEXT NOT NULL DEFAULT '', reminder_days TEXT NOT NULL DEFAULT '0,1,2,3,4,5,6', icon TEXT NOT NULL DEFAULT '✳', schedule_json TEXT NOT NULL DEFAULT '{}', start_date TEXT NOT NULL, end_date TEXT NOT NULL DEFAULT '', active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL",
"logs": "id INTEGER PRIMARY KEY, habit_id INTEGER NOT NULL REFERENCES habits(id) ON DELETE CASCADE, log_date TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'done', minutes INTEGER NOT NULL DEFAULT 0, note TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL, UNIQUE(habit_id, log_date)",
"experiments": "id INTEGER PRIMARY KEY, title TEXT NOT NULL, hypothesis TEXT NOT NULL DEFAULT '', duration_days INTEGER NOT NULL DEFAULT 30, start_date TEXT NOT NULL, end_date TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active', created_at TEXT NOT NULL",
"experiment_logs": "id INTEGER PRIMARY KEY, experiment_id INTEGER NOT NULL REFERENCES experiments(id) ON DELETE CASCADE, log_date TEXT NOT NULL, outcome TEXT NOT NULL DEFAULT '', rating INTEGER NOT NULL DEFAULT 3, note TEXT NOT NULL DEFAULT '', UNIQUE(experiment_id, log_date)",
"free_time_plans": "id INTEGER PRIMARY KEY, plan_date TEXT NOT NULL, start_time TEXT NOT NULL, end_time TEXT NOT NULL, intention TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(plan_date, start_time, end_time)"
}

def main():
    if not APP_URL or not TOKEN:
        raise SystemExit("Set WILD_WITHIN_URL and SYNC_TOKEN environment variables first.")
    req = Request(APP_URL + "/api/admin/snapshot", headers={"Authorization": "Bearer " + TOKEN, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=45) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as exc:
        raise SystemExit(f"Cloud sync failed; local copy was not changed: {exc}")
    tables = payload.get("tables")
    if not isinstance(tables, dict) or any(t not in tables for t in TABLES):
        raise SystemExit("Unexpected cloud snapshot; local copy was not changed.")
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        backup = DB_PATH.with_name(DB_PATH.stem + "_backup_" + datetime.now().strftime("%Y%m%d") + DB_PATH.suffix)
        if not backup.exists():
            shutil.copy2(DB_PATH, backup)
    # Build a temporary complete snapshot first; only replace the mirror after successful validation.
    fd, temp_name = tempfile.mkstemp(prefix="ww_sync_", suffix=".db", dir=str(DB_PATH.parent)); os.close(fd)
    try:
        con = sqlite3.connect(temp_name)
        con.execute("PRAGMA foreign_keys=ON")
        for table in TABLES:
            con.execute(f"CREATE TABLE {table} ({SCHEMA[table]})")
        with con:
            for table in TABLES:
                rows = tables[table]
                for row in rows:
                    if not isinstance(row, dict): raise ValueError(f"Invalid row in {table}")
                    cols = list(row.keys())
                    if not cols: continue
                    q = ",".join("?" for _ in cols)
                    col_sql = ",".join('"' + c.replace('"','""') + '"' for c in cols)
                    con.execute(f"INSERT INTO {table} ({col_sql}) VALUES ({q})", [row[c] for c in cols])
        counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in TABLES}
        con.close()
        os.replace(temp_name, DB_PATH)
        print(f"SYNC OK at {datetime.now().isoformat(timespec='seconds')}; source={payload.get('generated_at')}; records={counts}; local={DB_PATH}")
    except Exception:
        try: os.remove(temp_name)
        except OSError: pass
        raise

if __name__ == "__main__":
    main()
