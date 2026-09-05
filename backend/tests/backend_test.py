"""Backend regression tests for Klinik KF WA Agent."""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://8eaa804a-42f2-4374-b7f7-711be45e5d80.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
WEBHOOK_TOKEN = "whk_9c2f7a1e5b8d3046"


@pytest.fixture(scope="session")
def token():
    r = requests.post(f"{API}/auth/login", json={"username": "admin", "password": "admin123"}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="session")
def auth(token):
    return {"Authorization": f"Bearer {token}"}


# --- Health & Auth ---
def test_health():
    r = requests.get(f"{API}/health", timeout=10)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_login_wrong_password():
    r = requests.post(f"{API}/auth/login", json={"username": "admin", "password": "wrong"}, timeout=10)
    assert r.status_code == 401


def test_login_success(token):
    assert isinstance(token, str) and len(token) > 20


def test_me(auth):
    r = requests.get(f"{API}/auth/me", headers=auth, timeout=10)
    assert r.status_code == 200
    assert r.json()["username"] == "admin"


# --- Dashboard ---
def test_dashboard_stats(auth):
    r = requests.get(f"{API}/dashboard/stats", headers=auth, timeout=15)
    assert r.status_code == 200
    d = r.json()
    for k in ["conversations", "appointments", "messages_total", "containment_rate", "trend", "intent_distribution"]:
        assert k in d


def test_notifications(auth):
    r = requests.get(f"{API}/notifications", headers=auth, timeout=10)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# --- WhatsApp status/connect/pairing ---
def test_wa_status(auth):
    r = requests.get(f"{API}/whatsapp/status", headers=auth, timeout=15)
    # gateway may be unauth/loading but endpoint should not 500
    assert r.status_code in (200, 502, 503), r.text


def test_wa_pairing_invalid(auth):
    r = requests.post(f"{API}/whatsapp/pairing-code", headers=auth, json={"phone": "12"}, timeout=15)
    assert r.status_code == 400


# --- Webhook / workflow ---
SENDER = f"628{int(time.time())}@s.whatsapp.net"


def _wh(payload):
    return requests.post(f"{API}/whatsapp/webhook",
                         headers={"x-webhook-token": WEBHOOK_TOKEN},
                         json=payload, timeout=30)


def test_webhook_unauthorized():
    r = requests.post(f"{API}/whatsapp/webhook", json={"sender": SENDER, "text": "halo"}, timeout=10)
    assert r.status_code == 401


def test_webhook_welcome_menu():
    r = _wh({"sender": SENDER, "text": "halo", "messageType": "text", "pushName": "Tester"})
    assert r.status_code == 200, r.text
    replies = r.json()["replies"]
    assert replies and any("menu" in x.lower() or "selamat datang" in x.lower() for x in replies)


def test_webhook_booking_flow(auth):
    s = f"628{uuid.uuid4().hex[:10]}@s.whatsapp.net"
    # 1st msg -> welcome
    r = _wh({"sender": s, "text": "hai", "messageType": "text", "pushName": "Budi"})
    assert r.status_code == 200
    # start booking
    r = _wh({"sender": s, "text": "3", "messageType": "text"})
    assert r.status_code == 200
    assert any("layanan" in x.lower() or "janji" in x.lower() for x in r.json()["replies"])
    # service umum
    r = _wh({"sender": s, "text": "1", "messageType": "text"})
    assert r.status_code == 200
    # date besok
    r = _wh({"sender": s, "text": "besok", "messageType": "text"})
    assert r.status_code == 200
    reply = r.json()["replies"][0]
    assert "Slot tersedia" in reply or "slot" in reply.lower()
    # pick slot 1
    r = _wh({"sender": s, "text": "1", "messageType": "text"})
    assert r.status_code == 200
    # name (patient_name already Budi from pushName so may skip)
    reply = r.json()["replies"][0]
    if "nama" in reply.lower():
        r = _wh({"sender": s, "text": "Budi Santoso", "messageType": "text"})
        assert r.status_code == 200
    # confirm
    r = _wh({"sender": s, "text": "ya", "messageType": "text"})
    assert r.status_code == 200
    reply = r.json()["replies"][0]
    assert "dikonfirmasi" in reply.lower() or "✅" in reply
    # Verify appointment exists
    ar = requests.get(f"{API}/appointments", headers=auth, timeout=10)
    assert ar.status_code == 200
    appts = ar.json()
    assert any(a["patient_phone"] == s.split("@")[0] for a in appts)


def test_webhook_handoff_keyword():
    s = f"628{uuid.uuid4().hex[:10]}@s.whatsapp.net"
    _wh({"sender": s, "text": "halo", "messageType": "text"})
    r = _wh({"sender": s, "text": "mau bicara dengan staf", "messageType": "text"})
    assert r.status_code == 200
    assert r.json()["handoff"] is True


def test_webhook_image_handoff():
    s = f"628{uuid.uuid4().hex[:10]}@s.whatsapp.net"
    _wh({"sender": s, "text": "halo", "messageType": "text"})
    r = _wh({"sender": s, "text": "", "messageType": "image"})
    assert r.status_code == 200
    assert r.json()["handoff"] is True


def test_webhook_llm_answer():
    s = f"628{uuid.uuid4().hex[:10]}@s.whatsapp.net"
    _wh({"sender": s, "text": "halo", "messageType": "text"})
    r = _wh({"sender": s, "text": "apakah klinik menerima BPJS?", "messageType": "text"})
    assert r.status_code == 200
    reply = r.json()["replies"][0]
    assert len(reply) > 5


# --- Conversations ---
def test_conversations_list(auth):
    r = requests.get(f"{API}/conversations", headers=auth, timeout=10)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_conversation_takeover_resume(auth):
    s = f"628{uuid.uuid4().hex[:10]}@s.whatsapp.net"
    _wh({"sender": s, "text": "halo", "messageType": "text"})
    convs = requests.get(f"{API}/conversations", headers=auth, timeout=10).json()
    conv = next(c for c in convs if c["wa_jid"] == s)
    cid = conv["id"]
    r = requests.post(f"{API}/conversations/{cid}/takeover", headers=auth, timeout=10)
    assert r.status_code == 200
    r = requests.post(f"{API}/conversations/{cid}/send", headers=auth, json={"text": "TEST hello"}, timeout=15)
    assert r.status_code == 200
    r = requests.post(f"{API}/conversations/{cid}/resume", headers=auth, timeout=15)
    assert r.status_code == 200
    r = requests.get(f"{API}/conversations/{cid}", headers=auth, timeout=10)
    assert r.status_code == 200
    assert r.json()["conversation"]["status"] == "active"


# --- Appointments ---
def test_create_and_update_appointment(auth):
    payload = {
        "patient_name": "TEST_Pasien",
        "patient_phone": "628999888777",
        "service_type": "umum",
        "appointment_date": "2026-06-15",
        "appointment_time": "10:00",
    }
    r = requests.post(f"{API}/appointments", headers=auth, json=payload, timeout=10)
    assert r.status_code == 200
    aid = r.json()["id"]
    r = requests.patch(f"{API}/appointments/{aid}", headers=auth, json={"status": "completed"}, timeout=10)
    assert r.status_code == 200
    lst = requests.get(f"{API}/appointments", headers=auth, timeout=10).json()
    assert any(a["id"] == aid and a["status"] == "completed" for a in lst)


# --- Knowledge base ---
def test_knowledge_add_and_delete(auth):
    payload = {"source": "TEST_bpjs.txt", "content": "Klinik Kimia Farma Sepinggan menerima BPJS Kesehatan untuk layanan umum."}
    r = requests.post(f"{API}/knowledge/text", headers=auth, json=payload, timeout=15)
    assert r.status_code == 200, r.text
    doc_id = r.json()["id"]
    lst = requests.get(f"{API}/knowledge", headers=auth, timeout=10).json()
    assert any(d["id"] == doc_id for d in lst)
    r = requests.delete(f"{API}/knowledge/{doc_id}", headers=auth, timeout=10)
    assert r.status_code == 200


# --- Settings ---
def test_settings_get_update(auth):
    r = requests.get(f"{API}/settings", headers=auth, timeout=10)
    assert r.status_code == 200
    s = r.json()
    original_name = s["clinic"]["name"]
    new_name = original_name + " ✓"
    s["clinic"]["name"] = new_name
    r = requests.put(f"{API}/settings", headers=auth, json=s, timeout=10)
    assert r.status_code == 200
    r = requests.get(f"{API}/settings", headers=auth, timeout=10)
    assert r.json()["clinic"]["name"] == new_name
    # restore
    s["clinic"]["name"] = original_name
    requests.put(f"{API}/settings", headers=auth, json=s, timeout=10)


def test_settings_module_toggle(auth):
    s = requests.get(f"{API}/settings", headers=auth, timeout=10).json()
    modules = s.get("modules", {})
    orig = modules.get("faq", True)
    modules["faq"] = not orig
    s["modules"] = modules
    r = requests.put(f"{API}/settings", headers=auth, json=s, timeout=10)
    assert r.status_code == 200
    s2 = requests.get(f"{API}/settings", headers=auth, timeout=10).json()
    assert s2["modules"]["faq"] == (not orig)
    # restore
    modules["faq"] = orig
    s["modules"] = modules
    requests.put(f"{API}/settings", headers=auth, json=s, timeout=10)
