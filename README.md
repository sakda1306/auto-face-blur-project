# Auto Face Blur

Mini Project — Image and Audio Processing (Computer Vision)

ระบบตรวจจับและเซ็นเซอร์ใบหน้าในภาพนิ่ง วิดีโอ และกล้อง Webcam โดยอัตโนมัติ เพื่อคุ้มครองความเป็นส่วนตัว (PDPA)

## Features
- ตรวจจับใบหน้าได้หลายใบหน้าพร้อมกัน (Multi-face Detection)
- เซ็นเซอร์ได้ 2 แบบ: Gaussian Blur และ Pixelation (Mosaic)
- ปรับระดับความเบลอผ่าน Slider
- รองรับการอัปโหลดภาพและกล้อง Webcam แบบ Real-time

## Project Structure
```text
├── docs/             # Contract, Git Flow, Schedule
├── test_images/      # ภาพสำหรับทดสอบ
├── detector.py       # ตรวจจับใบหน้าและฟังก์ชันเบลอ/โมเสก
├── webcam_demo.py    # รันผ่านกล้องสดแบบ Real-time
├── app.py            # หน้าเว็บ UI ด้วย Streamlit
└── requirements.txt
```

## Setup
```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

## Run
```bash
streamlit run app.py          # Web App (Image + Live Webcam)
python webcam_demo.py         # (optional) ทดสอบกล้องบนเครื่องโดยไม่ผ่านเว็บ
```

## Docs
- [Contract](docs/CONTRACT.md): สถาปัตยกรรม, API ของ `detector.py`, UI, Test
- [Git Flow](docs/GIT_FLOW.md): Branch, Commit, Pull Request
- [Schedule](docs/SCHEDULE.md): แบ่งงาน 4 คน, ตารางเวลา 2 วัน, Checklist

## Git Workflow
- `main` — โค้ดที่พร้อมส่ง/นำเสนอ
- `develop` — branch หลักสำหรับรวมงาน (default)
- `feature/<ชื่องาน>` — แตกจาก `develop` แล้วเปิด Pull Request กลับเข้า `develop` (รายละเอียดใน [GIT_FLOW.md](docs/GIT_FLOW.md))

## Team
| ชื่อ | รหัสนักศึกษา | หน้าที่ |
|------|--------------|---------|
|      |              |         |
|      |              |         |
|      |              |         |
|      |              |         |
