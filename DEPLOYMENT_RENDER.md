# ClinicConnect AI - Render Cloud Deployment & Operations Guide

This guide provides an end-to-end walkthrough for deploying **ClinicConnect AI** to [Render](https://render.com) using **Gunicorn**, **Render Web Services**, **Render PostgreSQL**, and connecting to the **Meta WhatsApp Cloud API**.

---

## Table of Contents
1. [Architecture Overview](#1-architecture-overview)
2. [Prerequisites](#2-prerequisites)
3. [Deployment Method A: Render Blueprint (Recommended)](#3-deployment-method-a-render-blueprint-recommended)
4. [Deployment Method B: Manual Render Provisioning](#4-deployment-method-b-manual-render-provisioning)
5. [Obtaining Render PostgreSQL Connection Strings](#5-obtaining-render-postgresql-connection-strings)
6. [Migrating Local SQLite Data to Render PostgreSQL](#6-migrating-local-sqlite-data-to-render-postgresql)
7. [Configuring WhatsApp Cloud API for Clinic Tenants](#7-configuring-whatsapp-cloud-api-for-clinic-tenants)
8. [Configuring Meta Developer Console Webhook](#8-configuring-meta-developer-console-webhook)
9. [Verifying Live Handshake & WhatsApp Message Flow](#9-verifying-live-handshake--whatsapp-message-flow)
10. [Troubleshooting & Production Best Practices](#10-troubleshooting--production-best-practices)

---

## 1. Architecture Overview

```
                          +------------------------------------------------+
                          |                   RENDER CLOUD                 |
                          |                                                |
Meta WhatsApp Cloud API   |  +-------------------+    Internal Connection  |
[Webhook POST / GET] ---->|  |  clinic-connect-ai|------------------------+
                          |  |  (Gunicorn WSGI)  |                         |
                          |  +-------------------+                         v
                          |           ^                          +-------------------+
                          |           | External Connection      | clinic-connect-db |
                          +-----------|--------------------------|(Managed PostgreSQL|
                                      |                          +-------------------+
                                      |                                    ^
                           Developer CLI (Local)                           |
                     [migrate_sqlite_to_postgres.py] ----------------------+
```

- **Runtime**: Python 3.11+ on Linux container.
- **Application Server**: Gunicorn with 2 worker processes, 4 threads per worker, and 120-second timeout.
- **Database**: Render Managed PostgreSQL (`clinic_connect_prod`).
- **Communication Channels**:
  - Web UI / Patient Portal: `https://<service-name>.onrender.com`
  - Admin Dashboard: `https://<service-name>.onrender.com/admin/login`
  - WhatsApp Cloud API Webhook: `https://<service-name>.onrender.com/api/whatsapp/webhook`

---

## 2. Prerequisites

1. A [Render Account](https://render.com).
2. A GitHub or GitLab account with repository access for `AI-Agent-Render`.
3. A [Meta for Developers](https://developers.facebook.com/) account with:
   - A WhatsApp Business App created.
   - A registered WhatsApp Test/Production Phone Number.
   - A Permanent System User Access Token.
4. API keys for your preferred LLM provider:
   - **Groq API Key** (`gsk_...`) or **Gemini API Key** (`AIzaSy...`).

---

## 3. Deployment Method A: Render Blueprint (Recommended)

The repository includes `render.yaml` which automatically provisions both the PostgreSQL database and the Web Service with proper linkages.

### Step 1: Push Code to GitHub
Ensure `render.yaml`, `Procfile`, and `requirements.txt` are committed and pushed to your GitHub repository:
```bash
git add requirements.txt Procfile render.yaml scripts/ DEPLOYMENT_RENDER.md
git commit -m "feat(devops): add Render Blueprint, Procfile, and migration scripts"
git push origin main
```

### Step 2: Create Blueprint Instance on Render
1. Log in to your [Render Dashboard](https://dashboard.render.com).
2. Click **New +** in the top navigation bar and select **Blueprint**.
3. Connect your GitHub repository (`AI-Agent-Render`).
4. Render will detect `render.yaml` and display the resources to be created:
   - **Web Service**: `clinic-connect-ai`
   - **Database**: `clinic-connect-db` (PostgreSQL)
5. Review the blueprint and click **Apply**.

### Step 3: Enter Environment Variables in Dashboard
Render will prompt you for variables marked `sync: false`:
| Environment Variable | Required / Optional | Description | Example / Recommended |
| :--- | :--- | :--- | :--- |
| `LLM_PROVIDER` | **Required** | LLM backend to use | `groq` or `gemini` |
| `GROQ_API_KEY` | Conditional | Required if `LLM_PROVIDER=groq` | `gsk_...` |
| `GEMINI_API_KEY` | Conditional | Required if `LLM_PROVIDER=gemini` | `AIzaSy...` |
| `ADMIN_USERNAME` | Optional | Default clinic admin username | `admin` |
| `ADMIN_PASSWORD` | Optional | Default clinic admin password | Choose a strong password |
| `PLATFORM_ADMIN_USERNAME` | Optional | Platform owner superadmin | `clinicconnectaipro` |
| `PLATFORM_ADMIN_PASSWORD` | **Required** | Superadmin portal password | Choose a strong password |
| `WHATSAPP_PHONE_NUMBER_ID` | Optional | Meta WhatsApp Phone Number ID | e.g. `1313879111808444` |
| `WHATSAPP_BUSINESS_ACCOUNT_ID` | Optional | Meta WABA ID | e.g. `993720013281872` |
| `WHATSAPP_ACCESS_TOKEN` | Optional | Permanent System User Token | `EAAB...` |
| `WHATSAPP_WEBHOOK_VERIFY_TOKEN`| Optional | Secret token for Meta Webhook | `clinic_connect_secret_2026` |
| `WHATSAPP_APP_SECRET` | Optional | Meta App Secret for signature | From Meta App Basic Settings |

Render will automatically link `DATABASE_URL` and generate a cryptographically secure `SECRET_KEY`.

---

## 4. Deployment Method B: Manual Render Provisioning

If you prefer provisioning resources manually without blueprints:

### Step 1: Create PostgreSQL Database
1. Go to [Render Dashboard](https://dashboard.render.com) -> **New +** -> **PostgreSQL**.
2. Configure settings:
   - **Name**: `clinic-connect-db`
   - **Database**: `clinic_connect_prod`
   - **User**: `clinic_admin`
   - **Region**: Choose closest to your users (e.g. `Oregon` or `Frankfurt`).
   - **Plan**: `Starter` (or `Free`).
3. Click **Create Database**.
4. Once created, copy the **Internal Database URL** (for the Web Service) and **External Database URL** (for local migrations).

### Step 2: Create Web Service
1. In Render Dashboard, click **New +** -> **Web Service**.
2. Connect your repository.
3. Configure settings:
   - **Name**: `clinic-connect-ai`
   - **Region**: *Must match the database region selected above.*
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn "app:create_app()" --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120`
   - **Plan**: `Starter` (or `Free`).
4. Add Environment Variables:
   - `PYTHON_VERSION`: `3.11.9`
   - `FLASK_ENV`: `production`
   - `DATABASE_URL`: *Paste the **Internal Database URL** from Step 1.*
   - `SECRET_KEY`: Generate a random 32-character string.
   - `LLM_PROVIDER`: `groq` (or `gemini`)
   - `GROQ_API_KEY`: Your Groq API key
   - `GEMINI_API_KEY`: Your Gemini API key
   - `WHATSAPP_WEBHOOK_VERIFY_TOKEN`: `clinic_connect_secret_2026`
   - `PLATFORM_ADMIN_PASSWORD`: Your chosen secure password
5. Click **Deploy Web Service**.

---

## 5. Obtaining Render PostgreSQL Connection Strings

Render provides two distinct connection strings for your PostgreSQL instance:

1. **Internal Database URL** (`postgres://clinic_admin:...@dpg-xxx-a:5432/clinic_connect_prod`):
   - **Used exclusively** by Render services running within the same Render private network (e.g., your web service).
   - Has zero network latency overhead and does not consume external egress bandwidth.
2. **External Database URL** (`postgresql://clinic_admin:...@dpg-xxx-a.oregon-postgres.render.com/clinic_connect_prod`):
   - **Used by developers** connecting from outside Render (e.g. from your local development machine or terminal).
   - Required when running data migration scripts or database management tools like pgAdmin/DBeaver.

### Where to Find It:
1. Navigate to **Render Dashboard** -> click your database **`clinic-connect-db`**.
2. Scroll to the **Connections** panel on the database info page.
3. Locate **External Database URL** and click the copy icon.

---

## 6. Migrating Local SQLite Data to Render PostgreSQL

If you have existing clinic records, appointments, doctors, or messages in your local SQLite database (`instance/ai_business_agent.db`), use the included migration script.

### Step 1: Install PostgreSQL Driver Locally (if not already installed)
```bash
pip install psycopg2-binary
```

### Step 2: Test Data with Dry-Run
Run the migration script in dry-run mode to inspect your SQLite data:
```bash
python scripts/migrate_sqlite_to_postgres.py --dry-run
```
Output preview:
```
[INFO] Source SQLite: D:\AI-Agent-Render\instance\ai_business_agent.db
[INFO] Discovered 14 tables in SQLite database.
[INFO] === DRY RUN MODE: Inspecting SQLite tables and row counts ===
[INFO]   [Table] appointments              : 1 rows
[INFO]   [Table] businesses                : 1 rows
[INFO]   [Table] doctors                   : 2 rows
[INFO]   [Table] doctor_schedules          : 14 rows
[INFO]   [Table] services                  : 7 rows
[INFO]   [Table] messages                  : 64 rows
...
```

### Step 3: Execute Live Migration to Render PostgreSQL
Pass the **External Database URL** obtained in Section 5:
```bash
python scripts/migrate_sqlite_to_postgres.py --target-url "postgresql://clinic_admin:YOUR_PASSWORD@dpg-xxx.oregon-postgres.render.com/clinic_connect_prod"
```

The script will:
1. Auto-create all relational tables on PostgreSQL using SQLAlchemy metadata.
2. Preserve foreign key ordering across 14 tables.
3. Copy all rows without duplicating existing records.
4. Automatically reset PostgreSQL primary key sequences (`pg_get_serial_sequence`) so future web inserts start at the correct auto-increment ID.

---

## 7. Configuring WhatsApp Cloud API for Clinic Tenants

You can register your clinic's WhatsApp Cloud API credentials directly into Render PostgreSQL from your local terminal using `setup_whatsapp_account.py`.

### Required Meta Credentials:
From your [Meta Developer Console](https://developers.facebook.com/) -> WhatsApp -> API Setup:
- **Phone Number ID**: 15-16 digit ID assigned to your phone number.
- **WhatsApp Business Account ID (WABA ID)**: 15-16 digit account ID.
- **System User Access Token**: Permanent bearer token (`EAAB...`).
- **App Secret**: Located under Meta Dashboard -> App Settings -> Basic.

### Run Configuration Script:
```bash
python scripts/setup_whatsapp_account.py \
    --business-id 1 \
    --phone-number-id "1313879111808444" \
    --waba-id "993720013281872" \
    --display-phone "+923001234567" \
    --access-token "EAABxxxxxx..." \
    --verify-token "clinic_connect_secret_2026" \
    --app-secret "your_meta_app_secret" \
    --target-url "postgresql://clinic_admin:PASSWORD@dpg-xxx.oregon-postgres.render.com/clinic_connect_prod"
```

*Tip: You can also update these credentials via the Clinic Admin Web Portal at `https://<render-service>.onrender.com/admin/settings`.*

---

## 8. Configuring Meta Developer Console Webhook

Once your Render Web Service is running (`Live` status in Render):

1. Go to [Meta for Developers](https://developers.facebook.com/).
2. Select your App -> In the left sidebar, click **WhatsApp** -> **Configuration**.
3. Under the **Webhook** section, click **Edit**:
   - **Callback URL**:
     ```
     https://<your-render-service>.onrender.com/api/whatsapp/webhook
     ```
     *(Replace `<your-render-service>` with your actual Render URL, e.g. `https://clinic-connect-ai.onrender.com/api/whatsapp/webhook`)*
   - **Verify Token**:
     ```
     clinic_connect_secret_2026
     ```
     *(Or whichever custom token you configured in `WHATSAPP_WEBHOOK_VERIFY_TOKEN`)*
4. Click **Verify and Save**.
   - Meta will send a `GET` request to your endpoint.
   - The server will respond with the challenge string (`HTTP 200 OK`).
   - If successful, a green checkmark will appear.
5. Under **Webhook fields**, click **Manage**:
   - Locate the row for **`messages`**.
   - Click **Subscribe**.

---

## 9. Verifying Live Handshake & WhatsApp Message Flow

### 1. Test Verification Handshake (cURL / Browser)
You can verify the webhook handshake directly from your terminal:
```bash
curl -i -X GET "https://<your-render-service>.onrender.com/api/whatsapp/webhook?hub.mode=subscribe&hub.challenge=test_challenge_123&hub.verify_token=clinic_connect_secret_2026"
```
**Expected Response**:
```http
HTTP/1.1 200 OK
Content-Type: text/plain; charset=utf-8

test_challenge_123
```

### 2. Test Live WhatsApp Interaction
1. From your personal mobile phone, send a WhatsApp message to your Meta registered phone number (or test number):
   > *"Hi, I would like to book a dental checkup tomorrow morning with Dr. Ahmed."*
2. Monitor the Render live logs:
   - Go to **Render Dashboard** -> **`clinic-connect-ai`** -> **Logs**.
   - You will see:
     ```
     [WhatsApp Webhook] Incoming payload: {'object': 'whatsapp_business_account', ...}
     [WhatsApp Service] Received message from +92300... for Business ID: 1
     [AI Agent] Generating response via Groq / Gemini...
     [WhatsApp Service] Outgoing message sent successfully (Status 200).
     ```
3. Your mobile phone should receive an intelligent, formatted appointment booking reply within 2-3 seconds.

### 3. Check Clinic Admin Dashboard
1. Open `https://<your-render-service>.onrender.com/admin/login` in your browser.
2. Sign in with:
   - Username: `admin` (or your configured `ADMIN_USERNAME`)
   - Password: Your configured `ADMIN_PASSWORD`
3. Check the **Appointments** and **Inbox / Live Chat** tabs to see the conversation logged in real-time.

---

## 10. Troubleshooting & Production Best Practices

### Issue: Meta Webhook Fails Verification (403 Forbidden)
- **Cause**: Verify Token mismatch between Meta Developer Console and Render environment.
- **Fix**: Check `WHATSAPP_WEBHOOK_VERIFY_TOKEN` in Render Environment variables. Ensure there are no leading or trailing whitespace characters.

### Issue: Webhook POST returns `Invalid signature (403)`
- **Cause**: Meta sends an `X-Hub-Signature-256` HMAC header. If `WHATSAPP_APP_SECRET` is set in Render, it must match the App Secret from Meta Developer Console (Settings -> Basic -> App Secret).
- **Fix**: Verify your App Secret or temporarily unset `WHATSAPP_APP_SECRET` during initial testing (the server falls back to open signature mode when unset).

### Issue: Render Free Plan Sleep / Spin-down Delay
- **Behavior**: On Render Free tier, web services spin down after 15 minutes of inactivity. The first incoming WhatsApp message can take 30-50 seconds to respond as the container cold-starts.
- **Recommendation**: For production healthcare use cases, use the Render **Starter plan ($7/mo)** which runs 24/7 without spin-down or cold-starts.

### Issue: Gunicorn Worker Timeout (120s)
- Complex audio transcription (Whisper STT) or long LLM chains require sufficient timeout.
- The default Procfile and blueprint configure `--timeout 120` to prevent worker kills during speech processing.

### Checking Deployment Status
To inspect running Gunicorn workers and system logs:
```bash
# View last 100 log lines on Render
# In Dashboard -> clinic-connect-ai -> Logs
```

---

*ClinicConnect AI is now fully operational on Render Cloud with PostgreSQL persistence and Meta WhatsApp Cloud integration.*
