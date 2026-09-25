from fastapi import APIRouter, Depends, HTTPException

from app.dependencies.auth import get_current_user
from app.schemas.auth import AuthUser
from app.schemas.conversation import ConversationCreateRequest, ConversationDetailOut, ConversationOut, ConversationUpdateRequest
from app.services.conversation_service import conversation_service

router = APIRouter(prefix="/conversations", tags=["conversations"], dependencies=[Depends(get_current_user)])


@router.post("", response_model=ConversationDetailOut)
def create_conversation(payload: ConversationCreateRequest, current_user: AuthUser = Depends(get_current_user)):
    return conversation_service.create(current_user.id, payload.title or "New conversation")


@router.get("", response_model=list[ConversationOut])
def list_conversations(current_user: AuthUser = Depends(get_current_user)):
    return conversation_service.list(current_user.id)


@router.get("/{conversation_id}", response_model=ConversationDetailOut)
def get_conversation(conversation_id: str, current_user: AuthUser = Depends(get_current_user)):
    conversation = conversation_service.get_detail(conversation_id, current_user.id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.patch("/{conversation_id}", response_model=ConversationOut)
def rename_conversation(conversation_id: str, payload: ConversationUpdateRequest, current_user: AuthUser = Depends(get_current_user)):
    conversation = conversation_service.rename(conversation_id, current_user.id, payload.title)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.delete("/{conversation_id}")
def delete_conversation(conversation_id: str, current_user: AuthUser = Depends(get_current_user)):
    if not conversation_service.delete(conversation_id, current_user.id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"deleted": True, "conversation_id": conversation_id}
