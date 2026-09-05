"""Iteration 2 backend tests: KB seed, smart router, workflow config, reminders."""
import os
import time
import uuid
import pytest
import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://8eaa804a-42f2-4374-b7f7-711be45e5d80.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
WEBHOOK_TOKEN = "whk_9c2f7a1e5b8d3046"


@pytest.fixture(scope="module")
def auth():
    r = requests.post(f"{API}/auth/login", json={"username": "admin", "password": "admin123"}, timeout=15)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def _wh(payload):
    return requests.post(f"{API}/whatsapp/webhook",
                         headers={"x-webhook-token": WEBHOOK_TOKEN},
                         json=payload, timeout=45)


# ---- KB seed ----
def test_kb_seeded(auth):
    r = requests.get(f"{API}/knowledge", headers=auth, timeout=10)
    assert r.status_code == 200
    docs = r.json()
    sources = {d["source"] for d in docs}
    expected = {"Informasi BPJS Kesehatan", "Daftar Layanan dan Tarif",
                "SOP Pendaftaran Pasien", "Jam Operasional dan Lokasi"}
    missing = expected - sources
    assert not missing, f"Missing seeded KB docs: {missing}. Got sources: {sources}"


# ---- Smart RAG answer references BPJS ----
def test_smart_rag_bpjs():
    s = f"628{uuid.uuid4().hex[:10]}@s.whatsapp.net"
    r = _wh({"sender": s, "text": "halo", "messageType": "text", "pushName": "Tester"})
    assert r.status_code == 200
    r = _wh({"sender": s, "text": "apakah klinik menerima BPJS?", "messageType": "text"})
    assert r.status_code == 200
    reply = r.json()["replies"][0].lower()
    # Should not be handoff and should reference BPJS
    assert r.json()["handoff"] is False
    assert "bpjs" in reply, f"Reply doesn't mention BPJS: {reply}"
    # Should not be raw services menu
    assert "daftar layanan:" not in reply or "bpjs" in reply


# ---- Smart semantic router: casual booking phrase ----
def test_smart_router_booking():
    s = f"628{uuid.uuid4().hex[:10]}@s.whatsapp.net"
    r = _wh({"sender": s, "text": "halo", "messageType": "text", "pushName": "Tester"})
    assert r.status_code == 200
    r = _wh({"sender": s, "text": "saya pengen ketemu dokter minggu depan bisa ga",
             "messageType": "text"})
    assert r.status_code == 200
    body = r.json()
    reply = body["replies"][0]
    # Should start booking flow -> reply contains booking service options
    assert "Buat Janji Temu" in reply or "jenis layanan" in reply.lower(), \
        f"Not booking flow. reply={reply}"


# ---- Workflow config ----
def test_settings_workflow_shape(auth):
    r = requests.get(f"{API}/settings", headers=auth, timeout=10)
    assert r.status_code == 200
    s = r.json()
    wf = s.get("workflow", {})
    assert isinstance(wf.get("intents"), list)
    assert len(wf["intents"]) >= 6
    assert wf.get("use_llm_router") is True
    assert wf.get("fallback") in ("rag", "handoff")
    rem = s.get("reminders", {})
    assert rem.get("enabled") is True


def test_settings_workflow_update(auth):
    s = requests.get(f"{API}/settings", headers=auth, timeout=10).json()
    orig_fallback = s["workflow"]["fallback"]
    orig_intents = list(s["workflow"]["intents"])
    # Change fallback + add a test intent
    new_intents = orig_intents + [{
        "id": "TEST_intent_iter2", "name": "TEST", "action": "static",
        "menu_key": "", "keywords": ["testkw_iter2"], "examples": [],
        "response": "ok", "enabled": True,
    }]
    s["workflow"]["fallback"] = "handoff"
    s["workflow"]["intents"] = new_intents
    r = requests.put(f"{API}/settings", headers=auth, json=s, timeout=10)
    assert r.status_code == 200
    s2 = requests.get(f"{API}/settings", headers=auth, timeout=10).json()
    assert s2["workflow"]["fallback"] == "handoff"
    assert any(i["id"] == "TEST_intent_iter2" for i in s2["workflow"]["intents"])
    # restore
    s2["workflow"]["fallback"] = orig_fallback
    s2["workflow"]["intents"] = orig_intents
    requests.put(f"{API}/settings", headers=auth, json=s2, timeout=10)
    s3 = requests.get(f"{API}/settings", headers=auth, timeout=10).json()
    assert not any(i["id"] == "TEST_intent_iter2" for i in s3["workflow"]["intents"])


# ---- Reminders endpoint ----
def test_send_reminders_endpoint(auth):
    r = requests.post(f"{API}/appointments/send-reminders", headers=auth, timeout=20)
    assert r.status_code == 200
    body = r.json()
    assert "sent" in body
    assert "total_due" in body
    assert isinstance(body["sent"], int)
    assert isinstance(body["total_due"], int)


# ---- Handoff via keyword (from existing sender, 2nd msg) ----
def test_handoff_via_staf_keyword():
    s = f"628{uuid.uuid4().hex[:10]}@s.whatsapp.net"
    _wh({"sender": s, "text": "halo", "messageType": "text"})
    r = _wh({"sender": s, "text": "saya mau bicara dengan staf", "messageType": "text"})
    assert r.status_code == 200
    assert r.json()["handoff"] is True
