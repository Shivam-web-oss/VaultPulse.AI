from typing import Iterable, Sequence

from app.services.document_service import Document


class ChatService:
    provider_name = "mock"

    def generate_reply(self, message: str, documents: Sequence[Document] = ()) -> str:
        document_context = "\n\n".join(
            f"### {document.name}\n{document.text}" for document in documents if document.text
        )
        source_section = f"\n\n## Uploaded content\n{document_context}" if document_context else ""
        return (
            "## Mock assistant response\n\n"
            f"You asked: **{message.strip()}**\n\n"
            "VaultPulse.AI searched the uploaded content available to your account."
            f"{source_section}\n\n"
            "The provider layer is replaceable without changing the frontend API."
        )

    def stream_reply(self, message: str, documents: Sequence[Document] = ()) -> Iterable[str]:
        response = self.generate_reply(message, documents)
        for line in response.splitlines(keepends=True):
            yield line


chat_service = ChatService()
