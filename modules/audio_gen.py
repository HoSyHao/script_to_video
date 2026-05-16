import os
import subprocess
from elevenlabs.client import ElevenLabs
from elevenlabs import save

import sys

def generate_audio(scenes: list, provider: str, api_key: str, output_dir: str, voice_id: str = "pNInz6obpgDQGcFmaJgB", edge_voice: str = "vi-VN-HoaiMyNeural"):
    """
    Duyệt qua danh sách các scene, tạo audio đọc text và lưu vào thư mục.
    Cập nhật trường 'audio_path' vào scene.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    client = None
    if provider == "elevenlabs":
        if not api_key:
            raise ValueError("Vui lòng nhập ElevenLabs API Key để dùng ElevenLabs")
        client = ElevenLabs(api_key=api_key)

    for i, scene in enumerate(scenes):
        text = scene.get("text", "")
        audio_path = os.path.join(output_dir, f"scene_{i}.mp3")
        
        print(f"Đang tạo audio cho scene {i}...")

        if provider == "edge-tts":
            # Sử dụng Edge-TTS (Cực hay, miễn phí)
            import subprocess
            temp_txt = os.path.join(output_dir, f"temp_{i}.txt")
            with open(temp_txt, "w", encoding="utf-8") as f:
                f.write(text)
            
            # Khắc phục lỗi crash bằng cách đọc text từ file thay vì pass trực tiếp string vào CLI
            cmd = [
                "python", "-m", "edge_tts",
                "--voice", edge_voice,
                "--file", temp_txt,
                "--write-media", audio_path
            ]
            subprocess.run(cmd, check=True)
            
            # Xóa file temp
            if os.path.exists(temp_txt):
                os.remove(temp_txt)
            
        elif provider == "elevenlabs":
            # Sử dụng cú pháp mới của thư viện ElevenLabs v2.x
            audio_generator = client.text_to_speech.convert(
                text=text,
                voice_id=voice_id,
                model_id="eleven_multilingual_v2"
            )
            with open(audio_path, "wb") as f:
                for chunk in audio_generator:
                    if chunk:
                        f.write(chunk)
        
        scene['audio_path'] = audio_path
        
    return scenes
