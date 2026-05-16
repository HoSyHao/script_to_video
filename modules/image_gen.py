import os
import urllib.parse
import requests
from openai import OpenAI

def generate_images(scenes: list, provider: str, api_key: str, output_dir: str):
    """
    Duyệt qua danh sách các scene, tạo ảnh dựa trên image_prompt và lưu vào thư mục.
    Cập nhật trường 'image_path' vào scene.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    client = None
    if provider == "dalle":
        if not api_key:
            raise ValueError("Vui lòng nhập OpenAI API Key để dùng DALL-E")
        client = OpenAI(api_key=api_key)

    for i, scene in enumerate(scenes):
        prompt = scene.get("image_prompt", "")
        img_path = os.path.join(output_dir, f"scene_{i}.png")
        
        print(f"Đang tạo ảnh cho scene {i}...")

        if provider == "pollinations":
            # Sử dụng Pollinations.ai (Miễn phí, không cần API Key)
            # URL format: https://image.pollinations.ai/prompt/{prompt}?width={width}&height={height}&nologo=true
            safe_prompt = urllib.parse.quote(prompt)
            url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1024&height=1024&nologo=true"
            response = requests.get(url)
            if response.status_code == 200:
                with open(img_path, 'wb') as f:
                    f.write(response.content)
            else:
                raise Exception(f"Lỗi khi tạo ảnh từ Pollinations: {response.status_code}")
                
        elif provider == "presentation":
            # Tạo slide kiến thức (Màu nền ngẫu nhiên + viền trang trí)
            from PIL import Image, ImageDraw
            bg_colors = [(15, 23, 42), (30, 41, 59), (17, 24, 39), (24, 24, 27), (69, 10, 10)]
            bg_color = bg_colors[i % len(bg_colors)]
            img = Image.new('RGB', (1024, 1024), color=bg_color)
            draw = ImageDraw.Draw(img)
            draw.rectangle([(40, 40), (984, 984)], outline=(148, 163, 184), width=4)
            img.save(img_path)
                
        elif provider == "dalle":
            # Sử dụng DALL-E 3 của OpenAI
            response = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )
            image_url = response.data[0].url
            # Tải ảnh về
            img_data = requests.get(image_url).content
            with open(img_path, 'wb') as f:
                f.write(img_data)
        
        scene['image_path'] = img_path
        
    return scenes
