"""
Jadval muammosini ANIQ topish uchun bir martalik tashxis skripti.

Ishlatish (worker Railway Shell'ida):
    python diag_schedule.py
"""

from config import settings
from firebase_client import db

print("=" * 60)
print("1) config.py / CLASS_ID muhit o'zgaruvchisi:")
print("   settings.class_id =", repr(settings.class_id))

print()
print("2) Firestore 'settings/general' hujjati:")
try:
    doc = db().collection("settings").document("general").get()
    if doc.exists:
        data = doc.to_dict()
        print("   mavjud, tarkibi:", data)
        print("   className maydoni =", repr(data.get("className")))
    else:
        print("   MAVJUD EMAS (bot kodida bu holda '9-A' ga tushib qoladi)")
except Exception as e:
    print("   XATO:", e)

print()
print("3) 'schedule' kolleksiyasidagi HAMMA hujjatlar (eng ko'pi 50 ta):")
try:
    all_docs = list(db().collection("schedule").limit(50).stream())
    print(f"   jami topildi: {len(all_docs)} ta")
    class_ids_seen = {}
    for d in all_docs:
        data = d.to_dict()
        cid = data.get("classId", "<yo'q>")
        class_ids_seen[cid] = class_ids_seen.get(cid, 0) + 1
        if len(class_ids_seen) <= 10:
            pass
    print("   classId qiymatlari bo'yicha son:", class_ids_seen)
    print()
    print("   Birinchi 3 ta hujjat (to'liq):")
    for d in all_docs[:3]:
        print("  ", "ID:", d.id, "->", d.to_dict())
except Exception as e:
    print("   XATO:", e)

print()
print("4) get_schedule(settings.class_id) natijasi:")
try:
    from bot_compat_get_schedule import get_schedule as _unused
except ImportError:
    pass
# worker papkasida bot/ paketi yo'q, shuning uchun get_schedule mantig'ini
# shu yerda soddalashtirib takrorlaymiz:
def get_schedule_like_bot(class_id):
    client = db()
    doc = client.collection("schedule").document(class_id).get()
    if doc.exists:
        d = doc.to_dict()
        lessons = d.get("lessons") or d.get("items") or []
        if lessons:
            return ("BITTA HUJJAT (documentdan)", lessons)
    rows = []
    for field in ("classId", "className"):
        snap = client.collection("schedule").where(field, "==", class_id).stream()
        rows.extend(s.to_dict() for s in snap)
    return ("WHERE SO'ROVI (classId YOKI className bo'yicha)", rows)

src, rows = get_schedule_like_bot(settings.class_id)
print(f"   manba: {src}, topilgan dars soni: {len(rows)}")

print("=" * 60)
print("TAHLIL:")
print(f"- Yozilgan classId qiymati (2-band, agar settings/general bo'lsa): tekshiring")
print(f"- Yozilgan jadval classId qiymati (3-band): tekshiring")
print(f"- Ular settings.class_id ({settings.class_id!r}) bilan AYNAN bir xil bo'lishi kerak")
print("=" * 60)
