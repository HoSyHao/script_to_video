import os
from google import genai
import json

def parse_script(script_text: str, api_key: str):
    """
    Sử dụng Gemini API để chia kịch bản thành các câu/phân cảnh
    và sinh prompt hình ảnh bằng tiếng Anh cho mỗi phân cảnh.
    """
    os.environ['GEMINI_API_KEY'] = api_key
    client = genai.Client()
    
    prompt = f"""
    Bạn là một chuyên gia kịch bản và đạo diễn hình ảnh AI. 
    Nhiệm vụ của bạn là chia đoạn kịch bản sau đây thành các phân cảnh nhỏ (mỗi phân cảnh khoảng 1-2 câu).
    Với mỗi phân cảnh, hãy viết một `image_prompt` (bằng TIẾNG ANH) miêu tả hình ảnh minh họa cho câu đó để gửi cho AI vẽ ảnh.
    
    🔥 LƯU Ý CỰC KỲ QUAN TRỌNG ĐỂ ẢNH KHÔNG BỊ LỖI (DÀNH CHO AI MIỄN PHÍ):
    1. TUYỆT ĐỐI KHÔNG vẽ chữ viết, văn bản hay con số trong ảnh (vì AI vẽ chữ rất xấu và vô nghĩa). Bắt buộc phải thêm cụm "no text, no words, no watermarks" vào cuối MỌI image_prompt.
    2. HẠN CHẾ TỐI ĐA vẽ khuôn mặt người cận cảnh vì AI dễ vẽ méo mó. Hãy tập trung vẽ CÁC ĐỒ VẬT TƯỢNG TRƯNG, PHONG CẢNH, GÓC CHỤP SAU LƯNG, hoặc BÀN TAY.
    3. Phong cách ưu tiên: Cinematic lighting, Minimalist, 3D Render, Macro photography, depth of field.
    
    Ví dụ TỐT: "A glowing golden Bitcoin on a dark modern desk, cinematic lighting, macro shot, no text, no words"
    Ví dụ XẤU (Tuyệt đối tránh): "A man holding a sign saying Bitcoin, showing his face"
    
    Kịch bản:
    {script_text}

    Hãy trả về ĐÚNG MỘT mã JSON mảng (list), mỗi phần tử là một object có 2 trường: "text" (câu thoại tiếng Việt gốc) và "image_prompt" (prompt tiếng Anh).
    Không trả về markdown code block, chỉ trả về JSON.
    Ví dụ:
    [
        {{"text": "Xin chào các bạn đến với kênh tài chính.", "image_prompt": "A professional financial analyst sitting at a modern desk with multiple monitors displaying stock charts, cinematic lighting, 8k"}},
        {{"text": "Hôm nay chúng ta sẽ bàn về Bitcoin.", "image_prompt": "A glowing golden Bitcoin coin floating in a futuristic digital environment, cyber style, highly detailed"}}
    ]
    """
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    
    # Làm sạch response để lấy JSON
    res_text = response.text.strip()
    if res_text.startswith("```json"):
        res_text = res_text[7:]
    if res_text.endswith("```"):
        res_text = res_text[:-3]
    
    try:
        scenes = json.loads(res_text.strip())
        return scenes
    except Exception as e:
        print("Lỗi parse JSON:", e)
        print("Response trả về:", res_text)
        raise ValueError("Gemini không trả về đúng định dạng JSON. Vui lòng thử lại.")

def parse_script_with_slides(script_text: str, slide_texts: list, api_key: str, slide_image_paths: list = None):
    """
    Ép Gemini chia kịch bản thoại thành N nhóm (tương ứng N Slide).
    Mỗi nhóm chứa NHIỀU câu sub ngắn (segments).
    Nếu có slide_image_paths, sẽ gửi ảnh Slide cho Gemini NHÌN THẤY trực quan (Multimodal).
    """
    os.environ['GEMINI_API_KEY'] = api_key
    client = genai.Client()
    from google.genai import types
    
    slides_info = ""
    for i, t in enumerate(slide_texts):
        slides_info += f"Slide {i+1}: {t}\n"
        
    prompt_text = f"""
    Bạn là một đạo diễn âm thanh chuyên nghiệp. Tôi có một Kịch bản thoại dài và {len(slide_texts)} trang Slide thuyết trình.
    Tôi cũng GỬI KÈM HÌNH ẢNH các trang Slide để bạn NHÌN THẤY trực quan nội dung và bố cục của từng Slide.
    
    Kịch bản thoại gốc:
    {script_text}

    Nội dung text trên các trang Slide (để tham khảo thêm):
    {slides_info}

    NHIỆM VỤ CỦA BẠN:
    1. NHÌN KỸ từng hình ảnh Slide được gửi kèm để hiểu nội dung trực quan.
    2. Chia kịch bản gốc thành ĐÚNG {len(slide_texts)} nhóm, mỗi nhóm ứng với 1 Slide.
    3. Trong mỗi nhóm, tách thành NHIỀU câu sub ngắn (mỗi câu khoảng 1-2 câu nói, tối đa 30 từ).
    
    🔥 LUẬT THÉP:
    - KHÔNG ĐƯỢC TÓM TẮT. BÊ NGUYÊN XI từng chữ từ Kịch bản gốc.
    - Chỉ việc CẮT kịch bản thành các nhóm và các câu sub nối tiếp nhau.
    - Mapping phải DỰA TRÊN NỘI DUNG HÌNH ẢNH: đoạn kịch bản nói về chủ đề gì thì ghép với Slide có hình ảnh/biểu đồ liên quan.
    - Không rớt một chữ nào của kịch bản gốc.
    
    Trả về JSON (KHÔNG markdown code block). Cấu trúc:
    [
        {{
            "slide_index": 0,
            "segments": [
                {{"text": "Bạn có bao giờ thấy một người…"}},
                {{"text": "Đi làm chăm chỉ suốt 5 năm."}}
            ]
        }},
        {{
            "slide_index": 1,
            "segments": [
                {{"text": "Lương từ 8 triệu lên 20 triệu."}},
                {{"text": "Rất tiết kiệm. Ít ăn ngoài."}}
            ]
        }}
    ]
    (Độ dài mảng JSON phải đúng bằng {len(slide_texts)})
    """
    
    # Xây dựng nội dung multimodal: text + ảnh slide
    contents = [types.Part.from_text(text=prompt_text)]
    
    if slide_image_paths:
        for i, img_path in enumerate(slide_image_paths):
            with open(img_path, 'rb') as f:
                img_bytes = f.read()
            contents.append(types.Part.from_bytes(data=img_bytes, mime_type="image/png"))
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents
    )
    
    res_text = response.text.strip()
    if res_text.startswith("```json"):
        res_text = res_text[7:]
    if res_text.endswith("```"):
        res_text = res_text[:-3]
    
    try:
        result = json.loads(res_text.strip())
        return result
    except Exception as e:
        print("Lỗi parse JSON:", e)
        raise ValueError("Gemini không phân bổ được. Vui lòng thử lại.")
