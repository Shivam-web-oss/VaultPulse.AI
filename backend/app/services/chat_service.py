import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from typing import Iterable, Sequence

from app.services.document_service import Document


class ChatProviderUnavailableError(RuntimeError):
    pass


class ChatService:
    provider_name = "unconfigured"

    def generate_reply(self, message: str, documents: Sequence[Document] = ()) -> str:
        api_key = os.getenv("AI_PROVIDER_API_KEY", "").strip()
        if not api_key:
            raise ChatProviderUnavailableError("AI_PROVIDER_API_KEY is not configured")

        base_url = os.getenv("AI_PROVIDER_BASE_URL", "https://api.openai.com/v1/chat/completions").strip()
        model = os.getenv("AI_MODEL", "gpt-4o-mini").strip()
        context = "\n\n".join(f"{document.name}: {document.text}" for document in documents if document.text)
        prompt = message if not context else f"User documents:\n{context}\n\nUser question:\n{message}"
        payload = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        }).encode("utf-8")
        request = Request(base_url, data=payload, headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }, method="POST")

        try:
            with urlopen(request, timeout=60) as response:
                result = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
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
