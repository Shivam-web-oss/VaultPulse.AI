import json
import os
from datetime import datetime, timezone
from urllib.parse import quote, urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from typing import Iterable, Sequence

from app.services.document_service import Document


class ChatProviderUnavailableError(RuntimeError):
    pass


class ChatService:
    provider_name = "unconfigured"

    @staticmethod
    def _temporal_system_instruction(search_enabled: bool) -> str:
        timezone_name = os.getenv("APP_TIMEZONE", "Asia/Kolkata").strip() or "Asia/Kolkata"
        try:
            tz = ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            timezone_name = "UTC"
            tz = timezone.utc
        now = datetime.now(tz)
        temporal_context = (
            f"The current date and time is {now.strftime('%A, %B %d, %Y at %H:%M:%S')} "
            f"({now.isoformat(timespec='seconds')}; timezone {timezone_name}). "
            "Treat this runtime date and time as authoritative. Never claim that it is a different date "
            "based on training data."
        )
        if search_enabled:
            return temporal_context + (
                " Use Google Search grounding for current or historical time-sensitive facts when useful. "
                "Base factual claims on search results, and do not invent rankings, events, releases, or statistics."
            )
        return temporal_context + (
            " This request has no live web search results. For current, recent, or future facts, use only "
            "information provided in the conversation or supplied documents; do not invent rankings, events, "
            "releases, or statistics. Clearly say when such information cannot be verified from the available context."
        )

    @staticmethod
    def _is_gemini_endpoint(base_url: str) -> bool:
        return (urlsplit(base_url).hostname or "").lower() == "generativelanguage.googleapis.com"

    def _generate_grounded_gemini_reply(self, api_key: str, model: str, prompt: str) -> str:
        if os.getenv("AI_LIVE_SEARCH_ENABLED", "true").strip().lower() in {"0", "false", "no", "off"}:
            raise ChatProviderUnavailableError("Live search is disabled by AI_LIVE_SEARCH_ENABLED")

        model_path = quote(model, safe="-._")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_path}:generateContent"
        payload = json.dumps({
            "systemInstruction": {"parts": [{"text": self._temporal_system_instruction(search_enabled=True)}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "tools": [{"google_search": {}}],
        }).encode("utf-8")
        request = Request(url, data=payload, headers={
            "x-goog-api-key": api_key,
            "Content-Type": "application/json",
        }, method="POST")

        try:
            with urlopen(request, timeout=60) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            try:
                provider_error = json.loads(error.read().decode("utf-8"))
                detail = provider_error.get("error", {}).get("message", "")
            except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
                detail = ""
            if not isinstance(detail, str):
                detail = ""
            if error.code == 429:
                detail = "Gemini search grounding quota was exceeded. Check the Google AI API quota and billing settings."
            elif error.code == 403:
                detail = "Google denied the Gemini search request. Check that the API key and project can use Gemini Search grounding."
            elif not detail:
                detail = f"Gemini Search grounding returned HTTP {error.code}."
            raise ChatProviderUnavailableError(detail[:500]) from error
        except (URLError, TimeoutError, json.JSONDecodeError) as error:
            raise ChatProviderUnavailableError("The grounded Gemini request could not be completed") from error

        try:
            candidate = result["candidates"][0]
            parts = candidate["content"]["parts"]
            reply = "".join(part["text"] for part in parts if isinstance(part.get("text"), str)).strip()
        except (KeyError, IndexError, TypeError) as error:
            raise ChatProviderUnavailableError("The AI provider returned an invalid grounded response") from error
        if not reply:
            raise ChatProviderUnavailableError("The AI provider returned an empty grounded response")

        metadata = candidate.get("groundingMetadata") or {}
        sources = []
        seen_urls = set()
        for chunk in metadata.get("groundingChunks") or []:
            web = chunk.get("web", {})
            source_url = web.get("uri")
            title = (web.get("title") or "Source").replace("[", "(").replace("]", ")")
            if isinstance(source_url, str) and source_url.startswith(("https://", "http://")) and source_url not in seen_urls:
                seen_urls.add(source_url)
                sources.append(f"- [{title}]({source_url})")
        if sources:
            reply += "\n\nSources:\n" + "\n".join(sources)
        return reply

    def generate_reply(self, message: str, documents: Sequence[Document] = ()) -> str:
        api_key = os.getenv("AI_PROVIDER_API_KEY", "").strip()
        if not api_key:
            raise ChatProviderUnavailableError("AI_PROVIDER_API_KEY is not configured")

        base_url = os.getenv("AI_PROVIDER_BASE_URL", "https://api.openai.com/v1/chat/completions").strip()
        model = os.getenv("AI_MODEL", "gpt-4o-mini").strip()
        context = "\n\n".join(f"{document.name}: {document.text}" for document in documents if document.text)
        prompt = message if not context else f"User documents:\n{context}\n\nUser question:\n{message}"
        if self._is_gemini_endpoint(base_url):
            return self._generate_grounded_gemini_reply(api_key, model, prompt)

        payload = json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": self._temporal_system_instruction(search_enabled=False)},
                {"role": "user", "content": prompt},
            ],
        }).encode("utf-8")
        request = Request(base_url, data=payload, headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }, method="POST")

        try:
            with urlopen(request, timeout=60) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            if error.code in {401, 403}:
                detail = f"The AI provider rejected the API key or denied access (HTTP {error.code}). Verify the key and provider account."
            elif error.code == 429:
                detail = "The AI provider quota or rate limit was reached (HTTP 429). Check the provider plan and usage limits."
            elif error.code in {400, 404}:
                try:
                    provider_error = json.loads(error.read().decode("utf-8"))
                    detail = provider_error.get("message") or provider_error.get("error", {}).get("message")
                except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
                    detail = None
                if not isinstance(detail, str) or not detail:
                    detail = f"The AI provider rejected the model or endpoint (HTTP {error.code}). Check AI_MODEL and AI_PROVIDER_BASE_URL."
            else:
                detail = f"The AI provider returned HTTP {error.code}. Check provider status and configuration."
            raise ChatProviderUnavailableError(detail[:500]) from error
        except (URLError, TimeoutError, json.JSONDecodeError) as error:
            raise ChatProviderUnavailableError("The configured AI provider could not be reached") from error

        try:
            reply = result["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise ChatProviderUnavailableError("The AI provider returned an invalid response") from error
        if not isinstance(reply, str) or not reply.strip():
            raise ChatProviderUnavailableError("The AI provider returned an empty response")
        return reply.strip()

    def stream_reply(self, message: str, documents: Sequence[Document] = ()) -> Iterable[str]:
        response = self.generate_reply(message, documents)
        for line in response.splitlines(keepends=True):
            yield line


chat_service = ChatService()
