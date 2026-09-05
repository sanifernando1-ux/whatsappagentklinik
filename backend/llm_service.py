import os
from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage

load_dotenv()

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")

# Known providers use the Emergent Universal Key by default; a custom key overrides it.
KNOWN_PROVIDERS = {"openai", "anthropic", "gemini"}


async def generate_reply(system_message: str, user_text: str, session_id: str, settings: dict) -> str:
    ai = (settings or {}).get("ai", {})
    provider = ai.get("provider", "openai")
    model = ai.get("model", "gpt-4o")
    custom_key = ai.get("api_key")

    if provider in KNOWN_PROVIDERS and not custom_key:
        key = EMERGENT_LLM_KEY
    else:
        key = custom_key or EMERGENT_LLM_KEY

    chat = LlmChat(
        api_key=key,
        session_id=session_id,
        system_message=system_message,
    ).with_model(provider, model)

    resp = await chat.send_message(UserMessage(text=user_text))
    return (resp or "").strip()


async def classify_intent(text: str, settings: dict) -> str:
    """Lightweight LLM intent classifier used by the workflow router."""
    sys = (
        "Anda adalah pengklasifikasi intent untuk chatbot klinik. "
        "Kembalikan SATU kata dari daftar berikut sesuai maksud pesan pasien: "
        "layanan, jadwal_dokter, booking, antrian, obat_kesehatan, staf, lainnya. "
        "Jawab HANYA satu kata, tanpa penjelasan."
    )
    try:
        out = await generate_reply(sys, f"Pesan: {text}", f"intent-{hash(text) % 100000}", settings)
        word = out.split()[0].lower().strip(".,:")
        valid = {"layanan", "jadwal_dokter", "booking", "antrian", "obat_kesehatan", "staf", "lainnya"}
        return word if word in valid else "lainnya"
    except Exception:
        return "lainnya"
