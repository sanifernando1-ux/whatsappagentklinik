"""Iteration 3 backend tests: conditional flow, booking_link, broadcast."""
import os
import uuid
import pytest
import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "").rstrip("/")
API = f"{BASE_URL}/api"
WEBHOOK_TOKEN = "whk_9c2f7a1e5b8d3046"


@pytest.fixture(scope="module")
def auth():
    r = requests.post(f"{API}/auth/login", json={"username": "admin", "password": "admin123"}, timeout=15)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="module")
def base_settings(auth):
    """Snapshot settings before mutations, restore after module."""
    r = requests.get(f"{API}/settings", headers=auth, timeout=10)
    assert r.status_code == 200
    snap = r.json()
    yield snap
    # restore defaults
    from copy import deepcopy
    restore = deepcopy(snap)
    # reset to DEFAULT baseline (6 default intents, booking_url '', booking action 'booking')
    restore["clinic"]["booking_url"] = ""
    intents = restore["workflow"]["intents"]
    # drop TEST intents
    intents = [i for i in intents if not i["id"].startswith("TEST_")]
    for i in intents:
        if i["id"] == "booking":
            i["action"] = "booking"
    restore["workflow"]["intents"] = intents
    requests.put(f"{API}/settings", headers=auth, json=restore, timeout=10)


def _wh(payload):
    return requests.post(f"{API}/whatsapp/webhook",
                         headers={"x-webhook-token": WEBHOOK_TOKEN},
                         json=payload, timeout=45)


# ---------- Conditional multi-level flow ----------
def test_conditional_flow_multilevel(auth, base_settings):
    s = requests.get(f"{API}/settings", headers=auth, timeout=10).json()
    intents = [i for i in s["workflow"]["intents"] if not i["id"].startswith("TEST_")]
    # Add a flow intent
    flow_intent = {
        "id": "TEST_konsultasi_flow",
        "name": "Konsultasi Bertingkat",
        "action": "flow",
        "menu_key": "7",
        "keywords": ["konsultasi"],
        "examples": [],
        "response": "",
        "enabled": True,
        "steps": [
            {"id": "start", "message": "Pilih poli:\n1. Umum\n2. Gigi",
             "options": [
                 {"keywords": ["1", "umum"], "action": "message", "response": "Baik poli umum."},
                 {"keywords": ["2", "gigi"], "action": "next", "next_step": "gigi"},
             ]},
            {"id": "gigi", "message": "Darurat?\n1 Ya 2 Tidak",
             "options": [
                 {"keywords": ["1", "ya"], "action": "handoff", "response": "Menghubungkan staf."},
                 {"keywords": ["2", "tidak"], "action": "booking_link", "response": "Silakan booking di link:"},
             ]},
        ],
    }
    s["workflow"]["intents"] = intents + [flow_intent]
    s["clinic"]["booking_url"] = "https://booking.example.id"
    r = requests.put(f"{API}/settings", headers=auth, json=s, timeout=10)
    assert r.status_code == 200

    sender = f"628{uuid.uuid4().hex[:10]}@s.whatsapp.net"
    _wh({"sender": sender, "text": "halo", "messageType": "text"})
    # Trigger flow
    r = _wh({"sender": sender, "text": "saya mau konsultasi", "messageType": "text"})
    assert r.status_code == 200
    reply = r.json()["replies"][0]
    assert "Pilih poli" in reply, f"expected start step message, got: {reply}"
    # go to 'gigi'
    r = _wh({"sender": sender, "text": "2", "messageType": "text"})
    assert r.status_code == 200
    reply = r.json()["replies"][0]
    assert "Darurat" in reply, f"expected gigi step message, got: {reply}"
    # pick '1' -> handoff
    r = _wh({"sender": sender, "text": "1", "messageType": "text"})
    assert r.status_code == 200
    body = r.json()
    assert body["handoff"] is True
    assert "Menghubungkan staf" in body["replies"][0]


def test_conditional_flow_terminal_bookinglink(auth, base_settings):
    """Second sender: gigi -> 2 -> booking_link terminal."""
    # settings already set from previous test (fixture is module scope; but tests are independent order-wise)
    s = requests.get(f"{API}/settings", headers=auth, timeout=10).json()
    # Ensure the TEST intent still exists (idempotent add)
    if not any(i["id"] == "TEST_konsultasi_flow" for i in s["workflow"]["intents"]):
        pytest.skip("depends on previous test setup")

    sender = f"628{uuid.uuid4().hex[:10]}@s.whatsapp.net"
    _wh({"sender": sender, "text": "halo", "messageType": "text"})
    _wh({"sender": sender, "text": "saya mau konsultasi", "messageType": "text"})
    _wh({"sender": sender, "text": "2", "messageType": "text"})  # gigi step
    r = _wh({"sender": sender, "text": "2", "messageType": "text"})  # tidak -> booking_link
    assert r.status_code == 200
    reply = r.json()["replies"][0]
    assert "booking.example.id" in reply, f"expected booking link, got: {reply}"


# ---------- booking_link on top-level booking intent ----------
def test_booking_link_action(auth, base_settings):
    s = requests.get(f"{API}/settings", headers=auth, timeout=10).json()
    s["clinic"]["booking_url"] = "https://booking.example.id"
    for i in s["workflow"]["intents"]:
        if i["id"] == "booking":
            i["action"] = "booking_link"
    r = requests.put(f"{API}/settings", headers=auth, json=s, timeout=10)
    assert r.status_code == 200

    sender = f"628{uuid.uuid4().hex[:10]}@s.whatsapp.net"
    _wh({"sender": sender, "text": "halo", "messageType": "text"})
    r = _wh({"sender": sender, "text": "mau buat janji", "messageType": "text"})
    assert r.status_code == 200
    reply = r.json()["replies"][0]
    assert "booking.example.id" in reply
    # Should NOT be internal service picker
    assert "Konsultasi Umum" not in reply or "booking.example.id" in reply
    assert "jenis layanan" not in reply.lower()


# ---------- Broadcast ----------
def test_broadcast_audience(auth):
    r = requests.get(f"{API}/broadcast/audience?target=all", headers=auth, timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert "count" in body
    assert isinstance(body["count"], int)


def test_broadcast_send_and_history(auth):
    payload = {"message": "TEST_broadcast promo iter3", "target": "all"}
    r = requests.post(f"{API}/broadcast", headers=auth, json=payload, timeout=60)
    assert r.status_code == 200, r.text
    body = r.json()
    for k in ["id", "total", "sent", "failed"]:
        assert k in body
    assert isinstance(body["total"], int)
    assert isinstance(body["sent"], int)
    assert isinstance(body["failed"], int)
    # WA gateway offline: sent=0 expected
    assert body["sent"] == 0

    # History includes it
    r = requests.get(f"{API}/broadcast", headers=auth, timeout=10)
    assert r.status_code == 200
    hist = r.json()
    assert isinstance(hist, list)
    assert any(h.get("id") == body["id"] for h in hist)
