from fastapi import APIRouter, Depends, HTTPException
from app.dependencies.auth import get_current_user
from app.schemas.auth import AuthUser
from fastapi.responses import StreamingResponse

from app.schemas.chat import MessageRequest, MessageResponse
from app.services.chat_service import chat_service
from app.services.conversation_service import conversation_service
from app.services.document_service import document_service

router = APIRouter(prefix="/chat", tags=["chat"], dependencies=[Depends(get_current_user)])


@router.post("/{conversation_id}/messages", response_model=MessageResponse)
def send_message(conversation_id: str, payload: MessageRequest, current_user: AuthUser = Depends(get_current_user)):
    if conversation_service.get_detail(conversation_id, current_user.id) is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    user_message = payload.message.strip()
    conversation_service.add_message(conversation_id, current_user.id, "user", user_message)
    reply = chat_service.generate_reply(user_message, document_service.search(current_user.id, user_message))
    return conversation_service.add_message(conversation_id, current_user.id, "assistant", reply)


@router.post("/{conversation_id}/stream")
def stream_message(conversation_id: str, payload: MessageRequest, current_user: AuthUser = Depends(get_current_user)):
    if conversation_service.get_detail(conversation_id, current_user.id) is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conversation_service.add_message(conversation_id, current_user.id, "user", payload.message.strip())

    def event_stream():
        chunks = list(chat_service.stream_reply(payload.message, document_service.search(current_user.id, payload.message)))
        for chunk in chunks:
            yield f"data: {chunk.replace(chr(10), chr(10) + 'data: ')}\n\n"
        conversation_service.add_message(conversation_id, current_user.id, "assistant", "".join(chunks))
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
