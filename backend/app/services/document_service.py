import io
import zipfile
from dataclasses import dataclass
from html import unescape
from typing import Dict, List
from xml.etree import ElementTree

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover - dependency is installed in production
    PdfReader = None


@dataclass
class Document:
    id: str
    owner_id: str
    name: str
    content_type: str
    size: int
    text: str


class DocumentService:
    def __init__(self) -> None:
        self._documents: Dict[str, List[Document]] = {}

    def add(self, document: Document) -> Document:
        self._documents.setdefault(document.owner_id, []).append(document)
        return document

    def search(self, owner_id: str, query: str) -> List[Document]:
        documents = self._documents.get(owner_id, [])
        terms = [term.lower() for term in query.split() if len(term) > 2]
        if not terms:
            return documents
        return [document for document in documents if any(term in document.text.lower() for term in terms)]

    @staticmethod
    def extract_text(filename: str, content_type: str, content: bytes) -> str:
        extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if extension in {"txt", "csv"} or content_type.startswith("text/"):
            return content.decode("utf-8", errors="replace")
        if extension == "pdf" and PdfReader is not None:
            reader = PdfReader(io.BytesIO(content))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        if extension == "docx":
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                xml = archive.read("word/document.xml")
            root = ElementTree.fromstring(xml)
            text = " ".join(node.text or "" for node in root.iter() if node.tag.endswith("}t"))
            return unescape(text)
        return ""

document_service = DocumentService()
