#!/usr/bin/env python3
"""
SQLite to PostgreSQL Migration Script for ClinicConnect AI
Migrates data from SQLite (instance/ai_business_agent.db) to target PostgreSQL (e.g. on Render).

Preserves:
- Primary key IDs and foreign key relationships across all 14 tables in dependency order.
- PostgreSQL sequence counters (resets sequences after migration).
- Native data types (timestamps, booleans, nullables, text).

Usage:
  python scripts/migrate_sqlite_to_postgres.py --target-db "postgresql://user:pass@host/dbname"
  python scripts/migrate_sqlite_to_postgres.py --clean --target-db "postgresql://..."
  python scripts/migrate_sqlite_to_postgres.py --dry-run
"""

import os
import sys
import argparse
from datetime import datetime
from dotenv import load_dotenv

# Ensure project root is in sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Load environment variables
load_dotenv(os.path.join(BASE_DIR, ".env"))

from sqlalchemy import create_engine, select, text, inspect
from models import (
    db,
    Business,
    User,
    Doctor,
    DoctorSchedule,
    DoctorLeave,
    Service,
    Customer,
    ClinicWhatsAppAccount,
    ClinicInvitation,
    SubscriptionRequest,
    Conversation,
    Message,
    Appointment,
    Reminder,
)

# Strict dependency order for table migration
TABLE_MODELS = [
    ("businesses", Business),
    ("users", User),
    ("doctors", Doctor),
    ("doctor_schedules", DoctorSchedule),
    ("doctor_leaves", DoctorLeave),
    ("services", Service),
    ("customers", Customer),
    ("whatsapp_accounts", ClinicWhatsAppAccount),
    ("clinic_invitations", ClinicInvitation),
    ("subscription_requests", SubscriptionRequest),
    ("conversations", Conversation),
    ("messages", Message),
    ("appointments", Appointment),
    ("reminders", Reminder),
]


def clean_target_url(raw_url: str) -> str:
    """Normalize PostgreSQL connection string (handle postgres:// -> postgresql://)."""
    if not raw_url:
        return ""
    url = raw_url.strip().strip("'").strip('"')
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


def reset_postgres_sequences(conn, table_order):
    """
    Reset PostgreSQL primary key sequences to match the maximum ID in each table,
    preventing duplicate key errors on future inserts.
    """
    print("\n" + "=" * 60)
    print("STEP 4: Resetting PostgreSQL Primary Key Sequences")
    print("=" * 60)

    for table_name in table_order:
        try:
            # Query sequence associated with 'id' column
            seq_query = text(f"SELECT pg_get_serial_sequence('{table_name}', 'id');")
            seq_name = conn.execute(seq_query).scalar()

            if seq_name:
                # Query maximum id
                max_id_query = text(f'SELECT MAX(id) FROM "{table_name}";')
                max_id = conn.execute(max_id_query).scalar()

                if max_id is not None and max_id > 0:
                    # Next nextval will return max_id + 1
                    reset_sql = text(f"SELECT setval('{seq_name}', :max_id, true);")
                    conn.execute(reset_sql, {"max_id": max_id})
                    print(f"  [Sequence] {table_name:25} -> {seq_name} reset to {max_id} (nextval: {max_id + 1})")
                else:
                    # Empty table: nextval will return 1
                    reset_sql = text(f"SELECT setval('{seq_name}', 1, false);")
                    conn.execute(reset_sql)
                    print(f"  [Sequence] {table_name:25} -> {seq_name} reset to 1 (is_called=false, nextval: 1)")
            else:
                # Fallback to standard setval with pg_get_serial_sequence
                fallback_sql = text(
                    f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), coalesce(max(id), 1)) FROM \"{table_name}\";"
                )
                conn.execute(fallback_sql)
                print(f"  [Sequence] {table_name:25} -> generic setval executed")
        except Exception as e:
            print(f"  [Sequence Warning] {table_name:25} -> Could not reset sequence: {e}")

    conn.commit()
    print("  Sequences reset complete.")


def run_migration(
    sqlite_path: str,
    target_url: str,
    clean: bool = False,
    truncate: bool = False,
    dry_run: bool = False,
    skip_existing: bool = False,
    batch_size: int = 500,
):
    print("=" * 60)
    print("   ClinicConnect AI - SQLite -> PostgreSQL Migration Tool")
    print("=" * 60)
    print(f" Source SQLite  : {sqlite_path}")
    print(f" Target DB      : {target_url if not dry_run else '(DRY-RUN / NO CHANGES)'}")
    print(f" Clean Schema   : {clean}")
    print(f" Truncate First : {truncate}")
    print(f" Skip Existing  : {skip_existing}")
    print(f" Dry Run Mode   : {dry_run}")
    print("=" * 60)

    # 1. Verify SQLite source database
    if not os.path.exists(sqlite_path):
        print(f"\n[Error] Source SQLite database file not found at: {sqlite_path}")
        sys.exit(1)

    src_engine = create_engine(
        f"sqlite:///{os.path.abspath(sqlite_path)}",
        connect_args={"timeout": 30},
    )

    # Inspect source record counts
    src_counts = {}
    with src_engine.connect() as s_conn:
        for table_name, model in TABLE_MODELS:
            try:
                cnt = s_conn.execute(select(db.func.count()).select_from(model.__table__)).scalar() or 0
            except Exception:
                cnt = 0
            src_counts[table_name] = cnt

    print("\nSTEP 1: Source SQLite Record Counts:")
    for name, _ in TABLE_MODELS:
        print(f"  - {name:25}: {src_counts.get(name, 0):5} records")

    total_records = sum(src_counts.values())
    print(f"  Total records to migrate: {total_records}")

    if dry_run:
        print("\n[Dry Run] Validated source database. Target database will not be modified.")
        if target_url:
            try:
                print(f"Testing connection to target database...")
                target_engine = create_engine(
                    target_url,
                    pool_pre_ping=True,
                    pool_recycle=300,
                )
                with target_engine.connect() as test_conn:
                    test_conn.execute(text("SELECT 1;"))
                print("[Dry Run] Connection to target PostgreSQL successful!")
            except Exception as e:
                print(f"[Dry Run Warning] Connection test to target failed: {e}")
        print("\nDry-run complete. Exiting without changes.")
        return

    # 2. Connect to target PostgreSQL
    if not target_url:
        print("\n[Error] Target PostgreSQL URL is required.")
        print("Provide via --target-db argument or TARGET_DATABASE_URL environment variable.")
        sys.exit(1)

    target_engine = create_engine(
        target_url,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=10,
        max_overflow=20,
    )

    # Test connection
    try:
        with target_engine.connect() as test_conn:
            if target_engine.dialect.name == "postgresql":
                version = test_conn.execute(text("SELECT version();")).scalar()
                print(f"\nConnected to target PostgreSQL database:\n  {version[:80]}...")
            else:
                test_conn.execute(text("SELECT 1;"))
                print(f"\nConnected to target {target_engine.dialect.name} database.")
    except Exception as e:
        print(f"\n[Error] Failed to connect to target database: {e}")
        sys.exit(1)

    # 3. Clean / Drop if requested
    if clean:
        print("\n" + "=" * 60)
        print("STEP 2a: Dropping Existing Target Tables (--clean specified)")
        print("=" * 60)
        with target_engine.begin() as conn:
            # Drop in reverse dependency order with CASCADE
            for table_name, _ in reversed(TABLE_MODELS):
                try:
                    conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}" CASCADE;'))
                    print(f"  Dropped table '{table_name}'.")
                except Exception as e:
                    print(f"  [Notice] Drop '{table_name}': {e}")
        print("  Existing tables dropped.")
    elif truncate:
        print("\n" + "=" * 60)
        print("STEP 2a: Truncating Existing Target Tables (--truncate specified)")
        print("=" * 60)
        with target_engine.begin() as conn:
            table_list = ", ".join(f'"{name}"' for name, _ in reversed(TABLE_MODELS))
            try:
                conn.execute(text(f"TRUNCATE TABLE {table_list} RESTART IDENTITY CASCADE;"))
                print("  All tables truncated with RESTART IDENTITY CASCADE.")
            except Exception as e:
                print(f"  [Notice] Truncate error: {e}")

    # 4. Recreate/Ensure schema exists on PostgreSQL
    print("\n" + "=" * 60)
    print("STEP 2: Ensuring Database Schema Exists on PostgreSQL")
    print("=" * 60)
    db.metadata.create_all(bind=target_engine)
    print("  Schema verified. All 14 tables and indexes are ready.")

    # 5. Copy records preserving IDs
    print("\n" + "=" * 60)
    print("STEP 3: Copying Records from SQLite to PostgreSQL")
    print("=" * 60)

    target_counts = {}

    with src_engine.connect() as s_conn, target_engine.begin() as d_conn:
        for table_name, model in TABLE_MODELS:
            table = model.__table__
            query = select(table).order_by(table.c.id)
            rows = [dict(r) for r in s_conn.execute(query).mappings()]

            if not rows:
                print(f"  -> {table_name:25}: 0 records (skipped)")
                target_counts[table_name] = 0
                continue

            # Check if records already exist in target table
            existing_ids = set()
            if skip_existing:
                existing_res = d_conn.execute(select(table.c.id)).scalars().all()
                existing_ids = set(existing_res)

            rows_to_insert = [r for r in rows if r.get("id") not in existing_ids]

            if not rows_to_insert:
                print(f"  -> {table_name:25}: {len(rows)} records (all existed, skipped)")
                target_counts[table_name] = len(existing_ids)
                continue

            # Insert in chunks
            inserted_count = 0
            for i in range(0, len(rows_to_insert), batch_size):
                chunk = rows_to_insert[i : i + batch_size]
                d_conn.execute(table.insert(), chunk)
                inserted_count += len(chunk)

            print(
                f"  -> {table_name:25}: {inserted_count:5} records copied "
                f"(source: {len(rows)}, skipped: {len(rows) - inserted_count})"
            )
            target_counts[table_name] = inserted_count + len(existing_ids)

    # 6. Reset sequences in PostgreSQL
    is_postgres = target_engine.dialect.name == "postgresql"
    if is_postgres:
        with target_engine.connect() as seq_conn:
            reset_postgres_sequences(seq_conn, [name for name, _ in TABLE_MODELS])
    else:
        print(f"\n[Info] Dialect is {target_engine.dialect.name}, skipping PostgreSQL sequence reset.")

    # 7. Summary and Verification
    print("\n" + "=" * 60)
    print("STEP 5: Migration Verification & Summary")
    print("=" * 60)
    print(f" {'Table Name':<25} | {'SQLite Source':<15} | {'PostgreSQL Target':<17} | {'Status'}")
    print("-" * 75)

    all_matched = True
    for name, _ in TABLE_MODELS:
        src_cnt = src_counts.get(name, 0)
        tgt_cnt = target_counts.get(name, 0)
        status = "MATCH" if src_cnt == tgt_cnt else "MISMATCH"
        if status == "MISMATCH":
            all_matched = False
        print(f" {name:<25} | {src_cnt:<15} | {tgt_cnt:<17} | {status}")

    print("-" * 75)
    if all_matched:
        print("  SUCCESS: All table counts match perfectly between SQLite and PostgreSQL!")
    else:
        print("  WARNING: One or more table counts differ. Check logs above for skipped rows.")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Migrate ClinicConnect AI database from SQLite to PostgreSQL (e.g. on Render)."
    )
    parser.add_argument(
        "--sqlite-path",
        "-s",
        default=os.getenv("SQLITE_PATH", os.path.join(BASE_DIR, "instance", "ai_business_agent.db")),
        help="Path to source SQLite database file (default: instance/ai_business_agent.db)",
    )
    parser.add_argument(
        "--target-db",
        "-t",
        dest="target_url",
        default=os.getenv("TARGET_DATABASE_URL", os.getenv("DATABASE_URL", "")),
        help="Target PostgreSQL database URL (or set TARGET_DATABASE_URL / DATABASE_URL env var)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Drop all existing tables in target PostgreSQL before creating schema and migrating",
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Truncate all tables in target PostgreSQL before migrating",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Inspect SQLite records and test target connection without modifying target data",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip inserting records whose primary key (id) already exists in target table",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Batch size for bulk inserts (default: 500)",
    )

    args = parser.parse_args()

    # Clean target URL
    target_url = clean_target_url(args.target_url)

    # Run migration
    run_migration(
        sqlite_path=args.sqlite_path,
        target_url=target_url,
        clean=args.clean,
        truncate=args.truncate,
        dry_run=args.dry_run,
        skip_existing=args.skip_existing,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    main()
