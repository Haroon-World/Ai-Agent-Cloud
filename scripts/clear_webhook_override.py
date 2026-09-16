import sys
import json
import urllib.request
import urllib.parse

PHONE_ID = "1313879111808444"
WABA_ID = "993720013281872"
RENDER_WEBHOOK = "https://clinic-connect-ai.onrender.com/api/whatsapp/webhook"
VERIFY_TOKEN = "clinic_connect_secret_2026"

def clear_and_set_webhook(token):
    token = token.strip().strip("'").strip('"')
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    print("=" * 60)
    print("Step 1: Check current phone webhook configuration...")
    url = f"https://graph.facebook.com/v19.0/{PHONE_ID}?fields=webhook_configuration,display_phone_number"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            print("Current config:", json.dumps(data, indent=2))
    except Exception as e:
        print("Error checking config:", getattr(e, 'read', lambda: str(e))())

    print("\n" + "=" * 60)
    print("Step 2: Clearing phone-level webhook override...")
    # Setting override_callback_uri to empty string clears the phone-level override
    url = f"https://graph.facebook.com/v19.0/{PHONE_ID}"
    body = json.dumps({"webhook_configuration": {"override_callback_uri": ""}}).encode('utf-8')
    try:
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req) as resp:
            print("Phone override clear result:", resp.read().decode())
    except urllib.error.HTTPError as e:
        print("Phone clear HTTP error:", e.code, e.read().decode())
    except Exception as e:
        print("Phone clear error:", e)

    print("\n" + "=" * 60)
    print("Step 3: Pointing WABA subscription to Render webhook...")
    url_waba = f"https://graph.facebook.com/v19.0/{WABA_ID}/subscribed_apps"
    form_data = urllib.parse.urlencode({
        "override_callback_uri": RENDER_WEBHOOK,
        "verify_token": VERIFY_TOKEN
    }).encode('utf-8')
    try:
        req = urllib.request.Request(
            url_waba,
            data=form_data,
            headers={"Authorization": f"Bearer {token}"},
            method="POST"
        )
        with urllib.request.urlopen(req) as resp:
            print("WABA subscription result:", resp.read().decode())
    except urllib.error.HTTPError as e:
        print("WABA subscription HTTP error:", e.code, e.read().decode())
    except Exception as e:
        print("WABA subscription error:", e)

    print("\n" + "=" * 60)
    print("Step 4: Verifying final phone webhook configuration...")
    url = f"https://graph.facebook.com/v19.0/{PHONE_ID}?fields=webhook_configuration"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as resp:
            final_data = json.loads(resp.read().decode())
            print("Final phone config:", json.dumps(final_data, indent=2))
            phone_override = final_data.get("webhook_configuration", {}).get("phone_number")
            app_webhook = final_data.get("webhook_configuration", {}).get("application")
            if not phone_override or "loca.lt" not in phone_override:
                print("\n SUCCESS! The old localtunnel override is GONE!")
            else:
                print("\n Warning: phone_number override still present:", phone_override)
    except Exception as e:
        print("Error verifying final config:", getattr(e, 'read', lambda: str(e))())

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/clear_webhook_override.py <TOKEN>")
        sys.exit(1)
    clear_and_set_webhook(sys.argv[1])
