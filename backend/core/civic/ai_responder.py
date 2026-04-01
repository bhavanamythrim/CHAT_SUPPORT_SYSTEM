import os
from typing import Dict, List, Tuple

from langdetect import LangDetectException, detect
from rapidfuzz import fuzz

try:
    import anthropic
except Exception:  # pragma: no cover
    anthropic = None

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None

try:
    from google import genai as google_genai
except Exception:  # pragma: no cover
    google_genai = None


ANTHROPIC_MODEL = "claude-3-haiku-20240307"
OPENAI_MODEL = "gpt-4o-mini"
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
MAX_TOKENS = 450
TOP_K_ENTRIES = 5
FUZZY_THRESHOLD = 45


SUPPORTED_LANGS = {"en", "ta", "hi", "te", "ml", "kn", "mr", "bn"}


def detect_language(text: str) -> str:
    try:
        lang = detect(text or "")
        return lang if lang in SUPPORTED_LANGS else "en"
    except LangDetectException:
        return "en"


def get_relevant_kb_entries(user_message: str, language: str = "en", top_k: int = TOP_K_ENTRIES) -> List[Tuple[int, Dict[str, str]]]:
    from .models import KnowledgeBase

    entries = KnowledgeBase.objects.filter(language=language, is_active=True).select_related("service")
    if not entries.exists():
        entries = KnowledgeBase.objects.filter(language="en", is_active=True).select_related("service")
    if not entries.exists():
        entries = KnowledgeBase.objects.filter(is_active=True).select_related("service")

    scored: List[Tuple[int, Dict[str, str]]] = []
    user_lower = (user_message or "").lower().strip()

    for entry in entries:
        question = (entry.question or "").strip()
        answer = (entry.answer or "").strip()
        keywords = (entry.keywords or "").strip()
        service_name = entry.service.name if entry.service else ""
        if not question:
            continue

        score = max(
            fuzz.token_set_ratio(user_lower, question.lower()),
            fuzz.partial_ratio(user_lower, question.lower()),
            fuzz.WRatio(user_lower, question.lower()),
            fuzz.token_set_ratio(user_lower, keywords.lower()) if keywords else 0,
            fuzz.partial_ratio(user_lower, service_name.lower()) if service_name else 0,
        )

        if score >= FUZZY_THRESHOLD:
            scored.append(
                (
                    int(score),
                    {
                        "question": question,
                        "answer": answer,
                        "keywords": keywords,
                        "service": service_name,
                        "language": entry.language,
                    },
                )
            )

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top_k]


def build_system_prompt(language: str) -> str:
    if language == "ta":
        return (
            "நீங்கள் Smart Civic HelpDesk உதவியாளர். "
            "தமிழில் தெளிவாகவும் துல்லியமாகவும் பதிலளிக்கவும். "
            "முக்கிய தகவல்களை **bold** ஆகவும், நடைமுறை விஷயங்களை 1.2.3. படிகளாகவும் கொடுக்கவும்."
        )
    if language == "hi":
        return (
            "आप Smart Civic HelpDesk सहायक हैं। "
            "हिंदी में स्पष्ट और सटीक उत्तर दें। "
            "महत्वपूर्ण जानकारी को **bold** करें और चरण 1,2,3 में बताएं।"
        )
    if language == "te":
        return (
            "మీరు Smart Civic HelpDesk సహాయకుడు. "
            "తెలుగులో స్పష్టంగా మరియు ఖచ్చితంగా సమాధానం ఇవ్వండి. "
            "**bold** ముఖ్య సమాచారం, 1,2,3 దశలు ఉపయోగించండి."
        )
    if language == "ml":
        return (
            "നിങ്ങൾ Smart Civic HelpDesk സഹായകനാണ്. "
            "മലയാളത്തിൽ വ്യക്തവും കൃത്യവുമായ മറുപടി നൽകുക. "
            "**bold** ആയി പ്രധാന വിവരങ്ങൾയും 1,2,3 ഘട്ടങ്ങളായി നൽകുക."
        )
    if language == "kn":
        return (
            "ನೀವು Smart Civic HelpDesk ಸಹಾಯಕ. "
            "ಕನ್ನಡದಲ್ಲಿ ಸ್ಪಷ್ಟವಾಗಿ ಹಾಗೂ ನಿಖರವಾಗಿ ಉತ್ತರಿಸಿ. "
            "ಮುಖ್ಯ ಮಾಹಿತಿಯನ್ನು **bold** ಮಾಡಿ, 1,2,3 ಹಂತಗಳಲ್ಲಿ ಕೊಡಿ."
        )
    if language == "mr":
        return (
            "आपण Smart Civic HelpDesk सहाय्यक आहात. "
            "मराठीत स्पष्ट आणि अचूक उत्तर द्या. "
            "महत्त्वाची माहिती **bold** करा आणि 1,2,3 टप्प्यांत द्या."
        )
    if language == "bn":
        return (
            "আপনি Smart Civic HelpDesk সহকারী। "
            "বাংলায় স্পষ্ট ও সঠিক উত্তর দিন। "
            "**bold** করে গুরুত্বপূর্ণ তথ্য দিন এবং ১,২,৩ ধাপে বুঝিয়ে দিন।"
        )
    return (
        "You are Smart Civic HelpDesk assistant for local public services. "
        "Answer accurately from provided KB context. "
        "Use clear markdown with short sections and numbered steps when applicable. "
        "Avoid guessing; if uncertain, say so and suggest nearest office/helpdesk."
    )


def _fallback_response(relevant_entries: List[Tuple[int, Dict[str, str]]], language: str) -> str:
    if not relevant_entries:
        if language == "ta":
            return "மன்னிக்கவும், இந்த கேள்விக்கு தெளிவான தகவல் கிடைக்கவில்லை. அருகிலுள்ள அரசு அலுவலகத்தை அணுகவும்."
        return "Sorry, I could not find a reliable answer for this query. Please contact the nearest government office/helpdesk."

    score, best = relevant_entries[0]
    q = best.get("question", "")
    a = best.get("answer", "")
    return f"**{q}**\n\n{a}\n\n_Confidence: {score}%_"


def _prepare_context(relevant_entries: List[Tuple[int, Dict[str, str]]], language: str) -> str:
    if not relevant_entries:
        return "No direct KB match found. Use general civic guidance and be explicit about uncertainty."

    lines = []
    for i, (score, item) in enumerate(relevant_entries, 1):
        lines.append(
            f"Entry {i} (relevance {score}%):\n"
            f"Service: {item.get('service') or 'General'}\n"
            f"Q: {item.get('question') or ''}\n"
            f"A: {item.get('answer') or ''}"
        )
    header = "Use these KB entries as primary context:" if language == "en" else "இந்த KB தகவல்களை முதன்மையாக பயன்படுத்தவும்:"
    return header + "\n\n" + "\n\n".join(lines)


def _try_openai(messages: List[Dict[str, str]], language: str, openai_key: str):
    if not openai_key or OpenAI is None:
        return None
    client = OpenAI(api_key=openai_key)
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "system", "content": build_system_prompt(language)}] + messages,
        max_tokens=MAX_TOKENS,
        temperature=0.2,
    )
    if not resp or not resp.choices:
        return None
    return (resp.choices[0].message.content or "").strip()


def _try_anthropic(messages: List[Dict[str, str]], language: str, anthropic_key: str):
    if not anthropic_key or anthropic is None:
        return None
    client = anthropic.Anthropic(api_key=anthropic_key)
    resp = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=MAX_TOKENS,
        system=build_system_prompt(language),
        messages=messages,
    )
    if not resp or not resp.content:
        return None
    return (resp.content[0].text or "").strip()


def _messages_to_text(messages: List[Dict[str, str]], language: str) -> str:
    lines = [build_system_prompt(language), ""]
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        lines.append(f"{role.upper()}: {content}")
    return "\n".join(lines).strip()


def _try_gemini(messages: List[Dict[str, str]], language: str, google_key: str):
    if not google_key or google_genai is None:
        return None
    client = google_genai.Client(api_key=google_key)
    prompt = _messages_to_text(messages, language)
    resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    text = getattr(resp, "text", None)
    if text:
        return text.strip()
    return None


def generate_response(user_message: str, session_history: List[Dict[str, str]] = None, user_language: str = None) -> Dict[str, object]:
    language = user_language or detect_language(user_message)
    relevant_entries = get_relevant_kb_entries(user_message, language=language)
    kb_context = _prepare_context(relevant_entries, language)

    if session_history is None:
        session_history = []

    messages = session_history[-6:] + [
        {
            "role": "user",
            "content": f"{kb_context}\n\nCitizen question: {user_message}",
        }
    ]

    provider = (os.environ.get("AI_PROVIDER", "") or "").strip().lower()
    anthropic_key = (os.environ.get("ANTHROPIC_API_KEY", "") or "").strip()
    openai_key = (os.environ.get("OPENAI_API_KEY", "") or "").strip()
    google_key = (os.environ.get("GOOGLE_API_KEY", "") or "").strip()

    provider_order = []
    if provider in {"openai", "anthropic", "gemini"}:
        provider_order.append(provider)
    for p in ("gemini", "openai", "anthropic"):
        if p not in provider_order:
            provider_order.append(p)

    for p in provider_order:
        try:
            text = None
            if p == "openai":
                text = _try_openai(messages, language, openai_key)
            elif p == "anthropic":
                text = _try_anthropic(messages, language, anthropic_key)
            elif p == "gemini":
                text = _try_gemini(messages, language, google_key)

            if text:
                return {
                    "response": text,
                    "language": language,
                    "matched_entries": len(relevant_entries),
                    "confidence": relevant_entries[0][0] if relevant_entries else 0,
                    "error": None,
                    "provider": p,
                }
        except Exception:
            continue

    return {
        "response": _fallback_response(relevant_entries, language),
        "language": language,
        "matched_entries": len(relevant_entries),
        "confidence": relevant_entries[0][0] if relevant_entries else 0,
        "error": "missing_api_key_or_sdk",
        "provider": "fallback",
    }
