import json
import time
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from dotenv import load_dotenv

from civic.models import KnowledgeBase

try:
    from google import genai as google_genai
except Exception:  # pragma: no cover
    google_genai = None


LANG_NAME = {
    "hi": "Hindi",
    "te": "Telugu",
    "ml": "Malayalam",
    "kn": "Kannada",
    "mr": "Marathi",
    "bn": "Bengali",
}


def _extract_json(text):
    if not text:
        return None
    text = text.strip()
    if text.startswith("[") and text.endswith("]"):
        return text
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return None


class Command(BaseCommand):
    help = "Translate English KnowledgeBase entries into other languages using Gemini."

    def add_arguments(self, parser):
        parser.add_argument(
            "--languages",
            type=str,
            default="hi,ml,te,kn,mr,bn",
            help="Comma-separated language codes (default: hi,ml,te,kn,mr,bn).",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=5,
            help="How many entries per Gemini call (default: 5).",
        )
        parser.add_argument(
            "--sleep",
            type=float,
            default=0.4,
            help="Seconds to sleep between calls (default: 0.4).",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Limit number of English entries processed (0 = no limit).",
        )

    def handle(self, *args, **options):
        if google_genai is None:
            self.stderr.write("google-genai not installed. Run: pip install google-genai")
            return

        base_dir = Path(__file__).resolve().parents[3]
        load_dotenv(base_dir / ".env")

        api_key = (Path(base_dir / ".env").read_text(encoding="utf-8") if (base_dir / ".env").exists() else "")
        api_key = None
        from os import environ

        api_key = environ.get("GOOGLE_API_KEY", "")
        model_name = environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")

        if not api_key:
            self.stderr.write("GOOGLE_API_KEY not found in environment.")
            return

        languages = [l.strip() for l in options["languages"].split(",") if l.strip()]
        batch_size = max(1, int(options["batch_size"]))
        sleep_s = max(0, float(options["sleep"]))
        limit = int(options["limit"])

        client = google_genai.Client(api_key=api_key)

        en_entries = KnowledgeBase.objects.filter(language="en", is_active=True).order_by("id")
        if limit:
            en_entries = en_entries[:limit]

        total = en_entries.count()
        if total == 0:
            self.stdout.write("No English KB entries found.")
            return

        self.stdout.write(f"Translating {total} English entries into: {', '.join(languages)}")

        for lang in languages:
            lang_name = LANG_NAME.get(lang, lang)
            created = 0
            skipped = 0

            batch = []
            for entry in en_entries:
                exists = KnowledgeBase.objects.filter(
                    service=entry.service,
                    language=lang,
                    keywords=entry.keywords,
                    priority=entry.priority,
                    is_active=True,
                ).exists()
                if exists:
                    skipped += 1
                    continue
                batch.append(entry)

                if len(batch) < batch_size:
                    continue

                created += self._translate_batch(client, model_name, batch, lang, lang_name)
                batch = []
                if sleep_s:
                    time.sleep(sleep_s)

            if batch:
                created += self._translate_batch(client, model_name, batch, lang, lang_name)
                if sleep_s:
                    time.sleep(sleep_s)

            self.stdout.write(f"{lang}: created {created}, skipped {skipped}")

    def _translate_batch(self, client, model_name, batch, lang, lang_name):
        payload = []
        for entry in batch:
            payload.append(
                {
                    "source_id": entry.id,
                    "question": entry.question,
                    "answer": entry.answer,
                    "keywords": entry.keywords,
                }
            )

        prompt = (
            f"Translate the following civic Knowledge Base entries to {lang_name} ({lang}). "
            "Return ONLY valid JSON array. Each item must include: "
            "source_id, question, answer, keywords (comma-separated). "
            "Do not add new information. Keep proper nouns and official names as-is. "
            "Keep IDs and URLs unchanged.\n\n"
            f"INPUT JSON:\n{json.dumps(payload, ensure_ascii=False)}"
        )

        resp = client.models.generate_content(model=model_name, contents=prompt)
        raw = getattr(resp, "text", "")
        json_text = _extract_json(raw)
        if not json_text:
            self.stderr.write("Failed to parse JSON for a batch.")
            return 0

        try:
            items = json.loads(json_text)
        except json.JSONDecodeError:
            self.stderr.write("Invalid JSON returned for a batch.")
            return 0

        created = 0
        with transaction.atomic():
            for item in items:
                src_id = item.get("source_id")
                try:
                    src = KnowledgeBase.objects.get(id=src_id)
                except KnowledgeBase.DoesNotExist:
                    continue

                translated_keywords = (item.get("keywords") or "").strip()
                combined_keywords = ", ".join([k for k in [translated_keywords, src.keywords] if k]).strip(", ")

                KnowledgeBase.objects.create(
                    service=src.service,
                    language=lang,
                    question=(item.get("question") or "").strip() or src.question,
                    answer=(item.get("answer") or "").strip() or src.answer,
                    keywords=combined_keywords or src.keywords,
                    priority=src.priority,
                    is_active=src.is_active,
                )
                created += 1

        return created
