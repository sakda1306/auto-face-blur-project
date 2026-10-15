# Git Flow

Repo: https://github.com/sakda1306/auto-face-blur-project

## 1. Branch

```text
main      ●────────────────────────────────●  v1.0 (ส่งงาน)
           \                              /
develop     ●───●───────●───────●───────●     ← default branch
                 \     / \     /
feature/...       ●───●   ●───●
```

| Branch | ใช้ทำอะไร | ใครเขียนได้ |
|--------|----------|-----------|
| `main` | โค้ดเวอร์ชันส่งงาน/นำเสนอ ต้องรันได้เสมอ | Merge จาก `develop` ผ่าน PR เท่านั้น |
| `develop` | รวมงานของทุกคน (default branch) | Merge จาก `feature/*` ผ่าน PR เท่านั้น |
| `feature/<งาน>` | พัฒนาฟีเจอร์ 1 งาน | เจ้าของงาน |
| `fix/<งาน>` | แก้บั๊ก | ใครก็ได้ |
| `docs/<งาน>` | แก้เอกสาร/รายงาน | ใครก็ได้ |

**ชื่อ branch** ใช้ตัวพิมพ์เล็กและขีดกลาง เช่น
`feature/face-detection`, `feature/blur-mosaic`, `feature/web-ui`, `feature/live-webcam`, `fix/bbox-out-of-range`

## 2. ขั้นตอนทำงานประจำวัน

```bash
# 0) ครั้งแรกครั้งเดียว
git clone https://github.com/sakda1306/auto-face-blur-project.git
cd auto-face-blur-project
py -3.12 -m venv .venv          # ต้องใช้ Python 3.12
.venv\Scripts\activate
pip install -r requirements.txt

# 1) เริ่มงานใหม่: แตก branch จาก develop ล่าสุดเสมอ
git switch develop
git pull
git switch -c feature/face-detection

# 2) เขียนโค้ดแล้ว commit ทีละเรื่องเล็กๆ
git add detector.py
git commit -m "feat(detector): add MediaPipe face detection"

# 3) ก่อน push ให้ดึง develop ล่าสุดมารวมก่อน
git fetch origin
git merge origin/develop          # ถ้า conflict ให้แก้แล้ว commit
git push -u origin feature/face-detection

# 4) เปิด Pull Request: base = develop
gh pr create --base develop --fill
```

## 3. Commit Message

รูปแบบ `<type>(<scope>): <สรุปสั้นๆ>`

| type | ใช้เมื่อ |
|------|---------|
| `feat` | เพิ่มฟีเจอร์ |
| `fix` | แก้บั๊ก |
| `docs` | แก้เอกสาร |
| `refactor` | ปรับโค้ดโดยพฤติกรรมไม่เปลี่ยน |
| `test` | เพิ่มหรือแก้ภาพ/โค้ดทดสอบ |
| `chore` | งานจุกจิก เช่น `requirements.txt`, `.gitignore` |

ตัวอย่าง
```text
feat(detector): add apply_mosaic with adaptive block size
fix(app): convert BGR to RGB before st.image
docs: update contract for blur_faces return value
```

## 4. Pull Request

- **base เป็น `develop` เสมอ** ยกเว้น PR สำหรับส่งงานที่ไปเข้า `main`
- 1 PR = 1 เรื่อง ไม่ควรแก้เกิน ~300 บรรทัด
- ต้องมีคน Review และ Approve อย่างน้อย **1 คน** ที่ไม่ใช่คนเขียน
- คำอธิบาย PR ควรมี: ทำอะไร, ทดสอบอย่างไร, ภาพผลลัพธ์ Before/After (ถ้ามี)
- ใช้ **Squash and merge** เพื่อให้ประวัติใน `develop` สะอาด แล้วลบ branch หลัง merge
- ถ้าแก้ Contract ต้องแก้ `docs/CONTRACT.md` ใน PR เดียวกัน

## 5. Release ไป `main`

เมื่อถึง Checkpoint ส่งงาน (ดู [SCHEDULE.md](SCHEDULE.md))
```bash
gh pr create --base main --head develop --title "Release v1.0"
```
หลัง merge ให้สร้าง tag (เจ้าของ repo เป็นคนทำ)
```bash
git switch main && git pull
git tag v1.0
git push origin v1.0
```

## 6. ห้ามทำ

- ห้าม push ตรงเข้า `main` หรือ `develop`
- ห้าม `git push --force` บน branch ที่คนอื่นใช้ร่วม
- ห้าม commit `.venv/`, `.env`, `__pycache__/`, ไฟล์วิดีโอผลลัพธ์ หรือภาพขนาดใหญ่เกิน 5 MB
- ห้ามแก้ไฟล์ที่เป็นความรับผิดชอบของคนอื่นโดยไม่บอกก่อน (ดูการแบ่งงานใน [SCHEDULE.md](SCHEDULE.md))

## 7. แก้ Conflict

```bash
git fetch origin
git merge origin/develop
# เปิดไฟล์ที่ขึ้น conflict แล้วเลือกเก็บโค้ดระหว่าง <<<<<<< ======= >>>>>>>
git add <ไฟล์ที่แก้แล้ว>
git commit
git push
```
ถ้าไม่แน่ใจว่าจะเก็บโค้ดฝั่งไหน ให้ทักเจ้าของโค้ดส่วนนั้นก่อน
