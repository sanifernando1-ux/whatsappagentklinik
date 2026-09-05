from database import db

DEFAULT_SETTINGS = {
    "id": "singleton",
    "clinic": {
        "name": "Klinik Kimia Farma Sepinggan",
        "address": "Jl. Marsma R. Iswahyudi, Sepinggan, Balikpapan, Kalimantan Timur",
        "phone": "(0542) 123456",
        "hours": "Senin–Sabtu 08.00–20.00 WITA, Minggu 08.00–14.00 WITA",
        "description": "Klinik pratama dengan layanan dokter umum, laboratorium, dan farmasi.",
    },
    "ai": {
        "provider": "openai",
        "model": "gpt-4o",
        "api_key": "",
        "system_prompt": "",
    },
    "modules": {"faq": True, "booking": True, "rag": True, "handoff": True},
    "menu": [
        {"key": "1", "label": "Informasi Layanan & Jam Buka", "intent": "layanan"},
        {"key": "2", "label": "Jadwal Dokter", "intent": "jadwal_dokter"},
        {"key": "3", "label": "Buat Janji Temu", "intent": "booking"},
        {"key": "4", "label": "Cek Status Antrian", "intent": "antrian"},
        {"key": "5", "label": "Tanya Seputar Obat & Kesehatan", "intent": "obat_kesehatan"},
        {"key": "6", "label": "Hubungi Staf Klinik", "intent": "staf"},
    ],
    "handoff_keywords": ["staf", "admin", "operator", "manusia", "bicara dengan orang", "cs", "customer service", "keluhan serius"],
    "negative_words": ["marah", "kecewa", "buruk", "jelek", "parah", "komplain", "keluhan",
                        "lambat", "kesal", "kesel", "menyebalkan", "tidak puas", "gagal",
                        "payah", "bohong", "nipu", "lama sekali"],
    "confidence_threshold": 0.08,
    "rag_relevant_threshold": 0.08,
    "services": [
        {"name": "Konsultasi Dokter Umum", "type": "umum", "price": 50000},
        {"name": "Pemeriksaan Darah Lengkap", "type": "lab", "price": 120000},
        {"name": "Cek Gula Darah", "type": "lab", "price": 35000},
        {"name": "Cek Kolesterol", "type": "lab", "price": 45000},
        {"name": "Vaksinasi Influenza", "type": "vaksinasi", "price": 180000},
        {"name": "Layanan Tebus Obat (Farmasi)", "type": "farmasi", "price": 0},
    ],
    "doctors": [
        {"name": "dr. Andi Pratama", "specialty": "Dokter Umum", "schedule": "Senin–Jumat, 08.00–14.00"},
        {"name": "dr. Siti Rahma", "specialty": "Dokter Umum", "schedule": "Senin–Sabtu, 14.00–20.00"},
    ],
    "business_hours": {"start": "08:00", "end": "20:00", "slot_minutes": 60},
}


async def get_settings():
    s = await db.settings.find_one({"id": "singleton"})
    if not s:
        await db.settings.insert_one(dict(DEFAULT_SETTINGS))
        s = dict(DEFAULT_SETTINGS)
    s.pop("_id", None)
    return s


async def seed_settings():
    if not await db.settings.find_one({"id": "singleton"}):
        await db.settings.insert_one(dict(DEFAULT_SETTINGS))
