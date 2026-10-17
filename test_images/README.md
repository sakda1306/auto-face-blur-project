# Test Images

ภาพสำหรับ Test Contract (`docs/CONTRACT.md` หัวข้อ 6) ทุกภาพย่อให้ด้านยาวไม่เกิน 2000 px

```bash
python run_test_contract.py --group-faces 4 --save
```

## ภาพหลัก (ใช้โดย `run_test_contract.py`)

| ไฟล์ | กรณี | ผลที่ต้องได้ |
|------|------|-------------|
| `single_face.jpg` | ใบหน้าเดียว | 1 หน้า |
| `group_photo.jpg` | ภาพหมู่ (**มี 4 หน้า**) | พบอย่างน้อย 80% |
| `side_face.jpg` | หันข้างเล็กน้อย | พบ |
| `no_face.jpg` | ไม่มีใบหน้า | 0 หน้า |
| `edge_face.jpg` | ใบหน้าชิดขอบภาพ | ไม่ error, กรอบไม่หลุดขอบ |

## ภาพเพิ่มเติม (ทดสอบด้วยตา)

| ไฟล์ | กรณี |
|------|------|
| `single_face_2.jpg`, `single_face_3.jpg` | ใบหน้าเดียว |
| `side_face_2.jpg`, `side_face_3.jpg` | หันข้าง (`side_face_3` หันข้างเต็มที่) |
| `edge_face_2.jpg`, `edge_face_3.jpg` | ใบหน้าชิดขอบ / ใกล้กล้อง |
| `no_face_2.jpg` | ไม่มีใบหน้า (ขวดน้ำอัดลม) |
| `group_photo_2.jpg` – `group_photo_5.jpg` | ภาพหมู่ 6–20 คน |
| `group_photo_6.jpg` | ฝูงชนหนาแน่น |
| `group_photo_7.jpg` | ฝูงชนภาพเล็ก 547×365 จาก Issue #6 |
| `group_photo_8.jpg` | ภาพหมู่หน้าชิดกัน |

## กติกา
- ไฟล์ละไม่เกิน 5 MB และย่อด้านยาวไม่เกิน 2000 px ก่อน commit
- ห้ามใช้ภาพที่มีลายน้ำหรือภาพที่ต้องซื้อลิขสิทธิ์ (iStock, Shutterstock ฯลฯ) ให้ใช้ภาพฟรีจาก Unsplash หรือ Pexels
