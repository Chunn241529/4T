from fastapi import HTTPException, status
from pydantic import BaseModel
from typing import Optional
import httpx
import json
from auth.auth import validate_api_key
from models.models import Subscription, ImageGenerationHistory, User
from config.settings import API_TIMEOUT, COMFYUI_API_URL, COMFYUI_HISTORY_URL, COMFYUI_VIEW_URL
from services.chat_service import stream_chat_service_no_auth
from schemas.schemas import ChatRequest
from config.payload import payload_genimage_realistic, payload_genimage_2d, payload_genimage_Semi_Real
from sqlalchemy.orm import Session
from datetime import datetime
import asyncio
import os
from pathlib import Path
import base64
import re

from schemas.schemas import ImageGenRequest, ImageGenerationResponse


async def save_image_to_server(image_data: bytes, filename: str, positive_prompt: str, size: str, subscription_id: int, current_user, db: Session):
    # Tạo thư mục theo user_id
    image_dir = Path(f"storages/images/{current_user.id}")
    image_dir.mkdir(parents=True, exist_ok=True)

    # Đường dẫn file trên server
    file_path = image_dir / filename
    try:
        with open(file_path, "wb") as f:
            f.write(image_data)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Lỗi khi lưu ảnh vào server: {str(e)}")

    # Lưu vào ImageGenerationHistory
    image_history = ImageGenerationHistory(
        user_id=current_user.id,
        subscription_id=subscription_id,
        positive_prompt=positive_prompt,
        size=size,
        file_path=str(file_path)
    )
    db.add(image_history)
    db.commit()

    return str(file_path)


async def generate_image_service(request: ImageGenRequest, user, db: Session) -> ImageGenerationResponse:
    # Tìm API key hợp lệ
    api_key = None
    subscription_id = None
    subscription = db.query(Subscription).filter(
        Subscription.api_key == request.api_key if request.api_key else Subscription.user_id == user.id,
        Subscription.user_id == user.id,
        Subscription.end_date >= datetime.utcnow()
    ).order_by(Subscription.end_date.desc()).first()

    if not subscription:
        raise HTTPException(status_code=401 if request.api_key else 404,
                            detail="API key không hợp lệ hoặc đã hết hạn" if request.api_key else "Không tìm thấy gói đăng ký đang hoạt động")

    api_key = request.api_key or subscription.api_key
    subscription_id = subscription.id

    # Xác thực API key
    try:
        validated_user = await validate_api_key(api_key=api_key, db=db)
        if not validated_user:
            raise HTTPException(status_code=401, detail="API key không hợp lệ")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Lỗi xác thực: {str(e)}")

    # Kiểm tra và thay thế nội dung NSFW
    def sanitize_prompt(prompt: str) -> str:
        # Danh sách các từ khóa NSFW cần kiểm tra
        nsfw_keywords = [
            "nude", "naked", "nsfw", "porn", "sex", "hentai", "xxx",
            "breasts", "nipples", "genitals", "explicit", "18+", "r-18",
            "bikini", "lingerie", "underwear", "seductive", "erotic", "lewd",
            "ecchi", "fanservice", "revealing", "suggestive"
        ]

        # Danh sách thay thế cute
        cute_replacements = [
            "cute puppy", "adorable kitten", "fluffy bunny", "baby panda",
            "sweet teddy bear", "lovely hamster", "happy duck", "colorful bird",
            "playful dolphin", "gentle butterfly", "friendly penguin", "baby seal",
            "happy unicorn", "cute cartoon character", "friendly animal"
        ]

        prompt_lower = prompt.lower()
        contains_nsfw = any(keyword in prompt_lower for keyword in nsfw_keywords)

        if contains_nsfw:
            # Chọn ngẫu nhiên một chủ đề cute để thay thế
            import random
            safe_prompt = f"cute and wholesome {random.choice(cute_replacements)}"
            print(f"NSFW content detected. Replaced with: {safe_prompt}")
            return safe_prompt

        return prompt

    # Determine the image style based on prompt
    def determine_style(prompt: str) -> str:
        prompt = prompt.lower()
        if "2d" in prompt or "anime" in prompt or "manga" in prompt:
            return "2d"
        elif "3d" in prompt or "semi real" in prompt or "semi-real" in prompt:
            return "semi_real"
        return "real"  # default

    # Kiểm tra nội dung với LLM
    async def check_content_safety(prompt: str, db: Session) -> dict:
        safety_check_request = ChatRequest(
            model="4T-S",
            prompt=f"""
            Bạn là AI assistant tên '4T' có nhiệm vụ kiểm duyệt nội dung.

            Hãy phân tích yêu cầu tạo hình ảnh sau: "{prompt}"

            Kiểm tra các tiêu chí:
            1. Nội dung người lớn hoặc khiêu dâm
            2. Bạo lực hoặc máu me
            3. Ma túy hoặc chất kích thích
            4. Phân biệt chủng tộc hoặc tôn giáo
            5. Nội dung chính trị nhạy cảm
            6. Nội dung độc hại hoặc tiêu cực

            Trả về JSON với format:
            {{
                "is_safe": true/false,
                "message": "Lý do nếu không an toàn",
                "redirect": "storages/smile.jpg" nếu không an toàn
            }}

            CHỈ trả về JSON, không thêm giải thích.
            """,
            conversation_id=None,
            api_key=None
        )

        full_response = ""
        check_result = await stream_chat_service_no_auth(safety_check_request, db, temperature=0.4, num_predict=-1)

        async for chunk in check_result.body_iterator:
            try:
                chunk_str = chunk.decode('utf-8')
                if "content" in chunk_str:
                    data = json.loads(chunk_str)
                    if "message" in data and "content" in data["message"]:
                        content = data["message"]["content"]
                        if content:
                            full_response += content
            except Exception as e:
                print(f"Error processing safety check chunk: {str(e)}")
                continue

        try:
            # Clean and parse JSON response
            cleaned_response = re.sub(r'^```json\s*|\s*```$', '', full_response.strip()).strip()
            json_match = re.search(r'\{.*\}', cleaned_response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
        except Exception as e:
            print(f"Error parsing safety check response: {str(e)}")

        # Default to safe if there's any error
        return {"is_safe": True, "message": "", "redirect": None}

    # Hàm đọc và chuyển đổi ảnh sang base64
    def get_image_base64(image_data: bytes) -> str:
        try:
            base64_data = base64.b64encode(image_data).decode('utf-8')
            return f"data:image/jpeg;base64,{base64_data}"
        except Exception as e:
            print(f"Error encoding image to base64: {str(e)}")
            return ""

    # Kiểm tra an toàn trước
    safety_result = await check_content_safety(request.prompt, db)
    if not safety_result["is_safe"]:
        print(f"Unsafe content detected: {safety_result['message']}")
        smile_image_path = "storages/smile.jpg"
        try:
            with open(smile_image_path, "rb") as img_file:
                image_data = img_file.read()
                base64_image = get_image_base64(image_data)
                if base64_image:
                    return ImageGenerationResponse(
                        id=0,
                        positive_prompt="Safe content only",
                        size="1024x1024",
                        base64=base64_image,  # Trả về ảnh mặc định dưới dạng base64
                        timestamp=datetime.utcnow()
                    )
                else:
                    raise HTTPException(
                        status_code=500,
                        detail="Không thể mã hóa ảnh mặc định sang base64"
                    )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Không thể đọc ảnh mặc định: {str(e)}"
            )

    # Nếu an toàn, tiếp tục với sanitize và xử lý bình thường
    safe_prompt = sanitize_prompt(request.prompt)
    style = determine_style(safe_prompt)

    # Define style-specific prompts
    style_prompts = {
        "2d": """
            masterpiece, best quality, sharp, high resolution, anime style, 2d art, illustration, japanese anime, clean lines, vibrant colors, detailed, ultra-detailed, highly detailed, intricate details
        """,
        "semi_real": """
            masterpiece, best quality, sharp, high resolution, semi-realistic, unreal engine, 3d render, octane render, subsurface scattering, cinematic lighting, detailed, ultra-detailed, highly detailed, intricate details
        """,
        "real": """
            masterpiece, best quality, sharp, high resolution, realistic, photorealistic, cinematic lighting, professional photography, RAW photo, 8k uhd, detailed, ultra-detailed, highly detailed, intricate details
        """
    }

    generate_positive_prompt_request = ChatRequest(
        model="4T-L",
        prompt=f"""
        Bạn là trình tạo prompt cho ComfyUI, chuyên tạo JSON từ yêu cầu của người dùng.

        Nhiệm vụ:
        Từ yêu cầu của người dùng: "{safe_prompt}", tạo một JSON object chứa hai trường:
        - "positive_prompt": chuỗi mô tả chi tiết dựa trên yêu cầu CHÍNH XÁC của người dùng.
        - "size": chuỗi kích thước ảnh.

        QUAN TRỌNG: Luôn phải tôn trọng chủ thể trong yêu cầu của người dùng.
        - Nếu người dùng yêu cầu vẽ mèo -> phải tạo prompt về mèo, KHÔNG được chuyển thành người
        - Nếu người dùng yêu cầu vẽ phong cảnh -> phải tạo prompt về phong cảnh, KHÔNG được thêm nhân vật

        Style được xác định: {style}
        Base prompt cho style này: {style_prompts[style]}

        Quy tắc cho "positive_prompt":
        - Bắt đầu bằng base prompt ở trên.
        - Thêm trọng số cho các từ khóa quan trọng: (((key word))), ((key word)), (key word)
        - TẬP TRUNG vào mô tả chi tiết chủ thể chính từ yêu cầu của người dùng
        - Nếu yêu cầu đề cập đến con người hoặc nhân vật, hãy xử lý tuổi như sau:
          - Nếu có số tuổi cụ thể: thêm "<số tuổi> years old" với trọng số nếu quan trọng, ví dụ: (30 years old), không phải (30-year-old)
          - Nếu không rõ tuổi nhưng có gợi ý (như "trẻ em", "người già"): chuyển thành danh mục phù hợp như "baby" (0-2 tuổi), "child" (3-12 tuổi), "teenager" (13-19 tuổi), "young adult" (20-35 tuổi), "middle-aged" (36-55 tuổi), "elderly" (56+ tuổi), và thêm trọng số nếu cần.
          - Nếu không có thông tin tuổi: mặc định "adult" cho nhân vật trưởng thành, hoặc suy luận từ ngữ cảnh (ví dụ: học sinh -> teenager).
          - Điều chỉnh theo style: trong 2d/anime, dùng "chibi" cho trẻ em nếu phù hợp; trong real, dùng mô tả thực tế như "wrinkled skin" cho elderly.

        Quy tắc chi tiết theo style:
          2D/Anime style (nếu là 2d):
          - Sử dụng các từ khóa phù hợp: anime style, cel shading, clean lines
          - Nếu là động vật: cute animal, chibi style, kawaii
          - Nếu là phong cảnh: anime background art, ghibli style
          - Nếu là nhân vật: anime character, bishoujo/bishounen

          Semi-realistic style (nếu là semi_real):
          - Sử dụng các từ khóa 3D: 3d model, unreal engine
          - Ánh sáng: volumetric lighting, rim light, dynamic lighting
          - Chất liệu: detailed textures, fine materials, subsurface scattering
          - Chi tiết: fine details, high detail textures

          Realistic style (nếu là real):
          - Sử dụng các từ khóa photography
          - Ánh sáng: studio lighting, natural lighting
          - Chi tiết: highly detailed, intricate details
          - Môi trường: environmental details, realistic materials

        Các quy tắc chung cho mọi style:
        - Góc nhìn: Cowboy shot, wide angle, dynamic angle.
        - Ánh sáng và hiệu ứng: Daytime, natural lighting, motion blur, etc.
        - Đảm bảo các từ khóa phù hợp với style đã chọn.

        Định dạng:
        - Mỗi từ hoặc cụm từ PHẢI phân tách bằng dấu phẩy và MỘT khoảng trắng (", ").
        - KHÔNG nén, KHÔNG bỏ khoảng trắng sau phẩy.

        Quy tắc cho "size":
        - "768x1024" cho chân dung hoặc nhân vật chính.
        - "1024x768" cho phong cảnh hoặc góc rộng.
        - "1024x1024" cho vuông hoặc không rõ.

        Đầu ra:
        - Chỉ trả về JSON: {{"positive_prompt": "...", "size": "..."}}
        - KHÔNG bao bọc markdown, KHÔNG thêm thừa, Không thêm bất kì thứ gì.
        - JSON hợp lệ, chuỗi có khoảng trắng sau phẩy.
        """,
        conversation_id=None,
        api_key=None
    )

    _positive_prompt = ""
    _size = "1024x1024"  # Default size
    full_response = ""

    gen_prompt = await stream_chat_service_no_auth(generate_positive_prompt_request, db, temperature=0.4, num_predict=-1)
    async for chunk in gen_prompt.body_iterator:
        try:
            chunk_str = chunk.decode('utf-8')
            if "content" in chunk_str:
                data = json.loads(chunk_str)
                if "message" in data and "content" in data["message"]:
                    content = data["message"]["content"]
                    if content:
                        full_response += content
        except Exception as e:
            print(f"Error processing chunk: {str(e)}")
            continue

    if full_response:
        print(f"Full response from chat service: {full_response}")
        try:
            # Làm sạch phản hồi: loại bỏ markdown và ký tự thừa
            cleaned_response = full_response.strip()
            cleaned_response = re.sub(
                r'^```json\s*|\s*```$', '', cleaned_response).strip()
            cleaned_response = re.sub(
                r'^```\s*|\s*```$', '', cleaned_response).strip()

            # Extract phần JSON bằng cách tìm substring từ '{' đến '}'
            json_match = re.search(r'\{.*\}', cleaned_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                # Parse JSON
                response_data = json.loads(json_str)
                _positive_prompt = response_data.get("positive_prompt", "")
                _size = response_data.get("size", "1024x1024")

                # Sửa định dạng positive_prompt
                if _positive_prompt:
                    # Tách và nối lại với ", " để đảm bảo khoảng trắng
                    _positive_prompt = ", ".join(
                        term.strip() for term in _positive_prompt.split(",") if term.strip())

                print(f"Parsed JSON successfully:")
                print(f"Positive Prompt: {_positive_prompt}")
                print(f"Size: {_size}")
            else:
                raise ValueError("Không tìm thấy JSON object trong phản hồi")
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON: {str(e)}")
            print(f"Raw response: {full_response}")
            raise HTTPException(
                status_code=500, detail=f"Lỗi khi parse JSON từ phản hồi: {str(e)}")
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Lỗi khi xử lý phản hồi JSON: {str(e)}")

    # Validate and extract width and height
    try:
        width, height = map(int, _size.split("x"))
        if width <= 0 or height <= 0:
            raise ValueError
    except:
        print(f"Invalid size format: {_size}, using default")
        width, height = 1024, 1024

    # Analyze prompt to determine which payload to use
    def determine_payload_type(prompt: str) -> str:
        prompt = prompt.lower()
        if "2d" in prompt or "anime" in prompt or "manga" in prompt:
            return "2d"
        elif "3d" in prompt or "semi real" in prompt or "semi-real" in prompt:
            return "semi_real"
        elif "real" in prompt or "realistic" in prompt or "photograph" in prompt:
            return "real"
        return "real"  # default to realistic

    payload_type = determine_payload_type(request.prompt)

    # Select appropriate payload generator
    if payload_type == "2d":
        comfyui_payload = payload_genimage_2d(
            client_id=user.id,
            positive_prompt=_positive_prompt,
            width=width,
            height=height
        )
    elif payload_type == "semi_real":
        comfyui_payload = payload_genimage_Semi_Real(
            client_id=user.id,
            positive_prompt=_positive_prompt,
            width=width,
            height=height
        )
    else:  # real or default
        comfyui_payload = payload_genimage_realistic(
            client_id=user.id,
            positive_prompt=_positive_prompt,
            width=width,
            height=height
        )

    async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
        try:
            response = await client.post(COMFYUI_API_URL, json=comfyui_payload)
            response.raise_for_status()
            result = response.json()
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=500, detail=f"Lỗi khi gọi API ComfyUI /api/prompt: {str(e)}")

        if "prompt_id" not in result:
            raise HTTPException(
                status_code=500, detail="Không tìm thấy prompt_id từ ComfyUI")

        prompt_id = result["prompt_id"]

        filename = None
        max_retries = 20
        retry_delay = 3
        for attempt in range(max_retries):
            try:
                history_response = await client.get(f"{COMFYUI_HISTORY_URL}?max_items=64")
                history_response.raise_for_status()
                history_data = history_response.json()

                if str(prompt_id) in history_data:
                    outputs = history_data[str(prompt_id)].get("outputs", {})
                    # Xác định node ID dựa vào loại payload
                    node_id = "17" if payload_type in ["2d", "semi_real"] else "30"

                    if node_id in outputs:
                        output_files = outputs[node_id].get("images", [])
                        if output_files and isinstance(output_files, list):
                            filename = output_files[0].get("filename")
                            if filename and outputs[node_id]["images"][0].get("type") == "output":
                                print(f"Found image filename: {filename} from node {node_id}")
                                break
                    else:
                        print(f"Node {node_id} not found in outputs. Available nodes: {list(outputs.keys())}")
                await asyncio.sleep(retry_delay)
            except httpx.HTTPError as e:
                raise HTTPException(
                    status_code=500, detail=f"Lỗi khi gọi API ComfyUI /api/history: {str(e)}")

        if not filename:
            raise HTTPException(
                status_code=500, detail="Không thể lấy filename từ ComfyUI history sau nhiều lần thử")

        image_data = None
        try:
            view_params = {
                "filename": filename,
                "subfolder": "",
                "type": "output",
                "rand": str(datetime.now().timestamp())
            }
            image_response = await client.get(COMFYUI_VIEW_URL, params=view_params)
            image_response.raise_for_status()
            image_data = image_response.content
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=500, detail=f"Lỗi khi lấy ảnh từ ComfyUI /api/view: {str(e)}")

    if not image_data:
        raise HTTPException(
            status_code=500, detail="Không thể lấy dữ liệu ảnh từ ComfyUI")

    drive_filename = f"generated_image_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.png"
    file_path = await save_image_to_server(image_data, drive_filename, _positive_prompt, _size, subscription_id, user, db)

    # Chuyển đổi image_data sang base64
    base64_image = get_image_base64(image_data)
    if not base64_image:
        raise HTTPException(
            status_code=500,
            detail="Không thể mã hóa ảnh sang base64"
        )

    return ImageGenerationResponse(
        id=db.query(ImageGenerationHistory).filter(
            ImageGenerationHistory.user_id == user.id,
            ImageGenerationHistory.file_path == file_path
        ).first().id,
        positive_prompt=_positive_prompt,
        size=_size,
        base64=base64_image,  # Trả về base64 thay vì đường dẫn tệp
        timestamp=datetime.utcnow()
    )
