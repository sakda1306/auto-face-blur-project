# Contract: Auto Face Blur Web App

เอกสารนี้กำหนด "สัญญา" ระหว่างส่วนต่างๆ ของระบบ ได้แก่ชื่อฟังก์ชัน, Input/Output, ชนิดข้อมูล และพฤติกรรมเมื่อเจอกรณีพิเศษ
เพื่อให้สมาชิกทั้ง 4 คนเขียนโค้ดแยกกันได้พร้อมกัน แล้วนำมารวมกันได้โดยไม่ต้องแก้โค้ดของกันและกัน

> **กติกา:** ถ้าต้องการเปลี่ยน Contract ให้เปิด Pull Request ที่แก้ไฟล์นี้ก่อน และต้องได้รับ Approve จากทุกคนที่ได้รับผลกระทบ แล้วค่อยแก้โค้ด

---

## 1. ภาพรวมสถาปัตยกรรม (Architecture)

ระบบเป็น **Web App ด้วย Streamlit** มี 2 โหมดการใช้งานบนหน้าเว็บเดียวกัน

```text
┌───────────────────────── Browser ─────────────────────────┐
│  Sidebar: โหมด (Blur / Mosaic / BBox) + Slider ความเข้ม     │
│  Tab 1 "Image"        │  Tab 2 "Live Webcam"               │
│  อัปโหลดภาพ → Before/After│  กล้องผ่าน WebRTC → ภาพสด + FPS      │
└───────────┬───────────────────────────┬───────────────────┘
            │ app.py (UI Layer)         │ streamlit-webrtc
            ▼                           ▼
     ┌──────────────────────────────────────────┐
     │ detector.py (Core Layer, ไม่มีโค้ด UI)       │
     │ detect_faces → clip_box → obfuscate → merge │
     └──────────────────────────────────────────┘
```

| Layer | ไฟล์ | หน้าที่ | ห้ามทำ |
|-------|------|--------|--------|
| Core | `detector.py` | ตรวจจับใบหน้า, เบลอ, โมเสก, วาดกรอบ | ห้าม `import streamlit` |
| Web UI | `app.py` | อัปโหลด, ปุ่ม, Slider, แสดงผล, ดาวน์โหลด | ห้ามเขียน logic การเบลอเอง |
| Live | `app.py` (Tab 2) | รับเฟรมจากกล้องผ่าน `streamlit-webrtc` | ห้ามใช้ `cv2.VideoCapture` บนเว็บ |
| CLI (optional) | `webcam_demo.py` | ทดสอบกล้องบนเครื่องตัวเองแบบไม่ผ่านเว็บ | - |

> หมายเหตุ: บนเว็บต้องใช้ `streamlit-webrtc` เพราะ `cv2.VideoCapture(0)` จะเปิดกล้องของ **เครื่อง Server** ไม่ใช่กล้องของผู้ใช้ที่เปิดเบราว์เซอร์

---

## 2. ชนิดข้อมูลกลาง (Shared Data Types)

| ชื่อ | ชนิด | รายละเอียด |
|------|------|-----------|
| `Image` | `numpy.ndarray` | `dtype=uint8`, shape `(H, W, 3)`, **ระบบสี BGR** (ตาม OpenCV) |
| `BBox` | `tuple[int, int, int, int]` | `(x, y, w, h)` เป็นพิกเซล, มุมซ้ายบนคือ `(x, y)` |
| `Mode` | `str` | ค่าใดค่าหนึ่งใน `"blur"`, `"mosaic"`, `"bbox"` |
| `Strength` | `int` | ช่วง `1–100` (1 = เบาสุด, 100 = แรงสุด), ค่าเริ่มต้น `50` |

**กฎเรื่องระบบสี:** ภายใน `detector.py` ใช้ **BGR เสมอ** ส่วน `app.py` เป็นคนแปลง RGB ↔ BGR ที่ขอบระบบ
(ตอนอ่านไฟล์ที่อัปโหลดเข้ามา และก่อนส่งภาพไป `st.image`)

**กฎเรื่อง BBox:** BBox ที่ออกมาจาก `detect_faces` ต้องผ่าน `clip_box` แล้วเสมอ คือ `x ≥ 0`, `y ≥ 0`, `x + w ≤ W`, `y + h ≤ H` และ `w, h > 0`

---

## 3. Core API: `detector.py`

### 3.1 `detect_faces(image, min_confidence=0.5) -> list[BBox]`
| | |
|---|---|
| Input | `image: Image`, `min_confidence: float` ในช่วง `0.0–1.0` |
| Output | รายการ `BBox` ของทุกใบหน้า เรียงจากซ้ายไปขวา (ตามค่า `x`) |
| ไม่พบใบหน้า | คืนค่า `[]` (ห้าม raise error) |
| Side effect | ห้ามแก้ไข `image` ต้นฉบับ |
| Implementation | ใช้ MediaPipe **Tasks API** (`mediapipe.tasks.python.vision.FaceDetector`) กับโมเดล `models/blaze_face_short_range.tflite` เป็นหลัก และ Haar Cascade (`cv2.data.haarcascades`) เป็นตัวสำรองถ้าโหลด MediaPipe ไม่ได้ โมเดลต้องสร้างครั้งเดียว (lazy singleton) ห้ามสร้างใหม่ทุกเฟรม |
| หมายเหตุ | mediapipe 1.x **ไม่มี** `mp.solutions.face_detection` แบบเก่าแล้ว ตัวอย่างโค้ดเก่าในอินเทอร์เน็ตจะใช้ไม่ได้ และ Tasks API รับภาพเป็น RGB (`mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)`) จึงต้องแปลงจาก BGR ก่อนส่งเข้าโมเดล |

### 3.2 `clip_box(box, image_shape) -> BBox | None`
บีบ BBox ให้อยู่ในขอบภาพ ถ้าหลังบีบแล้ว `w ≤ 0` หรือ `h ≤ 0` ให้คืน `None`

### 3.3 `apply_gaussian_blur(roi, strength) -> Image`
| | |
|---|---|
| Input | `roi: Image` (ภาพเฉพาะใบหน้า), `strength: Strength` |
| Output | ภาพ shape เท่ากับ `roi` เดิม |
| Kernel | `k = max(3, int(min(h, w) * strength / 100))` แล้วบังคับเป็นเลขคี่ด้วย `k = k \| 1` ใช้ `(k, k)` กับ `cv2.GaussianBlur` |

> สูตรนี้ทำให้ **ขนาดเคอร์เนลแปรผันตามขนาดใบหน้า** โดยอัตโนมัติ (ฟีเจอร์เสริม): หน้าใหญ่ได้ `k` สูง หน้าเล็กได้ `k` ต่ำ

### 3.4 `apply_mosaic(roi, strength) -> Image`
| | |
|---|---|
| Input | `roi: Image`, `strength: Strength` |
| Output | ภาพ shape เท่ากับ `roi` เดิม |
| Blocks | `blocks = max(2, 32 - (strength * 30) // 100)` (strength 1 → 32 บล็อก, 100 → 2 บล็อก) |
| วิธีทำ | ย่อเป็น `(blocks, blocks)` ด้วย `INTER_LINEAR` แล้วขยายกลับเป็น `(w, h)` ด้วย `INTER_NEAREST` |

### 3.5 `draw_boxes(image, boxes) -> Image`
คืนภาพ **สำเนา** ที่วาดกรอบสีเขียว `(0, 255, 0)` หนา 2 px รอบแต่ละ BBox (ใช้กับโหมด `"bbox"`)

### 3.6 `blur_faces(image, mode="blur", strength=50) -> tuple[Image, int]`
ฟังก์ชันหลักที่ UI เรียกใช้ฟังก์ชันเดียว

| | |
|---|---|
| Input | `image: Image`, `mode: Mode`, `strength: Strength` |
| Output | `(result_image, face_count)` โดย `result_image` เป็นภาพใหม่ ห้ามแก้ภาพต้นฉบับ |
| ไม่พบใบหน้า | คืน `(สำเนาภาพเดิม, 0)` |
| Error | `ValueError` เมื่อ `image is None`, `mode` ไม่อยู่ใน 3 ค่า หรือ `strength` ไม่อยู่ในช่วง 1–100 |

ขั้นตอนข้างใน: `detect_faces` → วนแต่ละ BBox → ตัด ROI `[y:y+h, x:x+w]` → `apply_gaussian_blur` / `apply_mosaic` → วางกลับที่เดิม
(ถ้า `mode == "bbox"` ให้เรียก `draw_boxes` แทน)

---

## 4. Web UI Contract: `app.py`

### 4.1 Sidebar (ใช้ร่วมกันทั้ง 2 Tab)
| Widget | Label | ค่าที่ส่งเข้า `blur_faces` |
|--------|-------|------------------------|
| `st.radio` | `Gaussian Blur` / `Mosaic` / `BBox Only` | `"blur"` / `"mosaic"` / `"bbox"` |
| `st.slider` | `ความเข้มข้น` (1–100, ค่าเริ่มต้น 50) | `strength` |

### 4.2 Tab "Image"
1. `st.file_uploader` รับ `jpg`, `jpeg`, `png`
2. แปลงไฟล์เป็น `Image` (BGR) ด้วย `cv2.imdecode`
3. เรียก `blur_faces(image, mode, strength)`
4. แสดงผลด้วย `st.columns(2)`: ซ้าย **Before** ขวา **After** (แปลงเป็น RGB ก่อนแสดง)
5. `st.metric("จำนวนใบหน้าที่พบ", face_count)` ถ้าเป็น 0 ให้แสดง `st.info("ไม่พบใบหน้าในภาพ")`
6. `st.download_button` ดาวน์โหลดเป็น PNG ชื่อ `<ชื่อไฟล์เดิม>_blurred.png`

### 4.3 Tab "Live Webcam"
1. ใช้ `webrtc_streamer` จาก `streamlit-webrtc`
2. ใน `video_frame_callback`: `frame.to_ndarray(format="bgr24")` → `blur_faces(...)` → วาดค่า FPS มุมซ้ายบน → คืน `av.VideoFrame.from_ndarray(..., format="bgr24")`
3. ค่า `mode` และ `strength` อ่านจาก Sidebar
4. เป้าหมายประสิทธิภาพ: **≥ 15 FPS** ที่ความละเอียด 640×480

### 4.4 Caching
ตัวตรวจจับใบหน้าต้องสร้างครั้งเดียวต่อ process (singleton ใน `detector.py`) ห้ามสร้างใหม่ทุกครั้งที่ Streamlit rerun

---

## 5. Runtime & Dependencies

**Python 3.12** (ทุกเครื่องในทีมต้องใช้เวอร์ชันนี้ เพราะ numpy 2.5 ขึ้นไปรองรับเฉพาะ Python ≥ 3.12)

`requirements.txt` ระบุเวอร์ชันตายตัว ซึ่งทดสอบแล้วว่าติดตั้งและรัน `FaceDetector` ได้บน Python 3.12 / Windows

```text
opencv-python==5.0.0.93
mediapipe==1.0.1
numpy==2.5.3
streamlit==1.65.0
streamlit-webrtc==0.78.1
```

| ไฟล์ | ที่มา |
|------|------|
| `models/blaze_face_short_range.tflite` | โมเดลตรวจจับใบหน้าระยะใกล้ของ MediaPipe (230 KB) commit ไว้ใน repo เพื่อไม่ต้องดาวน์โหลดตอนรัน |

ถ้าต้องเพิ่มหรืออัปเกรดไลบรารี ให้แก้ทั้ง `requirements.txt` และหัวข้อนี้ใน PR เดียวกัน และต้องทดสอบติดตั้งใน venv ใหม่ก่อนเปิด PR

---

## 6. Test Contract (Definition of Done)

ภาพทดสอบเก็บใน `test_images/` และตั้งชื่อตามกรณี

| ไฟล์ | กรณี | ผลที่ต้องได้ |
|------|------|-------------|
| `single_face.jpg` | ใบหน้าเดียว | `face_count == 1` |
| `group_photo.jpg` | ภาพหมู่หลายระยะ | ตรวจพบอย่างน้อย 80% ของใบหน้าทั้งหมด |
| `side_face.jpg` | หันข้างเล็กน้อย | ตรวจพบ |
| `no_face.jpg` | ไม่มีคน | `face_count == 0` และไม่ error |
| `edge_face.jpg` | ใบหน้าชิดขอบภาพ | ไม่ error, BBox ไม่หลุดขอบ |

งานจะถือว่า "เสร็จ" เมื่อ
- ทำงานตาม Contract ข้างบนและผ่านทุกกรณีในตาราง
- `streamlit run app.py` เปิดได้โดยไม่มี error
- มีคนในทีมอย่างน้อย 1 คน Review และ Approve PR แล้ว
