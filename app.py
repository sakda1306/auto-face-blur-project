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
SAMPLE_IMAGE = Path(__file__).resolve().parent / "tests" / "data" / "portrait.jpg"
# Mascot logo. static/ is served at app/static/ (enableStaticServing in .streamlit/config.toml).
STATIC_DIR = Path(__file__).resolve().parent / "static"
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
    ("upload", "อัปโหลด", "ภาพของคุณ", f"รองรับ JPG และ PNG ขนาดไม่เกิน {MAX_FILE_MB} MB ภาพประมวลผลบนเครื่องนี้เท่านั้น"),
    ("tune", "เลือก", "โหมดเซ็นเซอร์", "Gaussian Blur, Mosaic หรือ BBox Only แล้วปรับความเข้มข้นที่แถบด้านซ้าย"),
    ("download", "ดาวน์โหลด", "ภาพผลลัพธ์", "ได้ไฟล์ PNG ที่เซ็นเซอร์ใบหน้าแล้ว พร้อมนำไปเผยแพร่อย่างปลอดภัย"),
]

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Prompt:ital,wght@0,400;0,500;0,600;0,700;1,400;1,500&family=IBM+Plex+Sans+Thai:wght@400;500;600&display=swap');

:root {
  --purple: #4B2AAD;
  --purple-2: #6A3FD1;
  --pink: #E5305B;
  --ink: #1F1B2E;
  --muted: #6B7280;
  --line: #E7E3F0;
  --font-head: 'Prompt', sans-serif;
  --font-body: 'IBM Plex Sans Thai', 'Prompt', sans-serif;
}
/* One font family across the whole page, Streamlit widgets included (icons excluded) */
.stApp, .stApp p, .stApp li, .stApp label, .stApp input, .stApp button, .stApp small,
.stApp [data-testid="stMarkdownContainer"], .stApp [data-testid="stCaptionContainer"],
.stApp [data-testid="stWidgetLabel"], .stApp [data-testid="stFileUploaderDropzoneInstructions"],
.stApp [data-testid="stSliderThumbValue"], .stApp [data-testid="stTickBarMin"], .stApp [data-testid="stTickBarMax"],
.stApp [data-testid="stMetricLabel"] {
  font-family: var(--font-body);
}
.stApp h1, .stApp h2, .stApp h3, [data-testid="stSidebar"] h2 { font-family: var(--font-head); font-weight: 600; }
.block-container { padding-top: 2.5rem; max-width: 1180px; position: relative; z-index: 1; }
header[data-testid="stHeader"] { background: transparent; }

/* Page background: soft lavender, faint dot grid, and two blurred glows drifting slowly */
.stApp { background: linear-gradient(180deg, #F7F4FE 0%, #FBF9FF 45%, #FFF6F8 100%); }
[data-testid="stMain"], [data-testid="stAppViewContainer"] > section:not([data-testid="stSidebar"]) {
  background-image: radial-gradient(rgba(75, 42, 173, .09) 1.2px, transparent 1.2px);
  background-size: 24px 24px;
}
[data-testid="stAppViewContainer"]::before, [data-testid="stAppViewContainer"]::after {
  content: ""; position: fixed; z-index: 0; pointer-events: none; border-radius: 50%;
  width: 560px; height: 560px; filter: blur(100px);
  animation: bg-drift 20s ease-in-out infinite alternate;
}
[data-testid="stAppViewContainer"]::before { background: #8B5CF6; opacity: .28; top: -160px; right: -140px; }
[data-testid="stAppViewContainer"]::after {
  background: #E5305B; opacity: .16; bottom: -200px; left: 18%; animation-delay: -10s;
}
@keyframes bg-drift {
  0% { transform: translate(0, 0) scale(1); }
  50% { transform: translate(-80px, 60px) scale(1.12); }
  100% { transform: translate(40px, -40px) scale(.95); }
}
@media (prefers-reduced-motion: reduce) {
  [data-testid="stAppViewContainer"]::before, [data-testid="stAppViewContainer"]::after { animation: none; }
}

/* Hero */
.hero {
  position: relative; overflow: hidden; text-align: center; color: #fff;
  background: linear-gradient(135deg, var(--purple), var(--purple-2));
  border-radius: 18px; padding: 52px 24px 0;
}
.hero-title {
  font-family: var(--font-head); font-weight: 700; letter-spacing: .03em;
  font-size: clamp(2rem, 5vw, 3.3rem); line-height: 1.15;
}
[data-testid="stSidebarHeader"] img, [data-testid="stLogo"] {
  height: 48px !important; width: auto; transform-origin: center bottom;
  animation: corner-logo 3.2s ease-in-out infinite;
  transition: transform .35s cubic-bezier(.3, 1.6, .5, 1);
}
[data-testid="stLogo"]:hover { animation-play-state: paused; transform: scale(1.15) rotate(-6deg); }
@keyframes corner-logo { 0%, 100% { transform: translateY(0) rotate(0); } 50% { transform: translateY(-3px) rotate(-3deg); } }
@media (prefers-reduced-motion: reduce) { [data-testid="stLogo"] { animation: none; } }
.hero-sub { font-family: var(--font-body); font-size: 1.15rem; opacity: .92; margin-top: 12px; }
.hero-cta {
  display: inline-block; margin-top: 26px; padding: 12px 30px; border-radius: 4px;
  background: var(--pink); color: #fff !important; text-decoration: none !important;
  font-family: var(--font-head); font-size: 1.05rem;
  box-shadow: 0 8px 20px rgba(229, 48, 91, .35);
}
.hero-cta:hover { filter: brightness(1.08); }
.hero-deco { position: absolute; color: #fff; opacity: .55; font-size: 28px; }
svg.hero-deco { width: 40px; height: 40px; fill: #fff; opacity: .4; }
@media (max-width: 640px) { .hero-deco { display: none; } }

/* Hero animation: floating cards, scan line, mosaic tiles popping in, moving arrow */
.hero-card, .hero-tile, .hero-scan, .hero-arrow { transform-box: fill-box; transform-origin: center; }
.hero-card { animation: hero-float 3s ease-in-out infinite; }
.hero-tile { animation: hero-tile 4s ease-out infinite; opacity: 0; }
.hero-scan { animation: hero-scan 4s ease-in-out infinite; opacity: 0; }
.hero-arrow { animation: hero-arrow 1.2s ease-in-out infinite; }
.hero-deco { animation: hero-twinkle 3s ease-in-out infinite; }
.hero-deco:nth-child(2) { animation-delay: .8s; }
.hero-deco:nth-child(3) { animation-delay: 1.6s; }
.hero-deco:nth-child(4) { animation-delay: 2.2s; }
@keyframes hero-float { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-6px); } }
@keyframes hero-scan {
  0% { opacity: 0; transform: translateY(0); }
  5% { opacity: 1; }
  25% { opacity: 1; transform: translateY(60px); }
  30%, 100% { opacity: 0; transform: translateY(60px); }
}
@keyframes hero-tile {
  0%, 25% { opacity: 0; transform: scale(.2); }
  35% { opacity: 1; transform: scale(1.15); }
  40%, 85% { opacity: 1; transform: scale(1); }
  100% { opacity: 0; transform: scale(1); }
}
@keyframes hero-arrow { 0%, 100% { transform: translateX(0); opacity: .7; } 50% { transform: translateX(6px); opacity: 1; } }
@keyframes hero-twinkle { 0%, 100% { opacity: .25; transform: scale(.9); } 50% { opacity: .7; transform: scale(1.1); } }
@media (prefers-reduced-motion: reduce) {
  .hero-card, .hero-scan, .hero-arrow, .hero-deco { animation: none; }
  .hero-tile { animation: none; opacity: 1; }
}
.hero svg { display: block; margin: 30px auto 0; max-width: 100%; height: auto; }

/* Section headings: black word + pink word */
.section-head { text-align: center; margin: 56px 0 28px; }
.section-head.compact { margin: 22px 0 16px; }
.section-head.compact .section-title { font-size: 1.6rem; }
.hero-compact {
  display: flex; align-items: baseline; justify-content: space-between; flex-wrap: wrap; gap: 4px 20px;
  text-align: left; padding: 18px 26px; border-radius: 14px; margin-bottom: 14px;
}
.hero-compact .hero-title { font-size: 1.5rem; letter-spacing: .03em; }
.hero-compact .hero-sub { margin: 0; font-size: .95rem; }
.section-title { font-family: var(--font-head); font-weight: 600; font-size: 2.1rem; color: var(--ink); }
.section-title span { color: var(--pink); }
.section-sub { color: var(--muted); font-size: 1.05rem; margin-top: 4px; }

/* How-it-works cards */
.steps { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 24px; align-items: start; }
.step {
  position: relative; background: #fff; border: 1px solid var(--line); border-radius: 6px;
  padding: 30px 28px 28px; box-shadow: 0 6px 24px rgba(31, 27, 46, .05);
}
.step.featured { border-color: var(--pink); box-shadow: 0 12px 32px rgba(229, 48, 91, .14); }
.step-icon { position: absolute; top: 20px; right: 20px; width: 72px; height: 72px; fill: #9CA3AF; opacity: .3; }
.step.featured .step-icon { fill: var(--pink); opacity: .18; }
.step-title, .step-em { padding-right: 72px; }
.step-title { font-family: var(--font-head); font-weight: 600; font-size: 1.45rem; color: var(--ink); }
.step-em { font-family: var(--font-head); font-style: italic; font-size: 1.3rem; color: var(--ink); }
.step.featured .step-title, .step.featured .step-em { color: var(--pink); }
.step-line { width: 32px; height: 3px; background: var(--pink); margin: 20px 0; }
.step-text { color: var(--muted); line-height: 1.85; }
@media (min-width: 900px) { .step:nth-child(2) { margin-top: 36px; } }

/* Hover: card lifts, turns pink, icon grows, accent line stretches */
.step, .step-icon, .step-title, .step-em, .step-line {
  transition: all .35s cubic-bezier(.2, .8, .2, 1);
}
.step:hover {
  transform: translateY(-10px); border-color: var(--pink);
  box-shadow: 0 22px 44px rgba(229, 48, 91, .18);
}
.step:hover .step-icon { fill: var(--pink); opacity: .3; transform: scale(1.15) rotate(-6deg); }
.step:hover .step-title, .step:hover .step-em { color: var(--pink); }
.step:hover .step-line { width: 64px; }
/* While one card is hovered, the others step back so it stands out */
.steps:hover .step:not(:hover) { opacity: .75; }
.steps:hover .step.featured:not(:hover) {
  border-color: var(--line); box-shadow: 0 6px 24px rgba(31, 27, 46, .05);
}
.steps:hover .step.featured:not(:hover) .step-title,
.steps:hover .step.featured:not(:hover) .step-em { color: var(--ink); }
.steps:hover .step.featured:not(:hover) .step-icon { fill: #9CA3AF; }

.hero-cta { transition: transform .25s ease, box-shadow .25s ease; }
.hero-cta:hover { transform: translateY(-3px); box-shadow: 0 14px 28px rgba(229, 48, 91, .45); }
/* Uploader: big centered drop card with a flowing purple-pink border */
[data-testid="stFileUploaderDropzone"] {
  position: relative; border: 2px solid transparent; border-radius: 18px;
  background:
    linear-gradient(180deg, #FFFFFF, #FDFBFF) padding-box,
    linear-gradient(90deg, #6A3FD1, #E5305B, #8B5CF6, #E5305B, #6A3FD1) border-box;
  background-size: 100% 100%, 300% 100%;
  animation: upload-border 6s linear infinite;
  box-shadow: 0 10px 30px rgba(75, 42, 173, .08);
  transition: transform .3s ease, box-shadow .3s ease;
}
[data-testid="stFileUploaderDropzone"]:hover {
  transform: translateY(-4px); box-shadow: 0 22px 48px rgba(229, 48, 91, .2);
}
/* Empty state only (while the instructions are shown): stack icon, text and button */
[data-testid="stFileUploaderDropzone"]:has([data-testid="stFileUploaderDropzoneInstructions"]) {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 12px; min-height: 260px; padding: 32px 20px; text-align: center;
}
[data-testid="stFileUploaderDropzone"]:has([data-testid="stFileUploaderDropzoneInstructions"])::before {
  content: ""; order: -2; width: 76px; height: 76px; border-radius: 50%;
  background:
    url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='%23fff' d='M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM14 13v4h-4v-4H7l5-5 5 5h-3z'/%3E%3C/svg%3E")
      center / 38px no-repeat,
    linear-gradient(135deg, #6A3FD1, #E5305B);
  box-shadow: 0 12px 26px rgba(229, 48, 91, .35);
  animation: upload-bob 2.4s ease-in-out infinite;
}
[data-testid="stFileUploaderDropzone"]:has([data-testid="stFileUploaderDropzoneInstructions"])::after {
  content: "ลากภาพมาวางที่นี่ หรือ"; order: -1;
  font-family: var(--font-head); font-size: 1.25rem; font-weight: 600; color: var(--ink);
}
[data-testid="stFileUploaderDropzone"]:hover::before { animation-duration: .9s; }
[data-testid="stFileUploaderDropzoneInstructions"] { order: 1; }
[data-testid="stFileUploaderDropzone"]:has([data-testid="stFileUploaderDropzoneInstructions"]) button {
  background: linear-gradient(135deg, #6A3FD1, #E5305B) !important; color: #fff !important;
  border: none !important; border-radius: 999px !important; padding: .55rem 1.6rem !important;
  font-family: var(--font-head); box-shadow: 0 8px 18px rgba(229, 48, 91, .3);
  transition: transform .25s ease, box-shadow .25s ease;
}
[data-testid="stFileUploaderDropzone"]:has([data-testid="stFileUploaderDropzoneInstructions"]) button:hover {
  transform: translateY(-2px) scale(1.04); box-shadow: 0 14px 26px rgba(229, 48, 91, .4);
}
@keyframes upload-border { to { background-position: 0 0, 300% 0; } }
@keyframes upload-bob { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-8px); } }
@media (prefers-reduced-motion: reduce) {
  [data-testid="stFileUploaderDropzone"], [data-testid="stFileUploaderDropzone"]::before { animation: none !important; }
}

/* Results */
[data-testid="stMetric"] {
  background: #fff; border: 1px solid var(--line); border-left: 4px solid var(--pink);
  border-radius: 6px; padding: 14px 20px;
}
[data-testid="stMetricValue"] { font-family: var(--font-head); color: var(--purple); }
.st-key-before, .st-key-after {
  background: #fff; border: 1px solid var(--line); border-radius: 6px; padding: 18px;
  box-shadow: 0 6px 24px rgba(31, 27, 46, .05);
}
.st-key-after { border-color: var(--pink); }
[data-testid="stMetric"], .st-key-before, .st-key-after {
  transition: transform .3s ease, box-shadow .3s ease;
}
[data-testid="stMetric"]:hover, .st-key-before:hover, .st-key-after:hover {
  transform: translateY(-4px); box-shadow: 0 16px 34px rgba(75, 42, 173, .12);
}
.img-label { font-family: var(--font-head); font-weight: 600; font-size: 1.2rem; color: var(--ink); }
.img-label span { color: var(--pink); font-style: italic; font-weight: 400; margin-left: 6px; }
.stDownloadButton button {
  font-family: var(--font-head); padding: .7rem 1rem; border-radius: 4px;
  transition: transform .25s ease, box-shadow .25s ease;
}
.stDownloadButton button:hover { transform: translateY(-3px); box-shadow: 0 14px 28px rgba(229, 48, 91, .35); }

/* Sidebar hide/show buttons: always visible (Streamlit shows them only on hover) */
[data-testid="stSidebarCollapseButton"] {
  display: inline-flex !important; visibility: visible !important; opacity: 1 !important;
}
[data-testid="stSidebarCollapseButton"] button,
[data-testid="stExpandSidebarButton"],
[data-testid="stSidebarCollapsedControl"] button {
  color: var(--pink) !important; background: #fff !important;
  border: 1px solid var(--line) !important; border-radius: 8px !important;
  box-shadow: 0 4px 12px rgba(31, 27, 46, .08);
  transition: transform .2s ease, box-shadow .2s ease;
}
[data-testid="stSidebarCollapseButton"] button:hover,
[data-testid="stExpandSidebarButton"]:hover,
[data-testid="stSidebarCollapsedControl"] button:hover {
  transform: scale(1.08); box-shadow: 0 8px 18px rgba(229, 48, 91, .25);
}

/* Example cards */
[class*="st-key-ex_"] {
  background: #fff; border: 1px solid var(--line); border-radius: 10px; padding: 18px;
  box-shadow: 0 6px 24px rgba(31, 27, 46, .05);
  transition: transform .35s cubic-bezier(.2, .8, .2, 1), box-shadow .35s ease, border-color .35s ease;
}
[class*="st-key-ex_"]:hover {
  transform: translateY(-8px); border-color: var(--pink); box-shadow: 0 22px 44px rgba(229, 48, 91, .18);
}
[class*="st-key-ex_"] img { border-radius: 8px; transition: transform .5s ease; }
[class*="st-key-ex_"]:hover img { transform: scale(1.04); }
[class*="st-key-ex_"] [data-testid="stImage"] { overflow: hidden; border-radius: 8px; }
.ex-hint { color: var(--muted); font-size: .92rem; margin: 2px 0 4px; }

/* Mascot in the bottom-right corner with a privacy fact card */
.mascot { position: fixed; right: 22px; bottom: 18px; z-index: 999990; outline: none; }
.mascot-fox {
  width: 118px; height: 118px; display: block; cursor: pointer;
  filter: drop-shadow(0 10px 18px rgba(31, 27, 46, .25));
  animation: mascot-float 3.2s ease-in-out infinite;
  transition: transform .35s cubic-bezier(.3, 1.6, .5, 1);
}
.mascot:hover .mascot-fox, .mascot:focus-within .mascot-fox { transform: scale(1.1) rotate(-5deg); animation-play-state: paused; }
.mascot-bubble {
  position: absolute; right: 112px; bottom: 98px; white-space: nowrap;
  background: #fff; color: var(--ink); font-family: var(--font-head); font-size: .9rem;
  padding: 7px 14px; border-radius: 16px 16px 4px 16px; border: 1px solid var(--line);
  box-shadow: 0 8px 20px rgba(75, 42, 173, .15);
  animation: mascot-pulse 2.4s ease-in-out infinite; transition: opacity .25s ease;
}
.mascot:hover .mascot-bubble, .mascot:focus-within .mascot-bubble { opacity: 0; }
.mascot-card {
  position: absolute; right: 0; bottom: calc(100% + 2px); width: 380px; max-height: 72vh;
  display: flex; flex-direction: column; overflow: hidden;
  background: #fff; border-radius: 18px; border: 1px solid var(--line);
  box-shadow: 0 28px 60px rgba(31, 27, 46, .22);
  opacity: 0; visibility: hidden; transform: translateY(14px) scale(.94); transform-origin: bottom right;
  transition: opacity .3s ease, transform .35s cubic-bezier(.2, .8, .2, 1), visibility .3s;
}
.mascot-card::after { content: ""; position: absolute; left: 0; right: 0; top: 100%; height: 12px; }
.mascot:hover .mascot-card, .mascot:focus-within .mascot-card { opacity: 1; visibility: visible; transform: none; }
.mascot-head {
  font-family: var(--font-head); font-weight: 600; font-size: 1.2rem; color: #fff;
  padding: 16px 20px; background: linear-gradient(135deg, var(--purple), var(--pink));
}
.mascot-body { padding: 14px 20px 16px; overflow-y: auto; font-family: var(--font-body); }
.mascot-body ul { margin: 6px 0 12px; padding-left: 18px; }
.mascot-body li { color: #4B5563; font-size: .9rem; line-height: 1.6; margin-bottom: 6px; }
.mascot-body li::marker { color: var(--pink); }
.mascot-body b { color: var(--ink); font-weight: 600; }
.mascot-why li { color: var(--ink); }
.mascot-tag {
  display: inline-block; font-family: var(--font-head); font-size: .8rem; font-weight: 600;
  color: var(--pink); background: #FFEAF0; padding: 3px 12px; border-radius: 999px; margin-top: 4px;
}
.mascot-note { color: var(--muted); font-size: .78rem; border-top: 1px solid var(--line); padding-top: 10px; }
@keyframes mascot-float { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-6px); } }
@keyframes mascot-pulse { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.05); } }
@media (max-width: 640px) {
  .mascot-fox { width: 84px; height: 84px; }
  .mascot-bubble { display: none; }
  .mascot-card { width: calc(100vw - 32px); right: -6px; }
}
@media (prefers-reduced-motion: reduce) { .mascot-fox, .mascot-bubble { animation: none; } }

/* Controls bar above the result */
.st-key-controls {
  background: #fff; border: 1px solid var(--line); border-radius: 14px; padding: 14px 22px 6px;
  margin-bottom: 14px; box-shadow: 0 8px 26px rgba(75, 42, 173, .08);
}
.st-key-controls [data-testid="stWidgetLabel"] p { font-family: var(--font-head); font-weight: 500; }
.st-key-controls button[kind^="segmented_control"] { font-family: var(--font-head); transition: transform .2s ease; }
.st-key-controls button[kind^="segmented_control"]:hover { transform: translateY(-2px); }

.footer { text-align: center; color: var(--muted); font-size: .9rem; margin: 56px 0 8px; }
</style>
"""


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


def encode_png(image):
    ok, buffer = cv2.imencode(".png", image)
    if not ok:
        raise RuntimeError("cannot encode image as PNG")
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
st.markdown(CSS, unsafe_allow_html=True)
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
    st.caption(":material/lock: ภาพประมวลผลบนเครื่องนี้เท่านั้น ไม่ถูกเก็บหรือส่งต่อ")


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
    section_head("เริ่ม", "เซ็นเซอร์ภาพ", "ภาพของคุณจะถูกประมวลผลบนเครื่องนี้เท่านั้น", anchor="upload")

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

st.download_button(
    "ดาวน์โหลดภาพผลลัพธ์ (PNG)",
    data=encode_png(result),
    file_name=f"{Path(file_name).stem}_blurred.png",
    mime="image/png",
    type="primary",
    icon=":material/download:",
    width="stretch",
)
show_footer()
