# Auto Face Blur

Mini Project — Image and Audio Processing (Computer Vision)

Web App ตรวจจับและเซ็นเซอร์ใบหน้าในภาพที่ผู้ใช้อัปโหลดโดยอัตโนมัติ เพื่อคุ้มครองความเป็นส่วนตัว (PDPA)

## Features
- ตรวจจับใบหน้าได้หลายใบหน้าพร้อมกัน (Multi-face Detection)
- เซ็นเซอร์ได้ 2 แบบ: Gaussian Blur และ Pixelation (Mosaic)
- ปรับระดับความเบลอผ่าน Slider
- อัปโหลดภาพ (JPG/PNG) → เปรียบเทียบ Before/After → ดาวน์โหลดผลลัพธ์
- ไม่ใช้กล้อง/Webcam (อยู่นอกขอบเขตงาน)

## Project Structure
```text
├── docs/             # Contract, Git Flow, Schedule
├── models/           # โมเดลตรวจจับใบหน้า (blaze_face_short_range.tflite)
├── test_images/      # ภาพสำหรับทดสอบ
├── tests/            # Unit tests ของ detector.py (pytest)
├── detector.py       # ตรวจจับใบหน้าและฟังก์ชันเบลอ/โมเสก
├── run_test_contract.py  # รันทุกกรณีใน Test Contract
├── app.py            # หน้าเว็บ UI ด้วย Streamlit
└── requirements.txt
```

## Setup
ต้องใช้ **Python 3.12** (เช็คด้วย `py -3.12 --version`) ทุกเครื่องในทีมต้องใช้เวอร์ชันเดียวกัน

```bash
py -3.12 -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

## Run
```bash
streamlit run app.py
```

## Test
```bash
pip install pytest
python -m pytest tests
```

ทดสอบตาราง Test Contract (`docs/CONTRACT.md` หัวข้อ 6) กับภาพใน `test_images/`
```bash
python run_test_contract.py                    # ภาพที่ยังไม่มีจะขึ้น SKIP
python run_test_contract.py --group-faces 12   # ระบุจำนวนหน้าจริงใน group_photo.jpg
python run_test_contract.py --save             # บันทึกภาพพร้อมกรอบใบหน้าไว้ที่ output/
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
