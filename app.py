import streamlit as st
import os
from dotenv import load_dotenv

# Load API keys từ file .env
load_dotenv()

# Import modules
from modules.gemini_parser import parse_script_with_slides
from modules.audio_gen import generate_audio
from modules.video_composer import create_video

st.set_page_config(page_title="AI Video Generator", page_icon="🎬", layout="wide")

st.title("🎬 AI Script-to-Video Generator (Từ PDF Slide)")
st.markdown("Biến file PDF Slide và Kịch bản thành Video Slideshow lồng tiếng tự động.")

# Hàm đọc key: ưu tiên st.secrets (Cloud) → os.getenv (.env local)
def get_secret(key, default=""):
    try:
        return st.secrets[key]
    except:
        return os.getenv(key, default)

# --- CẤU HÌNH API KEYS (SIDEBAR) ---
st.sidebar.header("⚙️ Cài đặt API Keys")
st.sidebar.markdown("API Key được đọc tự động. Bạn cũng có thể nhập trực tiếp bên dưới.")

gemini_key = st.sidebar.text_input("Gemini API Key (Bắt buộc)", value=get_secret("GEMINI_API_KEY"), type="password")
st.sidebar.markdown("[👉 Lấy Gemini Key miễn phí](https://aistudio.google.com/app/apikey)", unsafe_allow_html=True)

elevenlabs_key = st.sidebar.text_input("ElevenLabs API Key (Tuỳ chọn)", value=get_secret("ELEVENLABS_API_KEY"), type="password")
st.sidebar.markdown("[👉 Lấy ElevenLabs Key](https://elevenlabs.io/app/settings/api-keys)", unsafe_allow_html=True)
elevenlabs_voice_id = st.sidebar.text_input("ElevenLabs Voice ID", value=get_secret("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB"))

st.sidebar.header("🗣️ Cấu hình Giọng đọc")
audio_provider = st.sidebar.selectbox("Nguồn tạo giọng đọc", ["edge-tts", "elevenlabs"], index=0, format_func=lambda x: "Microsoft Edge TTS (Miễn phí - Cực mượt)" if x=="edge-tts" else "ElevenLabs (Trả phí)")
edge_voice = st.sidebar.selectbox("Chọn giọng đọc Miễn phí", ["vi-VN-HoaiMyNeural", "vi-VN-NamMinhNeural"], format_func=lambda x: "Giọng Nữ truyền cảm (Hoài My)" if x=="vi-VN-HoaiMyNeural" else "Giọng Nam trầm ấm (Nam Minh)")

st.sidebar.header("🎵 Cấu hình Âm thanh")

# Tự động tạo thư mục và tải nhạc mẫu nếu chưa có
bgm_dir = "bgm_samples"
if not os.path.exists(bgm_dir):
    os.makedirs(bgm_dir)
    import urllib.request
    try:
        urllib.request.urlretrieve("https://www.soundhelix.com/examples/mp3/SoundHelix-Song-16.mp3", os.path.join(bgm_dir, "chill_1.mp3"))
        urllib.request.urlretrieve("https://www.soundhelix.com/examples/mp3/SoundHelix-Song-10.mp3", os.path.join(bgm_dir, "chill_2.mp3"))
    except:
        pass

bg_option = st.sidebar.radio("Nhạc nền", ["Không dùng", "Mẫu 1: Nhẹ nhàng (Chill)", "Mẫu 2: Tập trung", "Tự tải file của bạn"])

bg_music = None
if bg_option == "Tự tải file của bạn":
    bg_music = st.sidebar.file_uploader("Tải bài nhạc của bạn lên đây", type=["mp3", "wav"])

# --- GIAO DIỆN CHÍNH ---
st.subheader("📝 Kịch bản của bạn")
script_text = st.text_area("Nhập kịch bản (Narrative) vào đây...", height=200, placeholder="Ví dụ:\nXin chào các bạn đến với kênh tài chính.\nHôm nay chúng ta sẽ bàn về Bitcoin...")

st.subheader("📁 Tải lên File PDF (Slide từ NotebookLM/Canva)")
uploaded_pdf = st.file_uploader("Chọn file PDF Slide của bạn", type=["pdf"])

if st.button("🚀 Bắt đầu tạo Video", type="primary"):
    if not script_text.strip():
        st.error("Vui lòng nhập kịch bản!")
        st.stop()
    if not gemini_key:
        st.error("Vui lòng nhập Gemini API Key ở menu bên trái!")
        st.stop()
    if not uploaded_pdf:
        st.error("Vui lòng tải lên file PDF của bạn!")
        st.stop()
        
    output_dir = "assets"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    video_output_path = os.path.join(output_dir, "output_video.mp4")
    
    # Xử lý đường dẫn file nhạc nền
    bgm_path = None
    if bg_option == "Mẫu 1: Nhẹ nhàng (Chill)":
        bgm_path = os.path.join(bgm_dir, "chill_1.mp3")
    elif bg_option == "Mẫu 2: Tập trung":
        bgm_path = os.path.join(bgm_dir, "chill_2.mp3")
    elif bg_option == "Tự tải file của bạn" and bg_music is not None:
        bgm_path = os.path.join(output_dir, "uploaded_bgm.mp3")
        with open(bgm_path, "wb") as f:
            f.write(bg_music.getbuffer())
    
    try:
        with st.status("Đang tiến hành tạo Video...", expanded=True) as status:
            progress_bar = st.progress(0, text="Bắt đầu khởi tạo...")
            
            st.write("1️⃣ Đang trích xuất hình ảnh từ PDF...")
            progress_bar.progress(10, text="Đang bóc tách PDF...")
            import fitz
            pdf_bytes = uploaded_pdf.read()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            slide_texts = []
            extracted_image_paths = []
            
            for i, page in enumerate(doc):
                slide_texts.append(page.get_text("text").strip())
                pix = page.get_pixmap(dpi=150)
                img_path = os.path.join(output_dir, f"slide_pdf_{i}.png")
                pix.save(img_path)
                extracted_image_paths.append(img_path)
            
            st.write(f"Đã trích xuất {len(extracted_image_paths)} trang Slide.")
            
            st.write("2️⃣ Đang dùng Gemini AI nhìn ảnh + đọc kịch bản để map...")
            progress_bar.progress(20, text="Gemini đang phân tích hình ảnh và nội dung Slide...")
            slide_groups = parse_script_with_slides(script_text, slide_texts, gemini_key, extracted_image_paths)
            
            # Gắn image_path vào từng nhóm slide
            for i, group in enumerate(slide_groups):
                if i < len(extracted_image_paths):
                    group['image_path'] = extracted_image_paths[i]
                    
            with st.expander("👀 Bấm vào đây để xem cách AI Map nội dung"):
                st.json(slide_groups)
            
            # Đếm tổng số segment để tính %
            total_segs = sum(len(g.get('segments', [])) for g in slide_groups)
            done_segs = 0
            
            st.write(f"3️⃣ Đang tạo Audio cho {total_segs} câu sub...")
            
            # Tạo audio cho TỪNG câu sub riêng biệt
            from elevenlabs.client import ElevenLabs as EL
            el_client = None
            if audio_provider == "elevenlabs" and elevenlabs_key:
                el_client = EL(api_key=elevenlabs_key)
            
            for slide_i, group in enumerate(slide_groups):
                for seg_i, seg in enumerate(group.get('segments', [])):
                    text = seg.get('text', '')
                    audio_path = os.path.join(output_dir, f"slide_{slide_i}_seg_{seg_i}.mp3")
                    
                    if audio_provider == "edge-tts":
                        import subprocess
                        temp_txt = os.path.join(output_dir, f"temp_{slide_i}_{seg_i}.txt")
                        with open(temp_txt, "w", encoding="utf-8") as f:
                            f.write(text)
                        cmd = ["python", "-m", "edge_tts", "--voice", edge_voice, "--rate=+50%", "--file", temp_txt, "--write-media", audio_path]
                        subprocess.run(cmd, check=True)
                        if os.path.exists(temp_txt):
                            os.remove(temp_txt)
                    elif audio_provider == "elevenlabs" and el_client:
                        audio_gen = el_client.text_to_speech.convert(text=text, voice_id=elevenlabs_voice_id, model_id="eleven_multilingual_v2")
                        with open(audio_path, "wb") as f:
                            for chunk in audio_gen:
                                if chunk:
                                    f.write(chunk)
                    
                    seg['audio_path'] = audio_path
                    done_segs += 1
                    pct = 30 + int(50 * done_segs / total_segs)
                    progress_bar.progress(pct, text=f"Đang thu âm câu {done_segs}/{total_segs}...")
            
            st.write("4️⃣ Đang lắp ráp và Render Video...")
            progress_bar.progress(85, text="Đang nén Video và lồng nhạc nền...")
            create_video(slide_groups, video_output_path, output_dir, bgm_path)
            
            progress_bar.progress(100, text="Hoàn tất!")
            status.update(label="Tạo Video hoàn tất!", state="complete", expanded=False)
            
        st.success("🎉 Xin chúc mừng! Video của bạn đã sẵn sàng.")
        
        # Hiển thị Video
        with open(video_output_path, 'rb') as video_file:
            video_bytes = video_file.read()
            st.video(video_bytes)
            
        # Nút Download
        st.download_button(
            label="⬇️ Tải Video Về Máy",
            data=video_bytes,
            file_name="ai_generated_video.mp4",
            mime="video/mp4"
        )
        
    except Exception as e:
        st.error(f"Đã xảy ra lỗi: {e}")

# --- QUẢN LÝ TÀI NGUYÊN (ASSETS) ---
st.divider()
st.subheader("🗂️ Quản lý Bộ nhớ tạm (Assets)")
st.markdown("Mỗi lần tạo video, hệ thống sẽ sinh ra nhiều ảnh và file audio lẻ lưu ở thư mục `assets`. Bạn có thể quản lý trực tiếp tại đây.")

def get_dir_size(path='assets'):
    total = 0
    if os.path.exists(path):
        for f in os.listdir(path):
            fp = os.path.join(path, f)
            if os.path.isfile(fp):
                total += os.path.getsize(fp)
    return total

size_mb = get_dir_size() / (1024 * 1024)
st.write(f"**Dung lượng thư mục hiện tại:** {size_mb:.2f} MB")

col1, col2 = st.columns([1, 3])
with col1:
    if st.button("🗑️ Xóa TOÀN BỘ file rác"):
        import shutil
        if os.path.exists('assets'):
            shutil.rmtree('assets')
        os.makedirs('assets', exist_ok=True)
        st.success("Đã xóa sạch sẽ!")
        st.rerun()

# Trình quản lý chi tiết
if os.path.exists('assets'):
    assets_files = os.listdir('assets')
    if assets_files:
        with st.expander("🔍 Mở Trình quản lý File (Xem trước & Xóa lẻ)"):
            selected_files = st.multiselect("Chọn các file bạn muốn xóa riêng:", assets_files)
            if st.button("🗑️ Xóa các file đã chọn"):
                for f in selected_files:
                    os.remove(os.path.join('assets', f))
                st.success("Đã xóa!")
                st.rerun()
            
            st.markdown("---")
            st.markdown("### 🖼️ File của bạn:")
            
            # Chia làm 3 cột để hiển thị cho đẹp
            cols = st.columns(3)
            for i, f in enumerate(assets_files):
                col = cols[i % 3]
                fp = os.path.join('assets', f)
                with col:
                    if f.endswith('.png') or f.endswith('.jpg'):
                        st.image(fp, caption=f, use_container_width=True)
                    elif f.endswith('.mp3'):
                        st.audio(fp)
                        st.caption(f)

