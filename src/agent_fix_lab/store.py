"""Package-owned immutable documents. Source observations never overwritten."""

import json
import os
import sqlite3
from pathlib import Path

from .models import Contract


class Store:
    def __init__(self, root: Path | str):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.path = self.root / "lab.sqlite"
        with self.connect() as c:
            version = c.execute("pragma user_version").fetchone()[0]
            tables = c.execute("select name from sqlite_master where type='table'").fetchall()
            if version not in (0, 1) or (version == 0 and tables):
                raise ValueError("Unsupported lab schema version")
            c.executescript("""
                CREATE TABLE IF NOT EXISTS documents (
                    kind TEXT NOT NULL, id TEXT NOT NULL, body TEXT NOT NULL,
                    PRIMARY KEY(kind,id));
                CREATE TRIGGER IF NOT EXISTS immutable_update BEFORE UPDATE ON documents
                    BEGIN SELECT RAISE(ABORT,'immutable evidence'); END;
                CREATE TRIGGER IF NOT EXISTS immutable_delete BEFORE DELETE ON documents
                    BEGIN SELECT RAISE(ABORT,'immutable evidence'); END;
                PRAGMA user_version=1;
            """)
        os.chmod(self.path, 0o600)

    def connect(self):
        c = sqlite3.connect(self.path, timeout=30)
        c.execute("pragma foreign_keys=on")
        return c

    def put_many(self, documents):
        added = 0
        with self.connect() as c:
            for kind, obj in documents:
                body = obj.model_dump() if isinstance(obj, Contract) else obj
                text = json.dumps(body, sort_keys=True)
                old = c.execute(
                    "select body from documents where kind=? and id=?", (kind, body["id"])
                ).fetchone()
                if old:
                    if old[0] != text:
                        raise ValueError("Conflicting immutable record")
                    continue
                c.execute("insert into documents values(?,?,?)", (kind, body["id"], text))
                added += 1
        return added

    def put(self, kind, obj):
        return self.put_many([(kind, obj)])

    def get(self, kind, identifier):
        with self.connect() as c:
            row = c.execute(
                "select body from documents where kind=? and id=?", (kind, identifier)
            ).fetchone()
        if not row:
            raise KeyError(f"{kind} not found")
        return json.loads(row[0])

    def all(self, kind):
        with self.connect() as c:
            return [
                json.loads(r[0])
                for r in c.execute(
                    "select body from documents where kind=? order by rowid", (kind,)
                )
            ]
