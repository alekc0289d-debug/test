"""
Sinf jadvalini Firestore'ga bir martalik yozish.

Sayt kodida (`maktab-tizimi/src/constants/jadval.js`) 9-A sinfining
haftalik jadvali qo'lda kiritilgan edi, lekin u FAQAT saytning o'zida
— Firestore'da emas. Bot esa jadvalni bevosita Firestore'dagi
'schedule' kolleksiyasidan o'qiydi, shuning uchun u hech narsa topa
olmasdi (sayt esa o'z JS fayldagi zaxira nusxasini ko'rsatib,
muammoni yashirib turardi).

Bu skript o'sha jadvalni (quyida, Python ko'rinishida takrorlangan)
'schedule' kolleksiyasiga, 'classId' bilan yozadi — shundan keyin
bot ham, sayt ham (agar eMaktab orqali hali sinxronlanmagan bo'lsa)
bir xil ma'lumotni ko'radi.

Ishlatish:
    python seed_schedule.py

Qayta ishga tushirsangiz ham xavfsiz — avval shu classId uchun
eski (studentId'siz, ya'ni shu skript yozgan) yozuvlarni o'chirib,
keyin qayta yozadi.
"""

import logging

from config import settings
from firebase_client import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("seed_schedule")

# 9-A sinf jadvali — maktab-tizimi/src/constants/jadval.js bilan AYNAN BIR XIL.
# Agar jadval o'zgarsa, shu yerni ham, saytdagi faylni ham yangilang.
JADVAL = [
    {"dayOfWeek": "Dushanba", "lessons": [
        {"lessonNumber": 1, "subject": "Kelajak soati", "teacher": "Raximova M.T.", "startTime": "08:00", "endTime": "08:45", "room": "7-xona"},
        {"lessonNumber": 2, "subject": "Fizika", "teacher": "Samadova Y.S.", "startTime": "08:50", "endTime": "09:35", "room": "7-xona"},
        {"lessonNumber": 3, "subject": "Informatika", "teacher": "Jo'rayeva B.B.", "startTime": "09:40", "endTime": "10:25", "room": "7-xona"},
        {"lessonNumber": 4, "subject": "Texnologiya", "teacher": "Hafizova M.Q.", "startTime": "10:35", "endTime": "11:20", "room": "7-xona"},
        {"lessonNumber": 5, "subject": "Ingliz tili", "teacher": "NORMAMATOVA S.O.", "startTime": "11:25", "endTime": "12:10", "room": "7-xona"},
        {"lessonNumber": 6, "subject": "Rus tili (n)", "teacher": "PO'LATOVA Z.I.", "startTime": "12:15", "endTime": "13:00", "room": "7-xona"},
    ]},
    {"dayOfWeek": "Seshanba", "lessons": [
        {"lessonNumber": 1, "subject": "Kimyo", "teacher": "Ro'ziyeva M.N.", "startTime": "08:00", "endTime": "08:45", "room": "7-xona"},
        {"lessonNumber": 2, "subject": "Chizmachilik", "teacher": "Suyunova L.J.", "startTime": "08:50", "endTime": "09:35", "room": "7-xona"},
        {"lessonNumber": 3, "subject": "Informatika", "teacher": "Jo'rayeva B.B.", "startTime": "09:40", "endTime": "10:25", "room": "7-xona"},
        {"lessonNumber": 4, "subject": "Geometriya", "teacher": "Tursinova M.A.", "startTime": "10:35", "endTime": "11:20", "room": "7-xona"},
        {"lessonNumber": 5, "subject": "O'zbekiston tarixi", "teacher": "Haydarov S.S.", "startTime": "11:25", "endTime": "12:10", "room": "7-xona"},
        {"lessonNumber": 6, "subject": "Algebra", "teacher": "Tursinova M.A.", "startTime": "12:15", "endTime": "13:00", "room": "7-xona"},
    ]},
    {"dayOfWeek": "Chorshanba", "lessons": [
        {"lessonNumber": 1, "subject": "O'zbekiston tarixi", "teacher": "Haydarov S.S.", "startTime": "08:00", "endTime": "08:45", "room": "7-xona"},
        {"lessonNumber": 2, "subject": "Rus tili (n)", "teacher": "PO'LATOVA Z.I.", "startTime": "08:50", "endTime": "09:35", "room": "7-xona"},
        {"lessonNumber": 3, "subject": "Ingliz tili", "teacher": "NORMAMATOVA S.O.", "startTime": "09:40", "endTime": "10:25", "room": "7-xona"},
        {"lessonNumber": 4, "subject": "Jismoniy tarbiya", "teacher": "Raxmatov B.A.", "startTime": "10:35", "endTime": "11:20", "room": "7-xona"},
        {"lessonNumber": 5, "subject": "Ona tili", "teacher": "Nabiyeva N.I.", "startTime": "11:25", "endTime": "12:10", "room": "7-xona"},
    ]},
    {"dayOfWeek": "Payshanba", "lessons": [
        {"lessonNumber": 1, "subject": "Biologiya", "teacher": "Xudoyberdiyeva", "startTime": "08:00", "endTime": "08:45", "room": "6-xona"},
        {"lessonNumber": 2, "subject": "Kimyo", "teacher": "Ro'ziyeva M.N.", "startTime": "08:50", "endTime": "09:35", "room": "5-xona"},
        {"lessonNumber": 3, "subject": "Ingliz tili", "teacher": "NORMAMATOVA S.O.", "startTime": "09:40", "endTime": "10:25", "room": "7-xona"},
        {"lessonNumber": 4, "subject": "Ona tili", "teacher": "Nabiyeva N.I.", "startTime": "10:35", "endTime": "11:20", "room": "7-xona"},
        {"lessonNumber": 5, "subject": "Jismoniy tarbiya", "teacher": "Hayitov N.X.", "startTime": "11:25", "endTime": "12:10", "room": "7-xona"},
        {"lessonNumber": 6, "subject": "Adabiyot", "teacher": "Nabiyeva N.I.", "startTime": "12:15", "endTime": "13:00", "room": "7-xona"},
    ]},
    {"dayOfWeek": "Juma", "lessons": [
        {"lessonNumber": 1, "subject": "Huquq", "teacher": "Raximova M.T.", "startTime": "08:00", "endTime": "08:45", "room": "6-xona"},
        {"lessonNumber": 2, "subject": "Geometriya", "teacher": "Tursinova M.A.", "startTime": "08:50", "endTime": "09:35", "room": "7-xona"},
        {"lessonNumber": 3, "subject": "Geografiya", "teacher": "Oroqova M.B.", "startTime": "09:40", "endTime": "10:25", "room": "6-xona"},
        {"lessonNumber": 4, "subject": "Algebra", "teacher": "Tursinova M.A.", "startTime": "10:35", "endTime": "11:20", "room": "7-xona"},
        {"lessonNumber": 5, "subject": "Adabiyot", "teacher": "Nabiyeva N.I.", "startTime": "11:25", "endTime": "12:10", "room": "7-xona"},
        {"lessonNumber": 6, "subject": "Ona tili", "teacher": "Nabiyeva N.I.", "startTime": "12:15", "endTime": "13:00", "room": "7-xona"},
    ]},
    {"dayOfWeek": "Shanba", "lessons": [
        {"lessonNumber": 1, "subject": "Algebra", "teacher": "Tursinova M.A.", "startTime": "08:00", "endTime": "08:45", "room": "7-xona"},
        {"lessonNumber": 2, "subject": "Tarbiya", "teacher": "Raximova M.T.", "startTime": "08:50", "endTime": "09:35", "room": "7-xona"},
        {"lessonNumber": 3, "subject": "Geografiya", "teacher": "Oroqova M.B.", "startTime": "09:40", "endTime": "10:25", "room": "8-xona"},
        {"lessonNumber": 4, "subject": "Fizika", "teacher": "Samadova Y.S.", "startTime": "10:35", "endTime": "11:20", "room": "7-xona"},
        {"lessonNumber": 5, "subject": "Biologiya", "teacher": "Xudoyberdiyeva", "startTime": "11:25", "endTime": "12:10", "room": "7-xona"},
        {"lessonNumber": 6, "subject": "Jahon tarixi", "teacher": "Haydarov S.S.", "startTime": "12:15", "endTime": "13:00", "room": "7-xona"},
    ]},
]


def main():
    class_id = settings.class_id
    client = db()
    coll = client.collection("schedule")

    # Avval shu classId uchun 'umumiy' (studentId'siz) eski yozuvlarni
    # tozalaymiz, keyin qayta yozamiz — bir necha marta ishga tushirish
    # xavfsiz bo'lishi uchun.
    deleted = 0
    seen_ids = set()
    for field in ("classId", "className"):
        for doc in coll.where(field, "==", class_id).stream():
            if doc.id in seen_ids:
                continue
            data = doc.to_dict()
            if not data.get("studentId"):
                doc.reference.delete()
                seen_ids.add(doc.id)
                deleted += 1
    if deleted:
        log.info("Eski %s ta umumiy yozuv o'chirildi", deleted)

    written = 0
    for day in JADVAL:
        for lesson in day["lessons"]:
            coll.add({
                # Loyihaning turli qismlari sinfni turlicha nomlagan —
                # ikkalasini ham yozamiz, shunda qaysi birini qidirishdan
                # qat'i nazar topiladi.
                "classId": class_id,
                "className": class_id,
                "dayOfWeek": day["dayOfWeek"],
                **lesson,
                "source": "seed_schedule",
            })
            written += 1

    log.info("✅ %s ta dars '%s' sinfi uchun yozildi", written, class_id)


if __name__ == "__main__":
    main()
