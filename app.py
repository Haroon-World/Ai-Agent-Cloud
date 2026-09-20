import os
import sys
from flask import Flask, render_template, redirect, url_for, request, session
from config.config import Config
from models import db, Business, auto_migrate_db
from routes.chat import chat_bp
from routes.appointments import appointments_bp
from routes.admin import admin_bp
from routes.platform import platform_bp
from routes.whatsapp import whatsapp_bp
from seed import seed_database

# Ensure stdout/stderr use UTF-8 on Windows so emoji in LLM responses
# don't crash the dev server with a cp1252 UnicodeEncodeError.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

def init_db(app):
    """Ensure database schema exists, missing columns are migrated, and seed data is populated."""
    with app.app_context():
        try:
            db.create_all()
            auto_migrate_db(app)
            seed_database(app)
        except Exception as e:
            print(f"[DB Init Warning]: {e}")

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize SQLAlchemy
    db.init_app(app)

    @app.template_filter("format_12hr")
    def format_12hr(time_str):
        if not time_str:
            return ""
        time_str = str(time_str).strip()
        upper = time_str.upper()
        if "AM" in upper or "PM" in upper:
            return time_str
        try:
            parts = time_str.split(":")
            hr = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 else 0
            if hr == 24:
                hr = 0
            period = "AM" if hr < 12 else "PM"
            hr12 = hr % 12
            if hr12 == 0:
                hr12 = 12
            return f"{hr12:02d}:{minute:02d} {period}"
        except Exception:
            return time_str

    # Register Blueprints
    app.register_blueprint(chat_bp)
    app.register_blueprint(appointments_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(platform_bp, url_prefix="/platform")
    app.register_blueprint(whatsapp_bp, url_prefix="/api/whatsapp")

    @app.route("/")
    @app.route("/clinic/<int:clinic_id>")
    def index(clinic_id=None):
        # When an admin is already logged in and accesses the root URL, direct them straight to their dashboard
        if not clinic_id and session.get("user_id"):
            if session.get("is_platform_admin") and not session.get("business_id"):
                return redirect(url_for("platform_bp.dashboard"))
            return redirect(url_for("admin_bp.dashboard"))

        target_id = clinic_id or request.args.get("clinic") or request.args.get("business_id")
        business = None
        if target_id and str(target_id).isdigit():
            business = db.session.get(Business, int(target_id))
        elif session.get("business_id"):
            business = db.session.get(Business, session.get("business_id"))
        elif session.get("active_clinic_id"):
            business = db.session.get(Business, session.get("active_clinic_id"))

        if not business:
            business = db.session.get(Business, Config.DEFAULT_BUSINESS_ID)
        return render_template("index.html", business=business)

    init_db(app)

    return app

if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("PORT", 5001))
    debug_mode = os.getenv("FLASK_ENV", "production").lower() == "development"
    print(f"[AI Agent] Server running at: http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
