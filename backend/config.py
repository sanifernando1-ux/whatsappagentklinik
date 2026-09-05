from database import db
from rag import chunk_text
import uuid

DEFAULT_INTENTS = [
    {"id": "layanan", "name": "Informasi Layanan & Jam Buka", "action": "services", "menu_key": "1",
     "keywords": ["jam buka", "jam operasional", "jam berapa", "alamat", "lokasi", "dimana klinik", "harga", "biaya", "tarif", "layanan apa"],
     "examples": ["klinik buka jam berapa?", "berapa biaya konsultasi?", "alamat kliniknya dimana?"],
     "response": "", "enabled": True},
    {"id": "jadwal_dokter", "name": "Jadwal Dokter", "action": "doctors", "menu_key": "2",
     "keywords": ["jadwal dokter", "dokter siapa", "jadwal praktik", "dokter praktek", "praktik dokter"],
     "examples": ["dokter praktek jam berapa?", "siapa saja dokternya?"],
     "response": "", "enabled": True},
    {"id": "booking", "name": "Buat Janji Temu", "action": "booking", "menu_key": "3",
     "keywords": ["janji", "booking", "buat janji", "daftar berobat", "jadwalkan", "appointment", "reservasi", "mau berobat"],
     "examples": ["saya mau buat janji", "bisa daftar untuk besok?"],
     "response": "", "enabled": True},
    {"id": "antrian", "name": "Cek Status Antrian", "action": "queue", "menu_key": "4",
     "keywords": ["antrian", "antre", "ngantri", "nomor antrian", "ramai"],
     "examples": ["antriannya panjang tidak?", "berapa nomor antrian sekarang?"],
     "response": "", "enabled": True},
    {"id": "obat_kesehatan", "name": "Tanya Seputar Obat & Kesehatan", "action": "rag", "menu_key": "5",
     "keywords": ["obat", "gejala", "sakit", "keluhan", "kesehatan", "bpjs", "resep"],
     "examples": ["apakah menerima BPJS?", "obat untuk demam apa?"],
     "response": "", "enabled": True},
    {"id": "staf", "name": "Hubungi Staf Klinik", "action": "handoff", "menu_key": "6",
     "keywords": ["staf", "admin", "operator", "manusia", "bicara dengan orang", "cs", "customer service"],
     "examples": ["saya mau bicara dengan orang", "hubungkan ke staf"],
     "response": "", "enabled": True},
]

DEFAULT_SETTINGS = {
    "id": "singleton",
    "clinic": {
        "name": "Klinik Kimia Farma Sepinggan",
        "address": "Jl. Marsma R. Iswahyudi, Sepinggan, Balikpapan, Kalimantan Timur",
        "phone": "(0542) 123456",
        "hours": "Senin–Sabtu 08.00–20.00 WITA, Minggu 08.00–14.00 WITA",
        "description": "Klinik pratama dengan layanan dokter umum, laboratorium, dan farmasi.",
    },
    "ai": {"provider": "openai", "model": "gpt-4o", "api_key": "", "system_prompt": ""},
    "modules": {"faq": True, "booking": True, "rag": True, "handoff": True},
    "workflow": {
        "intents": DEFAULT_INTENTS,
        "use_llm_router": True,
        "fallback": "rag",
        "welcome_extra": "",
    },
    "handoff_keywords": ["staf", "admin", "operator", "manusia", "bicara dengan orang", "cs", "customer service", "keluhan serius"],
    "negative_words": ["marah", "kecewa", "buruk", "jelek", "parah", "komplain", "keluhan",
                        "lambat", "kesal", "kesel", "menyebalkan", "tidak puas", "gagal",
                        "payah", "bohong", "nipu", "lama sekali"],
    "confidence_threshold": 0.08,
    "rag_relevant_threshold": 0.08,
    "reminders": {"enabled": True, "hours_before": 24},
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
    # backfill new keys for older docs
    changed = False
    for k, v in DEFAULT_SETTINGS.items():
        if k not in s:
            s[k] = v
            changed = True
    if changed:
        await db.settings.update_one({"id": "singleton"}, {"$set": s})
    return s


async def seed_settings():
    if not await db.settings.find_one({"id": "singleton"}):
        await db.settings.insert_one(dict(DEFAULT_SETTINGS))


SEED_KB = [
    ("Informasi BPJS Kesehatan", """Klinik Kimia Farma Sepinggan melayani peserta BPJS Kesehatan untuk layanan tertentu.
Syarat menggunakan BPJS: (1) Kartu BPJS/KIS dalam keadaan aktif, (2) membawa KTP/identitas diri, (3) untuk layanan rujukan mengikuti prosedur FKTP.
Peserta yang menjadikan klinik ini sebagai Fasilitas Kesehatan Tingkat Pertama (FKTP) dapat berobat tanpa biaya sesuai ketentuan BPJS.
Untuk layanan di luar tanggungan BPJS (misalnya pemeriksaan laboratorium tertentu atau vaksinasi mandiri) dikenakan biaya sesuai daftar tarif klinik.
Silakan tanyakan kepada petugas pendaftaran untuk memastikan layanan yang Anda butuhkan ditanggung BPJS."""),
    ("Daftar Layanan dan Tarif", """Daftar layanan Klinik Kimia Farma Sepinggan beserta tarif (pasien umum/non-BPJS):
- Konsultasi Dokter Umum: Rp50.000
- Pemeriksaan Darah Lengkap: Rp120.000
- Cek Gula Darah: Rp35.000
- Cek Kolesterol: Rp45.000
- Vaksinasi Influenza: Rp180.000
- Layanan Tebus Obat (Farmasi): sesuai harga obat
Tarif dapat berubah sewaktu-waktu. Untuk paket pemeriksaan (medical check up) silakan hubungi staf klinik."""),
    ("SOP Pendaftaran Pasien", """Prosedur pendaftaran pasien di Klinik Kimia Farma Sepinggan:
1. Pasien datang dan mengambil nomor antrian di meja pendaftaran, atau membuat janji temu terlebih dahulu via WhatsApp.
2. Pasien menunjukkan KTP dan kartu BPJS (bila menggunakan BPJS).
3. Petugas mendata keluhan awal dan mengarahkan ke poli/dokter yang sesuai.
4. Pasien menunggu dipanggil sesuai nomor antrian.
5. Setelah konsultasi, pasien menuju farmasi untuk mengambil obat (bila ada resep) dan menyelesaikan administrasi.
Pasien dengan janji temu online mendapat prioritas antrian sesuai jadwal yang dipilih."""),
    ("Jam Operasional dan Lokasi", """Klinik Kimia Farma Sepinggan berlokasi di Jl. Marsma R. Iswahyudi, Sepinggan, Balikpapan, Kalimantan Timur.
Jam operasional: Senin–Sabtu pukul 08.00–20.00 WITA, Minggu pukul 08.00–14.00 WITA.
Nomor telepon: (0542) 123456.
Tersedia area parkir, ruang tunggu ber-AC, apotek, dan laboratorium di lokasi yang sama."""),
]


async def seed_knowledge():
    if await db.knowledge_docs.count_documents({"seeded": True}) > 0:
        return
    for source, text in SEED_KB:
        chunks = chunk_text(text)
        doc_id = str(uuid.uuid4())
        await db.knowledge_docs.insert_one({
            "id": doc_id, "source": source, "chunk_count": len(chunks),
            "chars": len(text), "seeded": True,
            "created_at": "2026-06-05T00:00:00+00:00"})
        if chunks:
            await db.knowledge_chunks.insert_many([
                {"id": str(uuid.uuid4()), "doc_id": doc_id, "source": source, "text": c}
                for c in chunks])
