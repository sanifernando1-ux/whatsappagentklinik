# Test Credentials — Klinik KF Sepinggan WA Agent

## Admin Dashboard (JWT login)
- URL: `/login`
- Username: `admin`
- Password: `admin123`
- Role: admin

## Internal webhook (gateway → backend)
- Endpoint: `POST /api/whatsapp/webhook`
- Header: `x-webhook-token: whk_9c2f7a1e5b8d3046`
- Body: `{"sender":"628xxx@s.whatsapp.net","text":"...","messageType":"text","pushName":"Nama"}`

## Notes
- LLM uses EMERGENT_LLM_KEY (Universal Key) by default; provider/model configurable in Settings.
- Real WhatsApp requires scanning QR / pairing on a real phone (cannot be automated in tests).
