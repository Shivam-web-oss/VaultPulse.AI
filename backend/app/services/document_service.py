import io
import zipfile
from dataclasses import dataclass
from html import unescape
from typing import List
from app.db import connection
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
    def add(self, document: Document) -> Document:
        with connection() as conn:
            conn.execute(
                "insert into documents (id, owner_id, name, content_type, size, text_content) values (%s, %s, %s, %s, %s, %s)",
                (document.id, document.owner_id, document.name, document.content_type, document.size, document.text),
            )
            conn.commit()
        return document

    def search(self, owner_id: str, query: str) -> List[Document]:
        terms = [term.lower() for term in query.split() if len(term) > 2]
        with connection() as conn:
            if terms:
                rows = conn.execute(
                    "select id, owner_id, name, content_type, size, text_content from documents where owner_id = %s and text_content ilike any(%s)",
                    (owner_id, [f"%{term}%" for term in terms]),
                ).fetchall()
            else:
                rows = conn.execute("select id, owner_id, name, content_type, size, text_content from documents where owner_id = %s", (owner_id,)).fetchall()
        return [Document(id=str(row["id"]), owner_id=str(row["owner_id"]), name=row["name"], content_type=row["content_type"], size=row["size"], text=row["text_content"]) for row in rows]

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
