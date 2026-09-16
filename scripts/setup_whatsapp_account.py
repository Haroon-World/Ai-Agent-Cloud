#!/usr/bin/env python3
"""
Clinic WhatsApp Account Setup & Configuration Script for ClinicConnect AI
Configures or updates Meta WhatsApp Cloud API credentials for a specific clinic tenant (business_id).

Supports:
- Reads credentials from CLI arguments or environment variables.
- Direct PostgreSQL (Render) or SQLite connection.
- Creates or updates ClinicWhatsAppAccount records.
- Generates ready-to-use Meta Developer Portal Webhook Callback URL and Verify Token.
- Lists configured WhatsApp accounts across tenants.

Usage:
  python scripts/setup_whatsapp_account.py --list
  python scripts/setup_whatsapp_account.py \
      --business-id 1 \
      --phone-number-id "1313879111808444" \
      --waba-id "993720013281872" \
      --display-phone-number "+923001234567" \
      --access-token "EAA..." \
      --webhook-verify-token "clinic_connect_secret_2026" \
      --render-app "clinicconnect-ai"
"""

import os
import sys
import argparse
from datetime import datetime, timezone
from dotenv import load_dotenv

# Ensure project root is in sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Load environment variables
load_dotenv(os.path.join(BASE_DIR, ".env"))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from models import db, Business, ClinicWhatsAppAccount


def clean_val(val: str, prefix: str = "") -> str:
    """Clean quoted string and remove redundant key= prefixes if present."""
    if not val:
        return ""
    s = str(val).strip().strip("'").strip('"')
    if prefix and s.startswith(prefix + "="):
        s = s[len(prefix) + 1:].strip().strip("'").strip('"')
    return s


def clean_db_url(raw_url: str) -> str:
    """Normalize PostgreSQL connection string (handle postgres:// -> postgresql://)."""
    if not raw_url:
        instance_path = os.path.join(BASE_DIR, "instance", "ai_business_agent.db")
        return f"sqlite:///{instance_path}"
    url = raw_url.strip().strip("'").strip('"')
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


def get_db_session(db_url: str):
    """Create SQLAlchemy engine and session bound to the specified URL."""
    is_sqlite = db_url.startswith("sqlite")
    engine_options = {
        "connect_args": {"timeout": 30}
    } if is_sqlite else {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_size": 10,
        "max_overflow": 20,
    }
    engine = create_engine(db_url, **engine_options)
    # Ensure tables exist
    db.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return engine, Session()


def list_accounts(session):
    """List all configured Clinic WhatsApp accounts."""
    print("\n" + "=" * 75)
    print(" Configured Clinic WhatsApp Accounts")
    print("=" * 75)
    accounts = session.query(ClinicWhatsAppAccount).all()
    if not accounts:
        print("  No WhatsApp accounts found in the database.")
        print("=" * 75 + "\n")
        return

    print(f" {'ID':<4} | {'Clinic ID':<10} | {'Clinic Name':<22} | {'Phone Number ID':<18} | {'Display Phone'}")
    print("-" * 75)
    for acc in accounts:
        biz_name = acc.business.name if acc.business else "N/A"
        print(f" {acc.id:<4} | {acc.business_id:<10} | {biz_name[:20]:<22} | {acc.phone_number_id:<18} | {acc.display_phone_number}")
    print("=" * 75 + "\n")


def setup_account(
    db_url: str,
    business_id: int,
    phone_number_id: str,
    waba_id: str = None,
    display_phone_number: str = None,
    access_token: str = None,
    webhook_verify_token: str = None,
    app_secret: str = None,
    is_active: bool = True,
    render_app: str = None,
):
    engine, session = get_db_session(db_url)

    try:
        # 1. Verify Clinic / Business exists
        clinic = session.get(Business, business_id)
        if not clinic:
            print(f"\n[Warning] Clinic with Business ID {business_id} does not exist in the database.")
            clinics = session.query(Business).all()
            if clinics:
                print("Available Clinics:")
                for c in clinics:
                    print(f"  - ID {c.id}: {c.name} ({c.phone})")
            else:
                print("No clinics exist. Creating default Business record (ID: 1)...")
                clinic = Business(
                    id=business_id,
                    name="Arfa Polyclinic",
                    business_type="polyclinic",
                    address="Plot 42-B, Main Boulevard, Gulberg III, Lahore",
                    phone="+92 42 35789000",
                    email="admin@arfaclinic.com",
                    timezone="Asia/Karachi",
                )
                session.add(clinic)
                session.flush()

        clinic_name = clinic.name if clinic else f"Clinic #{business_id}"

        # 2. Check if a ClinicWhatsAppAccount already exists for this clinic
        account = session.query(ClinicWhatsAppAccount).filter_by(business_id=business_id).first()
        is_update = account is not None

        if is_update:
            print(f"\n[Update] Updating existing WhatsApp account (ID: {account.id}) for clinic: {clinic_name} (ID: {business_id})")
            account.phone_number_id = phone_number_id
            if waba_id:
                account.waba_id = waba_id
            if display_phone_number:
                account.display_phone_number = display_phone_number
            if access_token:
                account.access_token = access_token
            if webhook_verify_token:
                account.webhook_verify_token = webhook_verify_token
            if app_secret:
                account.app_secret = app_secret
            account.is_active = is_active
            account.updated_at = datetime.now(timezone.utc)
        else:
            print(f"\n[Create] Creating new WhatsApp account record for clinic: {clinic_name} (ID: {business_id})")
            account = ClinicWhatsAppAccount(
                business_id=business_id,
                phone_number_id=phone_number_id,
                waba_id=waba_id or None,
                display_phone_number=display_phone_number or "+923001234567",
                access_token=access_token or None,
                webhook_verify_token=webhook_verify_token or "clinic_connect_secret_2026",
                app_secret=app_secret or None,
                is_active=is_active,
            )
            session.add(account)

        session.commit()
        print(f"[Success] Database updated successfully! Record ID: {account.id}")

        # 3. Construct Webhook Callback URL
        app_domain = render_app or os.getenv("RENDER_EXTERNAL_HOSTNAME") or os.getenv("RENDER_EXTERNAL_URL") or "<your-app>.onrender.com"
        app_domain = app_domain.strip().strip("'").strip('"')
        if app_domain.startswith("http://") or app_domain.startswith("https://"):
            callback_url = f"{app_domain.rstrip('/')}/api/whatsapp/webhook"
        else:
            if "." not in app_domain and "localhost" not in app_domain and not app_domain.startswith("<"):
                app_domain = f"{app_domain}.onrender.com"
            callback_url = f"https://{app_domain.rstrip('/')}/api/whatsapp/webhook"

        verify_token = account.webhook_verify_token or webhook_verify_token or "clinic_connect_secret_2026"

        # 4. Display formatted summary and Meta configuration instructions
        print("\n" + "=" * 70)
        print("  Meta WhatsApp Cloud API Configuration Details")
        print("=" * 70)
        print(f" Clinic ID              : {account.business_id} ({clinic_name})")
        print(f" Record ID              : {account.id}")
        print(f" Phone Number ID        : {account.phone_number_id}")
        print(f" WABA Account ID        : {account.waba_id or 'Not specified'}")
        print(f" Display Phone Number   : {account.display_phone_number}")
        print(f" Channel Status         : {'ACTIVE' if account.is_active else 'INACTIVE'}")
        print(f" Access Token Saved     : {'YES (' + str(len(account.access_token or '')) + ' chars)' if account.access_token else 'NO'}")
        print("-" * 70)
        print("  META DEVELOPER PORTAL SETUP INSTRUCTIONS:")
        print("-" * 70)
        print(" 1. Go to: https://developers.facebook.com/apps/")
        print(" 2. Select your App -> WhatsApp -> Configuration")
        print(" 3. Click 'Edit' under Callback URL and paste the following:")
        print()
        print(f"    Callback URL : {callback_url}")
        print(f"    Verify Token : {verify_token}")
        print()
        print(" 4. Click 'Verify and save'")
        print(" 5. Under 'Webhook fields', click 'Manage' and subscribe to:")
        print("    [X] messages")
        print("-" * 70)
        print("  QUICK WEBHOOK VERIFICATION TEST (CURL):")
        print("-" * 70)
        print(f' curl -i -X GET "{callback_url}?hub.mode=subscribe&hub.verify_token={verify_token}&hub.challenge=1158201444"')
        print(" (Expected response: 1158201444 with HTTP status 200 OK)")
        print("=" * 70 + "\n")

    except Exception as e:
        session.rollback()
        print(f"\n[Error] Failed to setup WhatsApp account: {e}")
        sys.exit(1)
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(
        description="Configure Meta WhatsApp Cloud API credentials for a Clinic tenant."
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all configured Clinic WhatsApp accounts in the database",
    )
    parser.add_argument(
        "--db-url",
        default=os.getenv("DATABASE_URL", ""),
        help="Database URL (PostgreSQL or SQLite). Defaults to DATABASE_URL env var or local SQLite.",
    )
    parser.add_argument(
        "--business-id",
        type=int,
        default=int(os.getenv("BUSINESS_ID", "1")),
        help="Target Clinic Business ID (default: 1)",
    )
    parser.add_argument(
        "--phone-number-id",
        default=clean_val(os.getenv("WHATSAPP_PHONE_NUMBER_ID", "1313879111808444"), "WHATSAPP_PHONE_NUMBER_ID"),
        help="Meta Graph API Phone Number ID (e.g. 1313879111808444)",
    )
    parser.add_argument(
        "--waba-id",
        default=clean_val(os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID", "993720013281872"), "WHATSAPP_BUSINESS_ACCOUNT_ID"),
        help="WhatsApp Business Account ID (WABA ID)",
    )
    parser.add_argument(
        "--display-phone-number",
        default=clean_val(os.getenv("DISPLAY_PHONE_NUMBER", "+923001234567"), "DISPLAY_PHONE_NUMBER"),
        help="Display Phone Number (e.g. +923001234567)",
    )
    parser.add_argument(
        "--access-token",
        default=clean_val(os.getenv("WHATSAPP_ACCESS_TOKEN", ""), "WHATSAPP_ACCESS_TOKEN"),
        help="Meta System User or User Access Token",
    )
    parser.add_argument(
        "--webhook-verify-token",
        default=clean_val(os.getenv("WHATSAPP_WEBHOOK_VERIFY_TOKEN", "clinic_connect_secret_2026"), "WHATSAPP_WEBHOOK_VERIFY_TOKEN"),
        help="Webhook verify secret token (default: clinic_connect_secret_2026)",
    )
    parser.add_argument(
        "--app-secret",
        default=clean_val(os.getenv("WHATSAPP_APP_SECRET", ""), "WHATSAPP_APP_SECRET"),
        help="Meta App Secret for HMAC signature validation",
    )
    parser.add_argument(
        "--render-app",
        default=os.getenv("RENDER_APP_NAME", os.getenv("RENDER_EXTERNAL_HOSTNAME", "")),
        help="Render app name or hostname (e.g. clinicconnect-ai or clinicconnect-ai.onrender.com)",
    )
    parser.add_argument(
        "--inactive",
        action="store_true",
        help="Set account channel status to inactive",
    )

    args = parser.parse_args()

    db_url = clean_db_url(args.db_url)

    if args.list:
        engine, session = get_db_session(db_url)
        list_accounts(session)
        session.close()
        return

    # Check required inputs
    if not args.phone_number_id:
        print("[Error] --phone-number-id or WHATSAPP_PHONE_NUMBER_ID is required.")
        sys.exit(1)

    setup_account(
        db_url=db_url,
        business_id=args.business_id,
        phone_number_id=args.phone_number_id,
        waba_id=args.waba_id,
        display_phone_number=args.display_phone_number,
        access_token=args.access_token,
        webhook_verify_token=args.webhook_verify_token,
        app_secret=args.app_secret,
        is_active=not args.inactive,
        render_app=args.render_app,
    )


if __name__ == "__main__":
    main()
