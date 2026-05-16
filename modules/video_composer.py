import os
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFont
import textwrap

def add_text_to_image(image_path, text, output_path):
    """
    Vẽ text lên ảnh bằng Pillow với nền đen mờ phía sau (Sub chuyên nghiệp).
    Tự động resize ảnh về kích thước chẵn để tương thích H.264.
    """
    img = Image.open(image_path).convert("RGBA")
    width, height = img.size
    
    # Ép kích thước chẵn (H.264 bắt buộc)
    new_w = width if width % 2 == 0 else width - 1
    new_h = height if height % 2 == 0 else height - 1
    if new_w != width or new_h != height:
        img = img.resize((new_w, new_h), Image.LANCZOS)
        width, height = new_w, new_h
    
    # Tạo overlay trong suốt để vẽ nền đen mờ
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    
    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except IOError:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
        except IOError:
            font = ImageFont.load_default()
    
    # Wrap text (ngắn hơn, max 50 ký tự mỗi dòng)
    lines = textwrap.wrap(text, width=50)
    
    # Tính tổng chiều cao text
    line_heights = []
    for line in lines:
        bbox = overlay_draw.textbbox((0, 0), line, font=font)
        line_heights.append(bbox[3] - bbox[1])
    
    total_text_height = sum(line_heights) + 10 * (len(lines) - 1)
    padding = 20
    
    # Vị trí: phần dưới màn hình
    box_top = height - total_text_height - padding * 2 - 30
    box_bottom = height - 10
    
    # Vẽ nền đen mờ (alpha = 160 / 255 ≈ 63% độ đục)
    overlay_draw.rectangle(
        [(10, box_top), (width - 10, box_bottom)],
        fill=(0, 0, 0, 160)
    )
    
    # Ghép overlay vào ảnh gốc
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)
    
    # Vẽ chữ trắng (không cần viền đen nữa vì đã có nền mờ)
    y_text = box_top + padding
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_width = bbox[2] - bbox[0]
        x_text = (width - line_width) / 2
        draw.text((x_text, y_text), line, font=font, fill="white")
        y_text += (bbox[3] - bbox[1]) + 10
        
    img = img.convert("RGB")
    img.save(output_path)
    return output_path

def create_video(slide_groups: list, output_path: str, output_dir: str, bgm_path: str = None):
    """
    Ghép video từ cấu trúc phân cấp:
    slide_groups = [
        {"image_path": "...", "segments": [{"text": "...", "audio_path": "..."}]}
    ]
    Mỗi Slide sẽ giữ nguyên hình ảnh, nhưng tạo nhiều sub-clip với phụ đề + audio khác nhau.
    """
    clips = []
    
    for slide_i, group in enumerate(slide_groups):
        image_path = group.get('image_path')
        segments = group.get('segments', [])
        
        if not image_path:
            continue
            
        for seg_i, seg in enumerate(segments):
            audio_path = seg.get('audio_path')
            text = seg.get('text', '')
            
            if not audio_path:
                continue
            
            # Vẽ phụ đề lên ảnh cho sub-clip này
            sub_img_path = os.path.join(output_dir, f"slide_{slide_i}_seg_{seg_i}.png")
            add_text_to_image(image_path, text, sub_img_path)
            
            # Load audio
            audio_clip = AudioFileClip(audio_path)
            duration = audio_clip.duration
            
            # Tạo clip: ảnh slide + sub riêng + audio riêng
            img_clip = ImageClip(sub_img_path).with_duration(duration)
            img_clip = img_clip.with_audio(audio_clip)
            
            clips.append(img_clip)
        
    if clips:
        print(f"Đang render {len(clips)} sub-clip thành video chung...")
        final_video = concatenate_videoclips(clips, method="compose")
        
        # Thêm nhạc nền nếu có
        if bgm_path and os.path.exists(bgm_path):
            from moviepy import CompositeAudioClip, concatenate_audioclips
            import math
            bgm = AudioFileClip(bgm_path)
            repeats = math.ceil(final_video.duration / bgm.duration)
            bgm = concatenate_audioclips([bgm] * repeats)
            bgm = bgm.with_duration(final_video.duration).with_volume_scaled(0.1)
            
            final_audio = CompositeAudioClip([final_video.audio, bgm])
            final_video = final_video.with_audio(final_audio)

        final_video.write_videofile(
            output_path, 
            fps=10, 
            codec="libx264",
            audio_codec="aac",
            ffmpeg_params=["-pix_fmt", "yuv420p", "-preset", "ultrafast"]
        )
        print(f"Video đã xuất thành công tại: {output_path}")
    else:
        print("Không có clip nào để ghép.")
