import os
from dotenv import load_dotenv
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
import google.generativeai as genai

load_dotenv()

# All provider credentials come from settings.ai (persisted in MongoDB via the
# dashboard) — nothing is read from environment variables here. Once an admin
# saves a provider/model/api_key/base_url in Settings > AI, it stays in effect
# until they change or clear it.


async def _call_openai_compatible(system_message, user_text, model, api_key, base_url):
    client = AsyncOpenAI(api_key=api_key, base_url=base_url or None)
    resp = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_text},
        ],
    )
    return resp.choices[0].message.content or ""


async def _call_anthropic(system_message, user_text, model, api_key, base_url):
    client = AsyncAnthropic(api_key=api_key, base_url=base_url or None)
    resp = await client.messages.create(
        model=model,
        max_tokens=1024,
        system=system_message,
        messages=[{"role": "user", "content": user_text}],
    )
    parts = [b.text for b in resp.content if getattr(b, "type", "") == "text"]
    return "".join(parts)


async def _call_gemini(system_message, user_text, model, api_key):
    genai.configure(api_key=api_key)
    gm = genai.GenerativeModel(model_name=model, system_instruction=system_message)
    resp = await gm.generate_content_async(user_text)
    return (resp.text or "") if resp else ""


async def generate_reply(system_message: str, user_text: str, session_id: str, settings: dict) -> str:
    ai = (settings or {}).get("ai", {})
    provider = ai.get("provider", "openai")
    model = ai.get("model", "gpt-4o")
    api_key = ai.get("api_key") or ""
    base_url = ai.get("base_url") or ""

    if not api_key:
        raise RuntimeError("Belum ada API key AI. Isi provider/model/API key di Settings > AI & Model.")

    if provider == "anthropic":
        return (await _call_anthropic(system_message, user_text, model, api_key, base_url)).strip()
    if provider == "gemini":
        return (await _call_gemini(system_message, user_text, model, api_key)).strip()
    # "openai" and "custom" both speak the OpenAI-compatible chat completions
    # API; "custom" just requires a base_url pointing at the compatible
    # endpoint (self-hosted model, proxy, OpenRouter, vLLM, etc.).
    return (await _call_openai_compatible(system_message, user_text, model, api_key, base_url)).strip()


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
