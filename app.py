"""Streamlit web UI for Auto Face Blur (image upload only). See docs/CONTRACT.md section 4."""

from html import escape
from pathlib import Path

import cv2
import numpy as np
import streamlit as st

from detector import blur_faces

# Radio label -> mode passed to blur_faces (CONTRACT.md 4.1).
MODES = {
    "Gaussian Blur": "blur",
    "Mosaic": "mosaic",
    "BBox Only": "bbox",
}
MODE_HINTS = [
    "เบลอนุ่มแบบเลนส์หลุดโฟกัส",
    "แตกเป็นบล็อกสี่เหลี่ยมแบบเซ็นเซอร์ทีวี",
    "วาดกรอบอย่างเดียว ใช้เช็คการตรวจจับ",
]
DEFAULT_STRENGTH = 50
MAX_FILE_MB = 5
# static/ is served at app/static/ (enableStaticServing in .streamlit/config.toml).
STATIC_DIR = Path(__file__).resolve().parent / "static"
STYLE = STATIC_DIR / "style.css"
SAMPLE_IMAGE = STATIC_DIR / "sample.jpg"
LOGO_ANIMATED = STATIC_DIR / "fox.webp"
LOGO_STILL = STATIC_DIR / "fox.png"

# Material Design icon paths (Apache 2.0), inlined so icons work without loading a web font.
ICONS = {
    "upload": "M9 16h6v-6h4l-7-7-7 7h4zm-4 2h14v2H5z",
    "tune": "M3 17v2h6v-2H3zM3 5v2h10V5H3zm10 16v-2h8v-2h-8v-2h-2v6h2zM7 9v2H3v2h4v2h2V9H7zm14 4v-2H11v2h10zm-6-4h2V7h4V5h-4V3h-2v6z",
    "download": "M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z",
    "visibility_off": "M12 7c2.76 0 5 2.24 5 5 0 .65-.13 1.26-.36 1.83l2.92 2.92c1.51-1.26 2.7-2.89 3.43-4.75-1.73-4.39-6-7.5-11-7.5-1.4 0-2.74.25-3.98.7l2.16 2.16C10.74 7.13 11.35 7 12 7zM2 4.27l2.28 2.28.46.46C3.08 8.3 1.78 10.02 1 12c1.73 4.39 6 7.5 11 7.5 1.55 0 3.03-.3 4.38-.84l.42.42L19.73 22 21 20.73 3.27 3 2 4.27zM7.53 9.8l1.55 1.55c-.05.21-.08.43-.08.65 0 1.66 1.34 3 3 3 .22 0 .44-.03.65-.08l1.55 1.55c-.67.33-1.41.53-2.2.53-2.76 0-5-2.24-5-5 0-.79.2-1.53.53-2.2zm4.31-.78l3.15 3.15.02-.16c0-1.66-1.34-3-3-3l-.17.01z",
    "shield": "M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4z",
}


def icon(name, css_class, style=""):
    style_attr = f' style="{style}"' if style else ""
    return (
        f'<svg class="{css_class}"{style_attr} viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">'
        f'<path d="{ICONS[name]}"/></svg>'
    )


# (icon, title, italic subtitle, text) for the "how it works" cards.
STEPS = [
    ("upload", "อัปโหลด", "ภาพของคุณ", f"รองรับ JPG และ PNG ขนาดไม่เกิน {MAX_FILE_MB} MB ภาพไม่ถูกบันทึกหรือส่งต่อ"),
    ("tune", "เลือก", "โหมดเซ็นเซอร์", "Gaussian Blur, Mosaic หรือ BBox Only แล้วปรับความเข้มข้นที่แถบด้านซ้าย"),
    ("download", "ดาวน์โหลด", "ภาพผลลัพธ์", "ได้ไฟล์ PNG ที่เซ็นเซอร์ใบหน้าแล้ว พร้อมนำไปเผยแพร่อย่างปลอดภัย"),
]



def hero_illustration():
    """Animated inline SVG: a face on the left, the same face being pixelated on the right.

    The right card shows the face, a pink scan line sweeps over it, then the mosaic
    tiles pop in one by one, hold, and fade out (see the hero animation CSS).
    """
    def face(x0):
        return (
            f'<circle cx="{x0 + 70}" cy="85" r="30" fill="#F6C9A8"/>'
            f'<circle cx="{x0 + 60}" cy="82" r="3" fill="#1F1B2E"/>'
            f'<circle cx="{x0 + 80}" cy="82" r="3" fill="#1F1B2E"/>'
            f'<path d="M{x0 + 60} 96 Q{x0 + 70} 104 {x0 + 80} 96" stroke="#1F1B2E" '
            'stroke-width="2.5" fill="none" stroke-linecap="round"/>'
        )

    def card(x0, extra, delay):
        return (
            f'<g class="hero-card" style="animation-delay:{delay}s">'
            f'<rect x="{x0}" y="20" width="140" height="150" rx="14" fill="#fff"/>'
            f'<rect x="{x0 + 10}" y="30" width="120" height="140" rx="8" fill="#EDE7FB"/>'
            f'<path d="M{x0 + 22} 170 Q{x0 + 70} 112 {x0 + 118} 170 Z" fill="#6A3FD1"/>'
            f"{face(x0)}{extra}</g>"
        )

    shades = ["#F6C9A8", "#E9B48F", "#D99C79", "#F2BFA0", "#E3A887"]
    tiles = "".join(
        f'<rect class="hero-tile" x="{280 + col * 12}" y="{55 + row * 12}" width="12" height="12" '
        f'fill="{shades[(row * 2 + col * 3) % len(shades)]}" style="animation-delay:{(row * 5 + col) * 0.04:.2f}s"/>'
        for row in range(5)
        for col in range(5)
    )
    scan = '<rect class="hero-scan" x="276" y="52" width="68" height="3" rx="1.5" fill="#E5305B"/>'
    arrow = (
        '<g class="hero-arrow"><path d="M196 95 H228 M218 84 L230 95 L218 106" stroke="#fff" '
        'stroke-width="4" fill="none" stroke-linecap="round" stroke-linejoin="round"/></g>'
    )
    return (
        '<svg viewBox="0 0 420 170" width="420" xmlns="http://www.w3.org/2000/svg">'
        + card(40, "", 0) + arrow + card(240, tiles + scan, -1.5) + "</svg>"
    )


def section_head(plain, accent, sub, anchor="", compact=False):
    anchor_attr = f' id="{anchor}"' if anchor else ""
    css = "section-head compact" if compact else "section-head"
    st.markdown(
        f'<div class="{css}"{anchor_attr}><div class="section-title">{plain}<span>{accent}</span></div>'
        f'<div class="section-sub">{sub}</div></div>',
        unsafe_allow_html=True,
    )


def show_hero():
    deco = (
        '<span class="hero-deco" style="top:34px;left:6%">✦</span>'
        '<span class="hero-deco" style="top:58px;right:8%">✦</span>'
        + icon("visibility_off", "hero-deco", "top:180px;left:10%")
        + icon("shield", "hero-deco", "top:200px;right:12%")
    )
    st.markdown(
        f'<div class="hero">{deco}'
        '<div class="hero-title">AUTO FACE BLUR</div>'
        '<div class="hero-sub">เซ็นเซอร์ใบหน้าในภาพอัตโนมัติ คุ้มครองความเป็นส่วนตัวตาม PDPA</div>'
        '<a class="hero-cta" href="#upload">เริ่มใช้งาน</a>'
        f"{hero_illustration()}</div>",
        unsafe_allow_html=True,
    )


def show_hero_compact():
    """Slim header used once an image is loaded, so the result sits near the top."""
    st.markdown(
        '<div class="hero hero-compact"><div class="hero-title">AUTO FACE BLUR</div>'
        '<div class="hero-sub">เซ็นเซอร์ใบหน้าในภาพอัตโนมัติ คุ้มครองความเป็นส่วนตัวตาม PDPA</div></div>',
        unsafe_allow_html=True,
    )


def show_steps():
    cards = "".join(
        f'<div class="step{" featured" if i == 0 else ""}">'
        f'{icon(name, "step-icon")}'
        f'<div class="step-title">{title}</div><div class="step-em">{em}</div>'
        f'<div class="step-line"></div><div class="step-text">{text}</div></div>'
        for i, (name, title, em, text) in enumerate(STEPS)
    )
    section_head("วิธี", "ใช้งาน ?", "ครบในสามขั้นตอน ไม่ต้องติดตั้งอะไรเพิ่ม")
    st.markdown(f'<div class="steps">{cards}</div>', unsafe_allow_html=True)


@st.cache_data(max_entries=24, show_spinner=False)
def process(data, mode, strength):
    """Decode the uploaded bytes and run blur_faces. Cached, so switching tabs or moving
    the slider back to an earlier value does not run face detection again."""
    return blur_faces(decode_upload(data), mode, strength)


def decode_upload(data):
    """Decode uploaded bytes into a BGR image, or None if the file is not a valid image.

    IMREAD_COLOR also applies the EXIF orientation, so phone photos are not sideways.
    """
    return cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)


def to_rgb(image):
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def encode_image(image, extension):
    """Encode a BGR image as PNG or JPG bytes. A PNG of a phone photo can be 20-40 MB."""
    params = [cv2.IMWRITE_JPEG_QUALITY, 92] if extension == ".jpg" else []
    ok, buffer = cv2.imencode(extension, image, params)
    if not ok:
        raise RuntimeError(f"cannot encode image as {extension}")
    return buffer.tobytes()


def use_sample(on):
    st.session_state["use_sample"] = on


@st.cache_data(show_spinner=False)
def example_results():
    """The sample image through every mode, cropped to head and shoulders (RGB)."""
    image = cv2.imread(str(SAMPLE_IMAGE))
    height, width = image.shape[:2]
    crop = (slice(0, int(height * 0.55)), slice(int(width * 0.12), int(width * 0.88)))
    return {
        label: to_rgb(blur_faces(image, mode, DEFAULT_STRENGTH)[0][crop])
        for label, mode in MODES.items()
    }


def show_examples():
    if not SAMPLE_IMAGE.exists():
        return
    section_head("ตัวอย่าง", "ผลลัพธ์", f"ภาพเดียวกันผ่านทั้ง 3 โหมด ที่ความเข้มข้น {DEFAULT_STRENGTH}")
    for column, (label, image), hint in zip(st.columns(3, gap="medium"), example_results().items(), MODE_HINTS):
        with column, st.container(key=f"ex_{MODES[label]}"):
            st.markdown(f'<div class="img-label">{label}</div><div class="ex-hint">{hint}</div>',
                        unsafe_allow_html=True)
            st.image(image, width="stretch")
    _, middle, _ = st.columns([1, 1, 1])
    middle.button("ลองใช้ภาพตัวอย่างนี้", type="primary", icon=":material/photo_camera:",
                  on_click=use_sample, args=(True,), width="stretch")


# Hover card content (general information, checked against sources on 17 Oct 2026).
MASCOT_WHY = [
    "ใบหน้าระบุตัวตนได้ทันที ภาพที่เห็นหน้าชัดจึงนับเป็น <b>ข้อมูลส่วนบุคคล</b>",
    "ลดความเสี่ยงถูกนำภาพไปใช้ผิด เช่น ระบบจดจำใบหน้า การติดตามตัว หรือ Deepfake",
    "เผยแพร่ภาพข่าว รีวิว หรืองานวิจัยได้ โดยไม่ละเมิดคนที่ไม่ได้ยินยอม",
]
MASCOT_TH = [
    "<b>PDPA</b> (พ.ร.บ.คุ้มครองข้อมูลส่วนบุคคล พ.ศ. 2562) บังคับใช้เต็มรูปแบบ 1 มิ.ย. 2565",
    "ภาพใบหน้าเป็นข้อมูลส่วนบุคคล ส่วนข้อมูลชีวภาพที่ใช้จดจำใบหน้าเป็น <b>ข้อมูลอ่อนไหว</b> คุ้มครองเข้มกว่า",
    "องค์กรที่เก็บหรือเผยแพร่ภาพต้องมีฐานทางกฎหมาย เช่น ได้รับความยินยอม",
    "โทษปรับทางปกครองสูงสุด <b>5 ล้านบาท</b> โทษอาญาจำคุกสูงสุด 1 ปี และค่าสินไหมเพิ่มได้ถึง 2 เท่า",
]
MASCOT_WORLD = [
    "<b>EU · GDPR</b> ภาพคนที่ระบุตัวได้คือข้อมูลส่วนบุคคล ปรับสูงสุด €20 ล้าน หรือ 4% ของรายได้ทั่วโลก",
    "<b>เยอรมนี</b> ต้องได้รับความยินยอมก่อนเผยแพร่ภาพบุคคล (มีข้อยกเว้น เช่น ข่าวหรือฝูงชน)",
    "<b>สหรัฐฯ</b> ไม่มีกฎหมายกลาง แต่บางรัฐคุมข้อมูลชีวภาพเข้ม เช่น BIPA ของรัฐอิลลินอยส์",
    "<b>Google Street View</b> เบลอใบหน้าและป้ายทะเบียนอัตโนมัติด้วยเหตุผลเดียวกัน",
]


def show_mascot():
    """Fox mascot fixed in the bottom-right corner; hover (or tap) opens a privacy fact card."""
    if not LOGO_ANIMATED.exists():
        return

    def items(rows):
        return "".join(f"<li>{row}</li>" for row in rows)

    st.markdown(
        '<div class="mascot" tabindex="0" aria-label="ทำไมต้องเบลอหน้า">'
        '<div class="mascot-card" role="tooltip">'
        '<div class="mascot-head">ทำไมต้องเบลอหน้า?</div>'
        f'<div class="mascot-body"><ul class="mascot-why">{items(MASCOT_WHY)}</ul>'
        f'<div class="mascot-tag">กฎหมายไทย</div><ul>{items(MASCOT_TH)}</ul>'
        f'<div class="mascot-tag">ต่างประเทศ</div><ul>{items(MASCOT_WORLD)}</ul>'
        '<div class="mascot-note">ข้อมูลทั่วไปเพื่อการศึกษา ไม่ใช่คำปรึกษาทางกฎหมาย</div></div></div>'
        '<div class="mascot-bubble">รู้ไหม? ทำไมต้องเบลอหน้า</div>'
        '<img class="mascot-fox" src="app/static/fox.webp" alt="น้องจิ้งจอก"></div>',
        unsafe_allow_html=True,
    )


def show_footer():
    st.markdown(
        '<div class="footer">Auto Face Blur · Mini Project วิชา Image and Audio Processing</div>',
        unsafe_allow_html=True,
    )


st.set_page_config(
    page_title="Auto Face Blur",
    page_icon=str(LOGO_STILL) if LOGO_STILL.exists() else "🙈",
    layout="wide",
)
# Corner logo: the animated fox (falls back to the still one). The tab icon stays still,
# because browsers do not animate favicons.
corner_logo = LOGO_ANIMATED if LOGO_ANIMATED.exists() else LOGO_STILL
if corner_logo.exists():
    st.logo(str(corner_logo), size="large")
st.markdown(f"<style>{STYLE.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
show_mascot()

# --- Controls ---
# Mode and strength live in shared session keys. The sidebar (CONTRACT.md 4.1) and the bar
# above the result are two views of the same setting: each widget copies its value into the
# shared key when changed, and every run copies the shared value back into both widgets.
st.session_state.setdefault("mode_label", list(MODES)[0])
st.session_state.setdefault("strength", DEFAULT_STRENGTH)


def sync(widget_key, shared_key):
    value = st.session_state.get(widget_key)
    if value is not None:  # a segmented control can be clicked off; keep the last mode then
        st.session_state[shared_key] = value


for widget_key in ("sb_mode", "top_mode"):
    st.session_state[widget_key] = st.session_state["mode_label"]
for widget_key in ("sb_strength", "top_strength"):
    st.session_state[widget_key] = st.session_state["strength"]

mode_label = st.session_state["mode_label"]
mode = MODES[mode_label]
# bbox mode ignores strength, but blur_faces still rejects values outside 1-100.
strength = DEFAULT_STRENGTH if mode == "bbox" else st.session_state["strength"]

# --- Sidebar (CONTRACT.md 4.1) ---
with st.sidebar:
    st.header(":material/settings: ตั้งค่า")
    st.radio("รูปแบบการเซ็นเซอร์", list(MODES), captions=MODE_HINTS,
             key="sb_mode", on_change=sync, args=("sb_mode", "mode_label"))
    if mode != "bbox":
        st.slider("ความเข้มข้น", min_value=1, max_value=100,
                  key="sb_strength", on_change=sync, args=("sb_strength", "strength"))
    st.divider()
    st.caption(":material/lock: ภาพใช้ประมวลผลชั่วคราวเท่านั้น ไม่ถูกบันทึกหรือส่งต่อ")


def show_controls():
    """Mode and strength right above the result, synced with the sidebar."""
    with st.container(key="controls"):
        left, right = st.columns([3, 2], gap="large", vertical_alignment="center")
        left.segmented_control(
            "รูปแบบการเซ็นเซอร์", list(MODES), key="top_mode",
            on_change=sync, args=("top_mode", "mode_label"), width="stretch",
        )
        right.slider(
            "ความเข้มข้น", min_value=1, max_value=100, key="top_strength",
            on_change=sync, args=("top_strength", "strength"), disabled=mode == "bbox",
            help="โหมด BBox Only ไม่ใช้ค่าความเข้มข้น" if mode == "bbox" else None,
        )


# With an image loaded (uploaded or sample), shrink the header so the result is near the top.
has_image = st.session_state.get("uploader") is not None or (
    st.session_state.get("use_sample", False) and SAMPLE_IMAGE.exists()
)
if has_image:
    show_hero_compact()
else:
    show_hero()
    section_head("เริ่ม", "เซ็นเซอร์ภาพ", "ภาพใช้ประมวลผลชั่วคราว ไม่ถูกบันทึกหรือส่งต่อ", anchor="upload")

# --- Upload (CONTRACT.md 4.2) ---
uploaded = st.file_uploader(
    f"อัปโหลดภาพ (JPG/PNG, ไม่เกิน {MAX_FILE_MB} MB)",
    type=["jpg", "jpeg", "png"],
    label_visibility="collapsed",
    key="uploader",
)
if uploaded is not None:
    st.session_state["use_sample"] = False
    file_name, file_size, data = uploaded.name, uploaded.size, uploaded.getvalue()
elif st.session_state.get("use_sample") and SAMPLE_IMAGE.exists():
    file_name, data = SAMPLE_IMAGE.name, SAMPLE_IMAGE.read_bytes()
    file_size = len(data)
else:
    show_examples()
    show_steps()
    show_footer()
    st.stop()

if file_size > MAX_FILE_MB * 1024 * 1024:
    st.error(f"ไฟล์ใหญ่เกิน {MAX_FILE_MB} MB กรุณาเลือกภาพที่เล็กกว่านี้")
    st.stop()

original = decode_upload(data)
if original is None:
    st.error("เปิดไฟล์นี้ไม่ได้ ไฟล์อาจเสียหายหรือไม่ใช่ภาพ JPG/PNG")
    st.stop()

with st.spinner("กำลังตรวจจับใบหน้า..."):
    result, face_count = process(data, mode, strength)

# --- Result ---
section_head("ผล", "ลัพธ์", escape(file_name), compact=True)
if uploaded is None:
    note, back = st.columns([4, 1], vertical_alignment="center")
    note.caption(":material/info: กำลังใช้ภาพตัวอย่าง อัปโหลดภาพของคุณเองได้ที่กล่องด้านบน")
    back.button("ปิดภาพตัวอย่าง", icon=":material/close:", on_click=use_sample, args=(False,), width="stretch")
height, width = original.shape[:2]
show_controls()
faces_col, mode_col, size_col = st.columns(3)
faces_col.metric("จำนวนใบหน้าที่พบ", face_count)
mode_col.metric("โหมด", mode_label)
size_col.metric("ขนาดภาพ", f"{width}×{height}")

if face_count == 0:
    st.info("ไม่พบใบหน้าในภาพ")

before, after = st.columns(2, gap="medium")
with before, st.container(key="before"):
    st.markdown('<div class="img-label">Before<span>ต้นฉบับ</span></div>', unsafe_allow_html=True)
    st.image(to_rgb(original), width="stretch")
with after, st.container(key="after"):
    st.markdown(f'<div class="img-label">After<span>{mode_label}</span></div>', unsafe_allow_html=True)
    st.image(to_rgb(result), width="stretch")

png_col, jpg_col = st.columns(2)
png_col.download_button(
    "ดาวน์โหลด PNG (คุณภาพเต็ม)",
    data=encode_image(result, ".png"),
    file_name=f"{Path(file_name).stem}_blurred.png",
    mime="image/png",
    type="primary",
    icon=":material/download:",
    width="stretch",
)
jpg_col.download_button(
    "ดาวน์โหลด JPG (ไฟล์เล็ก)",
    data=encode_image(result, ".jpg"),
    file_name=f"{Path(file_name).stem}_blurred.jpg",
    mime="image/jpeg",
    icon=":material/download:",
    width="stretch",
)
show_footer()
