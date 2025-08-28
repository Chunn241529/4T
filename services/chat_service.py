from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse
import httpx
import json
import re
from datetime import datetime
from database import get_db
from schemas.schemas import ChatRequest, ChatHistoryResponse, ConversationResponse, ConversationCreate
from auth.auth import validate_api_key
from models.models import Subscription, ChatHistory, Conversation
from config.settings import API_TIMEOUT, DEFAULT_SYSTEM, OLLAMA_API_URL, OLLAMA_EMB_URL
from services.search_service import search_service
from sqlalchemy.orm import Session
from typing import List
import numpy as np
import tiktoken
from googletrans import Translator

ENCODING = tiktoken.encoding_for_model("gpt-3.5-turbo")
TRANSLATOR = Translator()

def count_tokens(text: str) -> int:
    return len(ENCODING.encode(text))

async def get_embedding(text: str, client: httpx.AsyncClient, translate: bool = True) -> list:
    input_text = text
    if translate:
        try:
            input_text = TRANSLATOR.translate(text, src='vi', dest='en').text
        except Exception as e:
            print(f"Lỗi dịch văn bản: {str(e)}")
    payload = {"model": "nomic-embed-text", "prompt": input_text}
    try:
        response = await client.post(f"{OLLAMA_EMB_URL}", json=payload)
        response.raise_for_status()
        return response.json().get("embedding", [])
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Lỗi tạo embedding: {str(e)}")

def cosine_similarity(a: list, b: list) -> float:
    a = np.array(a)
    b = np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

async def create_conversation_service(request: ConversationCreate, user, db: Session) -> ConversationResponse:
    conversation = Conversation(
        user_id=user.id,
        title=request.title or "New Conversation"
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation

async def stream_chat_service(request: ChatRequest, user, db: Session) -> StreamingResponse:
    user_id = user.id

    subscription = db.query(Subscription).filter(
        Subscription.api_key == request.api_key if request.api_key else Subscription.user_id == user_id,
        Subscription.user_id == user_id,
        Subscription.end_date >= datetime.utcnow()
    ).order_by(Subscription.end_date.desc()).first()

    if not subscription:
        raise HTTPException(status_code=401 if request.api_key else 404,
                            detail="API key không hợp lệ hoặc đã hết hạn" if request.api_key else "Không tìm thấy gói đăng ký đang hoạt động")

    api_key = request.api_key or subscription.api_key
    subscription_id = subscription.id

    try:
        validated_user = await validate_api_key(api_key=api_key, db=db)
        if not validated_user:
            raise HTTPException(status_code=401, detail="API key không hợp lệ")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Lỗi xác thực: {str(e)}")

    conversation_id = None
    if request.conversation_id:
        conversation = db.query(Conversation).filter(
            Conversation.id == request.conversation_id,
            Conversation.user_id == user_id
        ).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Không tìm thấy conversation")
        conversation_id = conversation.id
    else:
        conversation = Conversation(
            user_id=user_id,
            title=request.prompt[:50] + "..." if request.prompt else "New Conversation"
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        conversation_id = conversation.id

    history_query = db.query(ChatHistory).filter(
        ChatHistory.conversation_id == conversation_id
    ).order_by(ChatHistory.timestamp.desc()).limit(50).all()

    total_tokens = sum(count_tokens(hist.content) for hist in history_query)
    TOKEN_LIMIT = 32000

    async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
        prompt_embedding = await get_embedding(request.prompt, client, translate=True)

    if total_tokens > TOKEN_LIMIT:
        history_with_scores = []
        for hist in history_query:
            if hist.embedding:
                try:
                    embedding = json.loads(hist.embedding)
                    score = cosine_similarity(prompt_embedding, embedding)
                    history_with_scores.append((hist, score))
                except:
                    continue
        history_with_scores.sort(key=lambda x: x[1], reverse=True)
        selected_history = [hist for hist, _ in history_with_scores[:10]]
    else:
        selected_history = history_query

    current_time = datetime.now().strftime("%H:%M:%S")

    search_context = ""
    # Tạo search prompt đơn giản hóa
    search_prompt = f"""
    Tạo MỘT câu truy vấn tìm kiếm DUY NHẤT từ yêu cầu sau:
    "{request.prompt}"

    Quy tắc:
    - Chỉ trả về 1 câu truy vấn ngắn gọn nhất có thể
    - Sử dụng những từ khóa quan trọng nhất
    - Dùng tiếng Anh
    - KHÔNG giải thích hay liệt kê nhiều phương án
    - KHÔNG đánh số thứ tự hay thêm định dạng

    CHÚ Ý: Chỉ trả về đúng 1 truy vấn ngắn gọn, không thêm bất kỳ nội dung nào khác.
    """

    try:
        search_query_messages = [{"role": "user", "content": search_prompt}]
        search_query_payload = {
            "model": "4T-L",
            "messages": search_query_messages,
            "stream": False
        }

        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            print(f"[DEBUG] Generating search query for prompt: {request.prompt}")
            response = await client.post(OLLAMA_API_URL, json=search_query_payload)
            if response.status_code == 200:
                search_query = response.json().get("message", {}).get("content", "").strip()
                print(f"[DEBUG] Generated search query: {search_query}")
                search_results = search_service(search_query, max_results=3)

                if search_results:
                    search_context = "Dưới đây là thông tin liên quan:\n\n"
                    for idx, result in enumerate(search_results, 1):
                        title = result.get('title', 'Không có tiêu đề')
                        url = result.get('link', result.get('href', '#'))
                        content = result.get('content', '').strip()
                        if content:
                            search_context += f"{idx}. {title}\nNguồn: {url}\n{content}...\n\n"
    except Exception as e:
        print(f"Lỗi khi tìm kiếm: {str(e)}")

    # Tạo system prompt với context
    system_prompt = f"""
      Bạn là một AI assistant tích hợp với khả năng tìm kiếm thông tin chủ động.

      Bạn đang hỗ trợ cho user tên: `{user.username}`.
      Thời điểm hiện tại: `{current_time}`.

      {DEFAULT_SYSTEM}

      Dựa trên yêu cầu của user, tôi đã chủ động tìm kiếm và thu thập được thông tin sau:
      {search_context if search_context else 'Tôi đã tìm kiếm nhưng không tìm thấy thông tin phù hợp với yêu cầu của bạn.'}

      Hãy sử dụng thông tin tôi vừa tìm được để trả lời câu hỏi của user một cách chính xác và đáng tin cậy.
      Nếu thông tin không đủ, hãy nói rõ những gì chưa tìm thấy và đề xuất hướng tìm kiếm khác.
    """
    messages = [{"role": "system", "content": system_prompt}]
    messages += [{"role": hist.role, "content": hist.content} for hist in selected_history]
    messages.append({"role": "user", "content": request.prompt})

    async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
        original_prompt_embedding = await get_embedding(request.prompt, client, translate=False)
    new_user_msg = ChatHistory(
        user_id=user_id,
        conversation_id=conversation_id,
        subscription_id=subscription_id,
        role="user",
        content=request.prompt,
        embedding=json.dumps(original_prompt_embedding)
    )
    db.add(new_user_msg)
    db.commit()

    ollama_payload = {
        "model": request.model,
        "messages": messages,
        "stream": True,
        "options": {
            "temperature": 0.7,
            "num_predict": -1,
            "think": False
        }
    }

    full_response = ""
    async def stream_generator():
        nonlocal full_response
        from config.prompts import NEED_MORE_INFO_PATTERNS

        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            try:
                test_response = await client.post(OLLAMA_API_URL, json={**ollama_payload, "stream": False})
                if test_response.status_code != 200:
                    yield f"data: {{\"error\": \"API Ollama không khả dụng: Status {test_response.status_code}\"}}".encode()
                    return

                # Kiểm tra xem LLM có cần thêm thông tin không
                test_content = test_response.json().get("message", {}).get("content", "")
                needs_more_info = any(re.search(pattern, test_content.lower()) for pattern in NEED_MORE_INFO_PATTERNS)

                if needs_more_info:
                    # Tìm kiếm thêm thông tin
                    try:
                        search_results = search_service(request.prompt, max_results=3)
                        if search_results:
                            additional_context = "Tôi đã tìm thêm thông tin:\n\n"
                            for idx, result in enumerate(search_results, 1):
                                additional_context += f"{idx}. {result['title']}\n{result['content'][:500]}...\n\n"

                            # Thêm thông tin mới vào messages
                            messages.append({"role": "system", "content": additional_context})
                            messages.append({"role": "user", "content": "Bây giờ hãy trả lời câu hỏi của tôi với thông tin bổ sung trên"})

                            # Cập nhật payload với messages mới
                            ollama_payload["messages"] = messages
                    except Exception as e:
                        print(f"Lỗi khi tìm kiếm thông tin bổ sung: {str(e)}")

            except httpx.HTTPError as e:
                yield f"data: {{\"error\": \"Kiểm tra API Ollama thất bại: {str(e)}\"}}".encode()
                return

            try:
                async with client.stream("POST", OLLAMA_API_URL, json=ollama_payload) as response:
                    if response.status_code != 200:
                        yield f"data: {{\"error\": \"Lỗi API Ollama: Status {response.status_code}\"}}".encode()
                        return
                    async for chunk in response.aiter_bytes():
                        try:
                            chunk_str = chunk.decode('utf-8')
                            if "content" in chunk_str:
                                data = json.loads(chunk_str)
                                if "message" in data and "content" in data["message"]:
                                    content_delta = data["message"]["content"]
                                    full_response += content_delta
                                    yield chunk
                        except:
                            yield chunk
            except httpx.HTTPError as e:
                yield f"data: {{\"error\": \"Lỗi streaming API Ollama: {str(e)}\"}}".encode()

        if full_response:
            async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
                response_embedding = await get_embedding(full_response, client, translate=False)
            new_assistant_msg = ChatHistory(
                user_id=user_id,
                conversation_id=conversation_id,
                subscription_id=subscription_id,
                role="assistant",
                content=full_response,
                embedding=json.dumps(response_embedding)
            )
            db.add(new_assistant_msg)
            db.commit()

    return StreamingResponse(stream_generator(), media_type="text/event-stream")

async def get_conversations_service(user, db: Session) -> List[ConversationResponse]:
    conversations = db.query(Conversation).filter(Conversation.user_id == user.id).all()
    return conversations

async def get_history_service(conversation_id: int, user, db: Session) -> List[ChatHistoryResponse]:
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == user.id
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Không tìm thấy conversation")
    history = db.query(ChatHistory).filter(
        ChatHistory.conversation_id == conversation_id
    ).order_by(ChatHistory.timestamp.asc()).all()
    return history

async def delete_conversation_service(conversation_id: int, user, db: Session):
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == user.id
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Không tìm thấy conversation")
    db.delete(conversation)
    db.commit()
    return {"msg": "Conversation đã được xóa"}

async def delete_history_service(history_id: int, user, db: Session):
    history = db.query(ChatHistory).filter(
        ChatHistory.id == history_id,
        ChatHistory.user_id == user.id
    ).first()
    if not history:
        raise HTTPException(status_code=404, detail="Không tìm thấy tin nhắn")
    db.delete(history)
    db.commit()
    return {"msg": "Tin nhắn đã được xóa"}

async def stream_chat_service_no_auth(request: ChatRequest,  db: Session, temperature: int = 1, num_predict: int = -1,) -> StreamingResponse:
    try:
        current_time = datetime.now().strftime("%H:%M:%S")
        system_prompt = f"""
          Thời gian hiện tại là {current_time}.
          {DEFAULT_SYSTEM}
        """
        messages = [{"role": "system", "content": system_prompt}]
        messages.append({"role": "user", "content": request.prompt})

        ollama_payload = {
            "model": request.model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": num_predict,
                "think": False
            }
        }

        async def stream_generator():
            async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
                try:
                    test_response = await client.post(OLLAMA_API_URL, json={**ollama_payload, "stream": False})
                    if test_response.status_code != 200:
                        yield f"data: {{\"error\": \"API Ollama không khả dụng: Status {test_response.status_code}\"}}".encode()
                        return
                except httpx.HTTPError as e:
                    yield f"data: {{\"error\": \"Kiểm tra API Ollama thất bại: {str(e)}\"}}".encode()
                    return

                try:
                    async with client.stream("POST", OLLAMA_API_URL, json=ollama_payload) as response:
                        if response.status_code != 200:
                            yield f"data: {{\"error\": \"Lỗi API Ollama: Status {response.status_code}\"}}".encode()
                            return
                        async for chunk in response.aiter_bytes():
                            try:
                                yield chunk
                            except:
                                yield chunk
                except httpx.HTTPError as e:
                    yield f"data: {{\"error\": \"Lỗi streaming API Ollama: {str(e)}\"}}".encode()

        return StreamingResponse(stream_generator(), media_type="text/event-stream")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")

async def edit_history_service(history_id: int, content: str, user, db: Session):
    history = db.query(ChatHistory).filter(
        ChatHistory.id == history_id,
        ChatHistory.user_id == user.id,
        ChatHistory.role == "user"
    ).first()
    if not history:
        raise HTTPException(status_code=404, detail="Không tìm thấy tin nhắn hoặc không được phép sửa")
    async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
        new_embedding = await get_embedding(content, client, translate=False)
    history.content = content
    history.embedding = json.dumps(new_embedding)
    db.commit()
    return {"msg": "Tin nhắn đã được sửa"}
