from fastapi import APIRouter, Depends, HTTPException
import logging
from app.dependencies.auth import get_current_user
from app.schemas.auth import AuthUser
from fastapi.responses import StreamingResponse

from app.schemas.chat import MessageRequest, MessageResponse
from app.services.chat_service import ChatProviderUnavailableError, chat_service
from app.services.conversation_service import conversation_service
from app.services.document_service import document_service

router = APIRouter(prefix="/chat", tags=["chat"], dependencies=[Depends(get_current_user)])
logger = logging.getLogger(__name__)


@router.post("/{conversation_id}/messages", response_model=MessageResponse)
def send_message(conversation_id: str, payload: MessageRequest, current_user: AuthUser = Depends(get_current_user)):
    if conversation_service.get_detail(conversation_id, current_user.id) is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    user_message = payload.message.strip()
    logger.info("chat.request conversation_id=%s user_id=%s message_length=%s", conversation_id, current_user.id, len(user_message))
    conversation_service.add_message(conversation_id, current_user.id, "user", user_message)
    try:
        reply = chat_service.generate_reply(user_message, document_service.search(current_user.id, user_message))
    except ChatProviderUnavailableError as error:
        logger.error("chat.provider_unavailable conversation_id=%s user_id=%s", conversation_id, current_user.id)
        raise HTTPException(status_code=503, detail=str(error)) from error
    response = conversation_service.add_message(conversation_id, current_user.id, "assistant", reply)
    logger.info("chat.response conversation_id=%s user_id=%s response_length=%s", conversation_id, current_user.id, len(reply))
    return response


@router.post("/{conversation_id}/stream")
def stream_message(conversation_id: str, payload: MessageRequest, current_user: AuthUser = Depends(get_current_user)):
    if conversation_service.get_detail(conversation_id, current_user.id) is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conversation_service.add_message(conversation_id, current_user.id, "user", payload.message.strip())

    def event_stream():
        try:
            chunks = list(chat_service.stream_reply(payload.message, document_service.search(current_user.id, payload.message)))
        except ChatProviderUnavailableError as error:
            logger.error("chat.provider_unavailable conversation_id=%s user_id=%s", conversation_id, current_user.id)
            yield f"event: error\ndata: {error}\n\n"
            return
        for chunk in chunks:
            yield f"data: {chunk.replace(chr(10), chr(10) + 'data: ')}\n\n"
        conversation_service.add_message(conversation_id, current_user.id, "assistant", "".join(chunks))
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
