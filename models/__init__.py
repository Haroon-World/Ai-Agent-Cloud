from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text, event
from sqlalchemy.engine import Engine
import sqlite3

db = SQLAlchemy()

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

from models.business import Business
from models.doctor import Doctor
from models.service import Service
from models.customer import Customer
from models.appointment import Appointment
from models.conversation import Conversation
from models.message import Message
from models.reminder import Reminder
from models.doctor_schedule import DoctorSchedule
from models.doctor_leave import DoctorLeave
from models.user import User
from models.subscription_request import SubscriptionRequest
from models.whatsapp_account import ClinicWhatsAppAccount
from models.clinic_invitation import ClinicInvitation

DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def sync_postgres_sequences(engine=None):
    """
    Ensure all PostgreSQL primary key sequences match the maximum ID in their respective tables.
    Prevents duplicate key errors (UniqueViolation) on subsequent inserts when tables are seeded
    or populated with explicit IDs.
    """
    target_engine = engine or db.engine
    if not target_engine or target_engine.dialect.name != "postgresql":
        return

    table_names = [
        "businesses",
        "users",
        "doctors",
        "doctor_schedules",
        "doctor_leaves",
        "services",
        "customers",
        "whatsapp_accounts",
        "clinic_invitations",
        "subscription_requests",
        "conversations",
        "messages",
        "appointments",
        "reminders",
    ]

    try:
        with target_engine.connect() as conn:
            for tbl in table_names:
                try:
                    seq_query = text(f"SELECT pg_get_serial_sequence('{tbl}', 'id');")
                    seq_name = conn.execute(seq_query).scalar()
                    if seq_name:
                        max_id_query = text(f'SELECT MAX(id) FROM "{tbl}";')
                        max_id = conn.execute(max_id_query).scalar()
                        if max_id is not None and max_id > 0:
                            conn.execute(text(f"SELECT setval('{seq_name}', :max_id, true);"), {"max_id": max_id})
                        else:
                            conn.execute(text(f"SELECT setval('{seq_name}', 1, false);"))
                    else:
                        conn.execute(text(
                            f'SELECT setval(pg_get_serial_sequence(\'{tbl}\', \'id\'), coalesce(max(id), 1)) FROM "{tbl}";'
                        ))
                except Exception as ex:
                    print(f"[Sequence Sync Notice] '{tbl}': {ex}")
            conn.commit()
            print("[Auto-Migrate] PostgreSQL primary key sequences synchronized.")
    except Exception as e:
        print(f"[Sequence Sync Warning]: {e}")

def auto_migrate_db(app=None):
    """Automatically inspect existing database tables, add missing columns, and populate default doctor schedules."""
    def _migrate():
        db.create_all()
        try:
            sync_postgres_sequences()

            inspector = inspect(db.engine)
            for table_name, table in db.metadata.tables.items():
                if inspector.has_table(table_name):
                    existing_columns = {col['name'] for col in inspector.get_columns(table_name)}
                    for column in table.columns:
                        if column.name not in existing_columns:
                            col_type = column.type.compile(db.engine.dialect)
                            sql = f"ALTER TABLE {table_name} ADD COLUMN {column.name} {col_type}"
                            db.session.execute(text(sql))
                            db.session.commit()
                            print(f"[Auto-Migrate] Added column '{column.name}' to table '{table_name}'.")

            # Seed default DoctorSchedule entries & consultation services for any existing doctor lacking them
            doctors = Doctor.query.all()
            for doc in doctors:
                existing_schedules = {s.day_of_week: s for s in doc.schedules}
                working_days_list = [d.strip() for d in (doc.working_days or "").split(",")] if doc.working_days else ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
                for day in DAYS_OF_WEEK:
                    if day not in existing_schedules:
                        is_avail = day in working_days_list
                        sched = DoctorSchedule(
                            doctor_id=doc.id,
                            day_of_week=day,
                            is_available=is_avail,
                            start_time=doc.start_time or "09:00",
                            end_time=doc.end_time or "17:00"
                        )
                        db.session.add(sched)
                db.session.commit()

                # Ensure doctor has at least one active consultation service
                has_service = Service.query.filter_by(business_id=doc.business_id, doctor_id=doc.id, is_active=True).first()
                if not has_service:
                    biz = db.session.get(Business, doc.business_id)
                    fee = getattr(biz, "consultation_fee", 2000.0) or 2000.0
                    new_svc = Service(
                        business_id=doc.business_id,
                        doctor_id=doc.id,
                        name="Consultation & Checkup",
                        description=f"Clinical evaluation and general consultation with {doc.name}.",
                        duration=30,
                        price=fee,
                        is_active=True
                    )
                    db.session.add(new_svc)
                    try:
                        db.session.commit()
                    except Exception:
                        db.session.rollback()

            # Populate default trial_ends_at for any businesses lacking subscription data
            from datetime import datetime, timezone, timedelta
            businesses = Business.query.all()
            for biz in businesses:
                if not getattr(biz, "trial_ends_at", None):
                    biz.subscription_status = "trial"
                    base_time = biz.created_at or datetime.now(timezone.utc)
                    biz.trial_ends_at = base_time + timedelta(days=30)
            db.session.commit()

            sync_postgres_sequences()

        except Exception as e:
            db.session.rollback()
            print(f"[Auto-Migrate] Warning during migration: {e}")

    if app:
        with app.app_context():
            _migrate()
    else:
        _migrate()

__all__ = [
    "db",
    "Business",
    "Doctor",
    "Service",
    "Customer",
    "Appointment",
    "Conversation",
    "Message",
    "Reminder",
    "DoctorSchedule",
    "DoctorLeave",
    "User",
    "SubscriptionRequest",
    "ClinicWhatsAppAccount",
    "ClinicInvitation",
    "auto_migrate_db",
    "sync_postgres_sequences",
]


