import argparse
import os
from typing import Iterable
from urllib.parse import quote_plus, urlparse, urlunparse

from sqlalchemy import MetaData, create_engine, text
from sqlalchemy.dialects.sqlite import DATE as SQLITE_DATE
from sqlalchemy.dialects.sqlite import DATETIME as SQLITE_DATETIME
from sqlalchemy.dialects.sqlite import TIME as SQLITE_TIME
from sqlalchemy.types import Date, DateTime, Time
from sqlalchemy.engine import Connection


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, "")
    if not raw:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _load_env_file(path: str) -> None:
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("'").strip('"')
            if key and key not in os.environ:
                os.environ[key] = value


def _normalize_db_url(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme or parsed.username is None:
        return url

    username = quote_plus(parsed.username)
    password = quote_plus(parsed.password) if parsed.password is not None else None
    host = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""

    auth = username
    if password is not None:
        auth = f"{auth}:{password}"

    netloc = f"{auth}@{host}{port}"
    return urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))


def _ensure_target_schema_from_sqlite(sqlite_url: str, postgres_url: str) -> None:
    src_engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})
    dst_engine = create_engine(postgres_url)

    src_meta = MetaData()
    src_meta.reflect(bind=src_engine)
    _coerce_sqlite_types_for_postgres(src_meta)
    src_meta.create_all(bind=dst_engine, checkfirst=True)


def _coerce_sqlite_types_for_postgres(metadata: MetaData) -> None:
    if not metadata.tables:
        return
    for table in metadata.tables.values():
        for column in table.columns:
            col_type = column.type
            if isinstance(col_type, SQLITE_DATETIME):
                column.type = DateTime()
            elif isinstance(col_type, SQLITE_DATE):
                column.type = Date()
            elif isinstance(col_type, SQLITE_TIME):
                column.type = Time()


def _load_metadata(engine) -> MetaData:
    metadata = MetaData()
    metadata.reflect(bind=engine)
    return metadata


def _truncate_tables(conn: Connection, tables: Iterable) -> None:
    for table in reversed(list(tables)):
        conn.execute(text(f'TRUNCATE TABLE "{table.name}" RESTART IDENTITY CASCADE'))


def _copy_table(src_conn: Connection, dst_conn: Connection, table) -> int:
    rows = src_conn.execute(table.select()).mappings().all()
    if not rows:
        return 0
    dst_conn.execute(table.insert(), rows)
    return len(rows)


def _reset_sequences(dst_conn: Connection, metadata: MetaData) -> None:
    if dst_conn.dialect.name != "postgresql":
        return

    for table in metadata.sorted_tables:
        pk_cols = [col for col in table.primary_key.columns if col.autoincrement]
        if len(pk_cols) != 1:
            continue
        pk_col = pk_cols[0]
        seq = dst_conn.execute(
            text("SELECT pg_get_serial_sequence(:table, :column)"),
            {"table": table.name, "column": pk_col.name},
        ).scalar()
        if not seq:
            continue
        table_sql = f'"{table.name}"'
        col_sql = f'"{pk_col.name}"'
        dst_conn.execute(
            text(
                f"SELECT setval(:seq, GREATEST((SELECT COALESCE(MAX({col_sql}), 0) FROM {table_sql}), 1))"
            ),
            {"seq": seq},
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate SQLite data to Supabase Postgres.")
    parser.add_argument("--sqlite-url", default=os.getenv("SQLITE_URL", "sqlite:///./database_fresh.db"))
    parser.add_argument("--postgres-url", default=os.getenv("SUPABASE_DATABASE_URL") or os.getenv("DATABASE_URL", ""))
    parser.add_argument("--truncate", action="store_true", default=_bool_env("TRUNCATE_TARGET", False))
    parser.add_argument("--dry-run", action="store_true", default=False)
    args = parser.parse_args()

    _load_env_file(".env")

    postgres_url = args.postgres_url or os.getenv("SUPABASE_DATABASE_URL") or os.getenv("DATABASE_URL", "")
    if not postgres_url:
        postgres_url = input("Enter Supabase Postgres URL (password will be safely encoded): ").strip()
    if not postgres_url:
        raise SystemExit("Missing Postgres URL. Set SUPABASE_DATABASE_URL or DATABASE_URL.")

    postgres_url = _normalize_db_url(postgres_url)

    _ensure_target_schema_from_sqlite(args.sqlite_url, postgres_url)

    src_engine = create_engine(args.sqlite_url, connect_args={"check_same_thread": False})
    dst_engine = create_engine(postgres_url)

    src_meta = _load_metadata(src_engine)
    dst_meta = _load_metadata(dst_engine)

    src_tables = [t for t in src_meta.sorted_tables if not t.name.startswith("sqlite_")]
    dst_table_names = {t.name for t in dst_meta.sorted_tables}

    missing = [t.name for t in src_tables if t.name not in dst_table_names]
    if missing:
        print(f"Warning: Skipping tables not found in Postgres: {', '.join(missing)}")

    with src_engine.begin() as src_conn, dst_engine.begin() as dst_conn:
        if args.truncate:
            _truncate_tables(dst_conn, [t for t in dst_meta.sorted_tables])

        total = 0
        for table in src_tables:
            if table.name not in dst_table_names:
                continue
            count = _copy_table(src_conn, dst_conn, table)
            total += count
            print(f"Copied {count} rows into {table.name}")

        if not args.dry_run:
            _reset_sequences(dst_conn, dst_meta)

    print(f"Done. Total rows copied: {total}")


if __name__ == "__main__":
    main()
