"""Package-owned immutable documents. Source observations never overwritten."""

import fcntl
import json
import os
import sqlite3
from contextlib import contextmanager
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
            for field in ("case_id", "recipe_id", "candidate_id", "scope"):
                c.execute(
                    f"create index if not exists documents_{field} "
                    f"on documents(kind,json_extract(body,'$.{field}'))"
                )
        os.chmod(self.path, 0o600)

    def connect(self):
        c = sqlite3.connect(self.path, timeout=30)
        c.execute("pragma foreign_keys=on")
        return c

    @contextmanager
    def workflow_lock(self, name):
        if name not in {"scan", "authorize-draft"}:
            raise ValueError("Unsupported workflow lock")
        fd = os.open(self.root / f"{name}.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise ValueError(
                    "Workflow already running; retry the same bounded request"
                ) from exc
            yield
        finally:
            os.close(fd)

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

    def page(self, kind, *, field=None, value=None, offset=0, limit=100):
        if not 0 <= offset or not 1 <= limit <= 10000:
            raise ValueError("Expected nonnegative offset and limit 1..10000")
        if field is not None and field not in {
            "case_id",
            "recipe_id",
            "candidate_id",
            "source_id",
            "scope",
        }:
            raise ValueError("Unsupported document filter")
        clause = "kind=?"
        args = [kind]
        if field:
            clause += f" and json_extract(body,'$.{field}')=?"
            args.append(value)
        with self.connect() as c:
            return [
                json.loads(r[0])
                for r in c.execute(
                    f"select body from documents where {clause} order by rowid limit ? offset ?",
                    [*args, limit, offset],
                )
            ]

    def latest(self, kind, field, value):
        if field not in {"case_id", "recipe_id", "scope"}:
            raise ValueError("Unsupported document filter")
        with self.connect() as c:
            row = c.execute(
                f"select body from documents where kind=? and "
                f"json_extract(body,'$.{field}')=? order by rowid desc limit 1",
                (kind, value),
            ).fetchone()
        return json.loads(row[0]) if row else None

    def effective_annotations(self, case_id, offset=0, limit=100):
        if offset < 0 or not 1 <= limit <= 10000:
            raise ValueError("Invalid pagination")
        with self.connect() as c:
            return [
                json.loads(row[0])
                for row in c.execute(
                    """
                with recursive items as materialized (
                  select body,row_number() over(order by rowid desc) n
                  from documents where kind='annotation' and json_extract(body,'$.case_id')=?
                ), walk(n,retracted,body,active) as (
                  select 0,'[]',null,0 union all
                  select i.n,
                    case when json_extract(i.body,'$.id') not in (select value from json_each(w.retracted))
                      and json_extract(i.body,'$.retracts') is not null
                    then json_insert(w.retracted,'$[#]',json_extract(i.body,'$.retracts')) else w.retracted end,
                    i.body,json_extract(i.body,'$.id') not in (select value from json_each(w.retracted))
                  from walk w join items i on i.n=w.n+1
                ) select body from walk where active order by n desc limit ? offset ?
            """,
                    (case_id, limit, offset),
                )
            ]

    def latest_variants(self, recipe_id):
        with self.connect() as c:
            return [
                json.loads(row[0])
                for row in c.execute(
                    """
                select body from (
                  select body,row_number() over(partition by json_extract(body,'$.variant') order by rowid desc) n
                  from documents where kind='result' and json_extract(body,'$.recipe_id')=?
                ) where n=1
            """,
                    (recipe_id,),
                )
            ]

    def related_results(self, case_id, limit=100, offset=0):
        if not 1 <= limit <= 10000 or offset < 0:
            raise ValueError("Invalid pagination")
        with self.connect() as c:
            return [
                json.loads(r[0])
                for r in c.execute(
                    "select r.body from documents r join documents p "
                    "on p.kind='recipe' and p.id=json_extract(r.body,'$.recipe_id') "
                    "where r.kind='result' and json_extract(p.body,'$.case_id')=? "
                    "order by r.rowid limit ? offset ?",
                    (case_id, limit, offset),
                )
            ]
