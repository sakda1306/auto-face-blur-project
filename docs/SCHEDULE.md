# Schedule & Team Roles

**ระยะเวลา:** 2 วัน (วันที่ 1: ____ / วันที่ 2: ____)
**ผลลัพธ์สุดท้าย:** Web App (Streamlit) ที่เบลอใบหน้าได้ทั้งภาพอัปโหลดและกล้องสด + สไลด์/รายงาน + วิดีโอสาธิต 30–60 วินาที

## 1. แบ่งงาน 4 คน

| Role | ชื่อ | Branch หลัก | ไฟล์ที่รับผิดชอบ | งาน |
|------|------|-------------|------------------|-----|
| **A: Face Detection** | | `feature/face-detection` | `detector.py` (`detect_faces`, `clip_box`, `draw_boxes`) | MediaPipe + Haar สำรอง, ป้องกัน BBox หลุดขอบ, เตรียมภาพทดสอบ |
| **B: Obfuscation** | | `feature/blur-mosaic` | `detector.py` (`apply_gaussian_blur`, `apply_mosaic`, `blur_faces`) | Gaussian Blur, Mosaic, Adaptive kernel ตามขนาดหน้า |
| **C: Web UI** | | `feature/web-ui` | `app.py` (Sidebar + Tab "Image") | อัปโหลด, Radio, Slider, Before/After, จำนวนใบหน้า, ปุ่มดาวน์โหลด |
| **D: Live Webcam & Report** | | `feature/live-webcam` | `app.py` (Tab "Live Webcam"), `webcam_demo.py` | `streamlit-webrtc`, FPS, สไลด์, วิดีโอสาธิต |

> A และ B ทำงานในไฟล์เดียวกันแต่คนละฟังก์ชัน ให้ B ใช้ BBox ปลอม เช่น `[(50, 50, 120, 120)]` ทดสอบไปก่อนระหว่างรองาน A
> C และ D ใช้ `blur_faces` แบบ stub ที่คืน `(image.copy(), 0)` ไปก่อนได้ เพราะ Contract กำหนด Input/Output ไว้แล้ว

## 2. ตารางเวลา

### วันที่ 1: Core Processing

| เวลา | A: Detection | B: Obfuscation | C: Web UI | D: Live & Report |
|------|--------------|----------------|-----------|------------------|
| 09:00–09:30 | **ทุกคน:** clone repo, ติดตั้ง venv, อ่าน `CONTRACT.md` ร่วมกัน, แตก branch ของตัวเอง ||||
| 09:30–12:00 | `detect_faces` ด้วย MediaPipe, วาดกรอบเช็คพิกัด | `apply_gaussian_blur`, `apply_mosaic` บน ROI ตัวอย่าง | โครงหน้า Streamlit: Sidebar, Tabs, file_uploader | ทดลอง `streamlit-webrtc` ให้เปิดกล้องบนเว็บได้ |
| 12:00–13:00 | พักเที่ยง ||||
| 13:00–15:00 | `clip_box`, Haar fallback, เตรียมภาพทดสอบ 5 กรณี | `blur_faces` (ตัด ROI → เบลอ → วางกลับ), Adaptive kernel | Before/After ด้วย `st.columns(2)`, แปลง RGB↔BGR | ใส่ `video_frame_callback` + FPS overlay (ใช้ stub) |
| 15:00–16:00 | **PR เข้า `develop`** | **PR เข้า `develop`** | Review PR ของ A/B | Review PR ของ A/B |
| 16:00–18:00 | ทดสอบความแม่นยำ, แก้บั๊ก | ปรับค่า kernel/blocks ให้สวย | ต่อกับ `blur_faces` ตัวจริง | ต่อกับ `blur_faces` ตัวจริง, วัด FPS |
| **18:00** | ✅ **Checkpoint 1:** `detector.py` merge แล้ว, ภาพนิ่งเบลอได้จริง, กล้องบนเว็บเปิดได้ ||||

### วันที่ 2: Web App, Testing, Presentation

| เวลา | A: Detection | B: Obfuscation | C: Web UI | D: Live & Report |
|------|--------------|----------------|-----------|------------------|
| 09:00–09:15 | **ทุกคน:** Stand-up 15 นาที: เมื่อวานเสร็จอะไร / วันนี้ทำอะไร / ติดอะไร ||||
| 09:15–12:00 | ช่วย D ปรับความเร็วให้ได้ ≥ 15 FPS | ช่วย C ทดสอบทุกโหมด | `st.metric` จำนวนหน้า, `st.download_button`, ข้อความเมื่อไม่พบหน้า | **PR Tab Live Webcam เข้า `develop`** |
| 12:00–13:00 | พักเที่ยง ||||
| 13:00–15:00 | ทดสอบตาราง Test Contract ทุกกรณี | แก้บั๊กที่เจอจากการทดสอบ | **PR Web UI เข้า `develop`**, เก็บ UI ให้สวย | เขียนสไลด์: Pipeline, ทฤษฎี Gaussian/Mosaic |
| 15:00–16:00 | **ทุกคน:** Integration test บน `develop` (เครื่องละ 1 รอบ), อัปเดต `README.md` ||||
| **16:00** | ✅ **Checkpoint 2 (Code Freeze):** PR `develop` → `main` + tag `v1.0` ||||
| 16:00–18:00 | แคปภาพ Before/After ทุกโหมด | ช่วยทำสไลด์ส่วนอัลกอริทึม | ช่วยทำสไลด์ส่วน UI | อัดวิดีโอสาธิต 30–60 วินาที, รวมสไลด์ |
| **18:00** | ✅ **Checkpoint 3:** สไลด์ + วิดีโอ + รายงาน พร้อมส่ง ||||

## 3. Checklist ส่งงาน

- [ ] `streamlit run app.py` บนเครื่องที่ clone ใหม่ รันได้ทันที
- [ ] Tab Image: Gaussian Blur / Mosaic / BBox Only ทำงานครบ, Slider เปลี่ยนผลทันที
- [ ] Tab Live Webcam: เบลอสด, แสดง FPS
- [ ] แสดงจำนวนใบหน้า + ปุ่มดาวน์โหลด
- [ ] ผ่านทุกกรณีใน Test Contract (`CONTRACT.md` หัวข้อ 6)
- [ ] `main` มี tag `v1.0`
- [ ] README มีวิธีรันและรายชื่อสมาชิกครบ
- [ ] สไลด์/รายงาน + วิดีโอสาธิต

## 4. ช่องทางสื่อสาร

- ติดปัญหาเกิน 30 นาที ให้แจ้งในกลุ่มทันที
- แจ้งในกลุ่มทุกครั้งที่เปิด PR พร้อมแนบลิงก์ เพื่อให้คนอื่นมา Review
- ใช้ GitHub Issues จดบั๊กที่ยังแก้ไม่ทัน
