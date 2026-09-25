from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.dependencies.auth import get_current_user
from app.schemas.auth import AuthUser
from app.services.document_service import Document, document_service
router = APIRouter(prefix="/upload", tags=["upload"], dependencies=[Depends(get_current_user)])
ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "csv", "png", "jpg", "jpeg"}
MAX_FILE_SIZE = 10 * 1024 * 1024


@router.post("")
def upload_file(file: UploadFile = File(...), current_user: AuthUser = Depends(get_current_user)):
    extension = Path(file.filename or "").suffix.lower().lstrip(".")
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Unsupported file type")

    content = file.file.read(MAX_FILE_SIZE + 1)
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File is larger than 10 MB")

    document_id = str(uuid4())
    document_service.add(Document(
        id=document_id,
        owner_id=current_user.id,
        name=file.filename or "uploaded-file",
        content_type=file.content_type or "application/octet-stream",
        size=len(content),
        text=document_service.extract_text(file.filename or "", file.content_type or "", content),
    ))

    return {
        "id": document_id,
        "name": file.filename,
        "size": len(content),
        "type": file.content_type or "application/octet-stream",
        "status": "uploaded",
        "content_indexed": True,
    }
