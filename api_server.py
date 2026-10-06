"""eMaktab tekshirish API — FastAPI."""

import hmac
import json
import logging
import os
import threading
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from captcha_flow import process_answered
from config import settings
from emaktab import login, fetch_data, CaptchaRequired, LoginFailed
from firebase_client import (
    BatchWriter,
    db,
    save_credentials,
    save_sync,
    save_captcha_to_queue,
    mark_error,
    read_credentials,
    check_login_exists,
)
from crypto import decrypt

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("api")



@asynccontextmanager
async def lifespan(_app):
    scheduler.start()
    log.info("Scheduler ishga tushdi — har soatda sync")
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="Maktab API", lifespan=lifespan)

_origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]
if "*" in _origins:
    log.warning("ALLOWED_ORIGINS=* — productionda aniq domen bering!")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins or ["*"],
    allow_credentials=False,  # cookie ishlatilmaydi
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Admin-Token"],
)

tasks = {}
_task_ts = {}
_TASK_TTL = 3600  # soniya
# Bir vaqtning o'zida ko'pi bilan 2 ta Chrome (ro'yxatdan o'tish uchun)
_register_slots = threading.BoundedSemaphore(2)


def require_admin(x_admin_token: str = Header(default="")):
    expected = settings.api_admin_token
    if not expected:
        raise HTTPException(503, "API_ADMIN_TOKEN sozlanmagan")
    if not hmac.compare_digest(x_admin_token.encode(), expected.encode()):
        raise HTTPException(401, "Ruxsat yo'q")


def _purge_tasks():
    now = time.time()
    for tid in [t for t, ts in _task_ts.items() if now - ts > _TASK_TTL]:
        tasks.pop(tid, None)
        _task_ts.pop(tid, None)


def _run_register(task_id, req):
    set_status(task_id, "queue", "Navbatda...", 1)
    with _register_slots:
        do_register(task_id, req)


class RegisterRequest(BaseModel):
    fullName: str = ""
    login: str
    password: str
    phone: str
    motherPhone: str
    fatherPhone: str = ""
    consent: bool = False


def set_status(task_id, step, message, progress, status="processing"):
    tasks[task_id] = {
        "status": status,
        "step": step,
        "message": message,
        "progress": progress,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    log.info("[%s] %s - %s", task_id[:8], step, message)


# ============================================================
# RO'YXATDAN O'TISH
# ============================================================
def do_register(task_id, req):
    try:
        # 1. DUPLICATE CHECK
        set_status(task_id, "check", "Login tekshirilmoqda...", 3)

        if check_login_exists(req.login):
            set_status(
                task_id, "error",
                "Bu login allaqachon ro'yxatdan o'tgan. "
                "Har bir o'quvchi faqat bir marta ro'yxatdan o'tishi mumkin.",
                0, "error"
            )
            return

        # 2. LOGIN
        set_status(task_id, "login", "eMaktab'ga kirilmoqda...", 8)

        try:
            lr = login(req.login, req.password)
            cookies = lr.cookies
            log.info("[%s] Login muvaffaqiyatli", task_id[:8])
            set_status(task_id, "login", "eMaktab'ga kirildi", 18)
        except CaptchaRequired:
            set_status(task_id, "error",
                "CAPTCHA chiqdi. Iltimos, qayta urinib ko'ring.",
                0, "error")
            return
        except LoginFailed:
            set_status(task_id, "error",
                "eMaktab login yoki parol xato", 0, "error")
            return
        except Exception as e:
            log.error("[%s] Login xato: %s", task_id[:8], e)
            set_status(task_id, "error",
                "Login vaqtida xatolik. Keyinroq urinib ko'ring.", 0, "error")
            return

        # 3. MA'LUMOT OLISH
        def status_cb(msg, progress):
            set_status(task_id, "fetch", msg, progress)

        try:
            data = fetch_data(cookies, status_cb=status_cb)
        except Exception as e:
            log.error("[%s] Fetch xato: %s", task_id[:8], e)
            set_status(task_id, "error",
                "eMaktab'dan ma'lumot olib bo'lmadi. Keyinroq urinib ko'ring.", 0, "error")
            return

        student = data.get("student", {})
        grades = data.get("grades", [])
        schedule = data.get("schedule", [])
        subjects = data.get("subjects", [])
        subjects_count = data.get("subjectsCount", 0)

        log.info("[%s] Student: %s", task_id[:8],
                 json.dumps(student, ensure_ascii=False))
        log.info("[%s] Grades: %s ta, Fanlar: %s, Jadval: %s",
                 task_id[:8], len(grades), subjects_count, len(schedule))

        person_id = student.get("personId") or f"manual_{task_id[:8]}"
        first_name = student.get("firstName") or ""
        last_name = student.get("lastName") or ""

        if first_name and last_name:
            full_name = f"{first_name} {last_name}".strip()
        elif first_name:
            full_name = first_name
        elif last_name:
            full_name = last_name
        else:
            full_name = req.fullName.strip() or "Noma'lum"

        # 4. SAQLASH
        set_status(task_id, "save", "Firestore'ga saqlanmoqda...", 92)

        try:
            student_id = f"student_{uuid.uuid4().hex[:12]}"
            client = db()
            now = datetime.now(timezone.utc)

            save_credentials(student_id, req.login, req.password, cookies)

            client.collection("students").document(student_id).set({
                "fullName": full_name,
                "classId": settings.class_id,
                "phone": req.phone,
                "motherPhone": req.motherPhone,
                "fatherPhone": req.fatherPhone,
                "status": "active",
                "emaktab": {
                    "personId": person_id,
                    "userId": student.get("userId"),
                    "firstName": first_name,
                    "lastName": last_name,
                    "schoolId": student.get("schoolId"),
                    "groupId": student.get("groupId"),
                },
                "gradesCount": len(grades),
                "subjectsCount": subjects_count,
                "scheduleCount": len(schedule),
                "registeredAt": now,
                "createdAt": now,
                "updatedAt": now,
            })

            # BAHOLAR
            batch = BatchWriter(client)
            for g in grades:
                emaktab_id = g.get("emaktabId")
                if not emaktab_id:
                    continue
                doc_id = f"{student_id}_{emaktab_id}"
                batch.set(
                    client.collection("grades").document(doc_id),
                    {
                        "studentId": student_id,
                        **g,
                        "source": "emaktab",
                        "syncedAt": now,
                        "createdAt": now,
                    },
                )
            batch.flush()

            # FANLAR
            if subjects:
                batch2 = BatchWriter(client)
                for s in subjects:
                    if not s.get("id"):
                        continue
                    sid_doc = f"{student_id}_{s['id']}"
                    batch2.set(
                        client.collection("subjects").document(sid_doc),
                        {
                            "studentId": student_id,
                            "classId": settings.class_id,
                            "subjectId": s["id"],
                            "name": s["name"],
                            "source": "emaktab",
                            "syncedAt": now,
                        },
                    )
                batch2.flush()
                log.info("[%s] Fanlar saqlandi: %s ta",
                         task_id[:8], len(subjects))

            # JADVAL
            if schedule:
                batch3 = BatchWriter(client)
                for lesson in schedule:
                    batch3.set(client.collection("schedule").document(), {
                        "studentId": student_id,
                        "classId": settings.class_id,
                        **lesson,
                        "source": "emaktab",
                        "syncedAt": now,
                    })
                batch3.flush()
                log.info("[%s] Jadval saqlandi: %s ta dars",
                         task_id[:8], len(schedule))

            # QUEUE
            client.collection("emaktab_queue").document(student_id).set({
                "studentId": student_id,
                "priority": 10,
                "nextAttempt": now,
                "lastAttempt": None,
                "attempts": 0,
                "lastResult": None,
                "errorMessage": "",
            })

            # LOG
            client.collection("emaktab_sync_log").add({
                "studentId": student_id,
                "status": "success",
                "method": "register",
                "gradesCount": len(grades),
                "scheduleCount": len(schedule),
                "timestamp": now,
            })

            log.info("[%s] SAQLANDI: %s (%s) - %s baho, %s fan, %s dars",
                     task_id[:8], student_id, full_name,
                     len(grades), subjects_count, len(schedule))

        except Exception as e:
            log.error("[%s] Firestore xato: %s", task_id[:8], e)
            set_status(task_id, "error",
                "Saqlashda xatolik yuz berdi.", 0, "error")
            return

        set_status(task_id, "done",
            f"{full_name} muvaffaqiyatli qo'shildi! "
            f"({len(grades)} ta baho, {subjects_count} ta fan)",
            100, "done")

        tasks[task_id]["result"] = {
            "student_id": student_id,
            "student": {
                "fullName": full_name,
                "classId": settings.class_id,
                "personId": person_id,
            },
            "gradesCount": len(grades),
            "subjectsCount": subjects_count,
            "scheduleCount": len(schedule),
        }

    except Exception as e:
        log.exception("[%s] Kutilmagan xato", task_id[:8])
        set_status(task_id, "error", "Kutilmagan xatolik yuz berdi.", 0, "error")


# ============================================================
# AUTO-SYNC — har soatda
# ============================================================
def sync_all_students():
    log.info("=" * 60)
    log.info("AUTO-SYNC boshlandi")
    log.info("=" * 60)

    try:
        client = db()
        students_snap = list(client.collection("students").stream())

        if not students_snap:
            log.info("O'quvchilar yo'q")
            return

        log.info("%s ta o'quvchi topildi", len(students_snap))

        for sdoc in students_snap:
            sid = sdoc.id
            try:
                creds = read_credentials(sid)
                if creds.get("status") == "captcha_required":
                    continue  # admin captcha yechmaguncha qayta urinmaymiz
                cookies = (
                    json.loads(decrypt(creds["cookiesEncrypted"]))
                    if creds.get("cookiesEncrypted")
                    else []
                )

                method = "cookie"
                try:
                    result = fetch_data(cookies)
                except LoginFailed:
                    log.info("[%s] Cookie tugagan, login...", sid[:12])
                    lr = login(
                        creds["login"],
                        decrypt(creds["passwordEncrypted"]),
                    )
                    cookies = lr.cookies
                    method = "login"
                    result = fetch_data(cookies)
                    save_credentials(
                        sid,
                        creds["login"],
                        decrypt(creds["passwordEncrypted"]),
                        cookies,
                    )

                new_count = save_sync(sid, result, method)

                subjects = result.get("subjects", [])

                log.info(
                    "[%s] OK: %s yangi baho, %s fan, %s dars",
                    sid[:12], new_count,
                    len(subjects),
                    len(result.get("schedule", [])),
                )
            except CaptchaRequired as ce:
                log.warning("[%s] CAPTCHA kerak", sid[:12])
                try:
                    save_captcha_to_queue(
                        sid,
                        ce.captcha_image or "",
                        ce.cookies or [],
                        ce.hidden_fields or {},
                        ce.login or creds["login"],
                        ce.password or decrypt(creds["passwordEncrypted"]),
                        ce.captcha_input_selector,
                    )
                    mark_error(sid, "captcha_required", str(ce))
                except Exception:
                    log.exception("[%s] captcha navbatga saqlanmadi", sid[:12])
            except Exception as e:
                log.error("[%s] Xato: %s", sid[:12], e)

    except Exception:
        log.exception("Auto-sync xato")


def _process_captcha_answers():
    """Admin panelda javob berilgan captchalarni qayta ishlash.

    'main.py'dagi bilan bir xil bitta-o'quvchi sync mantig'ini qayta
    ishlatish uchun shu yerda, funksiya ichida import qilinadi (aylanma
    import bo'lmasligi uchun) — shunda faqat api_server.py'ni ishga
    tushirish YETARLI: alohida 'main.py' xizmatini Railway'da qo'shimcha
    joylashtirish shart emas.
    """
    from main import sync_one
    process_answered(sync_one)


TASHKENT_TZ = timezone(timedelta(hours=5))
scheduler = BackgroundScheduler(timezone=TASHKENT_TZ)
scheduler.add_job(
    sync_all_students,
    "cron",
    hour="*",
    minute=0,
    id="hourly_sync",
    max_instances=1,
    coalesce=True,
)
scheduler.add_job(
    _process_captcha_answers,
    "interval",
    minutes=3,
    id="captcha_answers",
    max_instances=1,
    coalesce=True,
)


# ============================================================
# ROUTES
# ============================================================
@app.get("/")
def root():
    return {"status": "ok", "message": "Maktab API ishlayapti"}


@app.post("/api/register")
def register_start(req: RegisterRequest):
    log.info("=" * 60)
    log.info("YANGI RO'YXATDAN O'TISH: %s", req.login)
    log.info("Ism: %s", req.fullName)
    log.info("Rozilik: %s", req.consent)
    log.info("=" * 60)

    if not req.consent:
        raise HTTPException(400, "Foydalanish shartlariga rozilik bering")

    if not req.login or not req.password:
        raise HTTPException(400, "Login va parol majburiy")

    if not req.fullName or not req.fullName.strip():
        raise HTTPException(400, "Ism-familiya majburiy")

    if not req.phone or not req.motherPhone:
        raise HTTPException(400, "Telefon raqamlar majburiy")

    _purge_tasks()
    task_id = uuid.uuid4().hex
    _task_ts[task_id] = time.time()
    tasks[task_id] = {
        "status": "processing",
        "step": "start",
        "message": "Boshlanmoqda...",
        "progress": 0,
    }

    thread = threading.Thread(target=_run_register, args=(task_id, req))
    thread.daemon = True
    thread.start()

    return {"task_id": task_id}


@app.get("/api/register/status/{task_id}")
def register_status(task_id: str):
    if task_id not in tasks:
        raise HTTPException(404, "Task topilmadi")
    return tasks[task_id]


# SYNC NOW — faqat POST va admin token bilan (X-Admin-Token)
@app.post("/api/sync-now", dependencies=[Depends(require_admin)])
def sync_now():
    thread = threading.Thread(target=sync_all_students)
    thread.daemon = True
    thread.start()
    return {"status": "started", "message": "Sync boshlandi. Log'ni kuzatib turing."}


@app.post("/api/cleanup-orphans", dependencies=[Depends(require_admin)])
def cleanup_orphans():
    client = db()
    students_snap = list(client.collection("students").stream())
    student_ids = {s.id for s in students_snap}

    deleted = 0
    w = BatchWriter(client)
    for coll_name in ("grades", "schedule", "subjects"):
        for g in client.collection(coll_name).stream():
            sid = g.to_dict().get("studentId")
            if sid and sid not in student_ids:
                w.delete(g.reference)
                deleted += 1
    w.flush()

    log.info("Cleanup: %s ta orphan o'chirildi", deleted)
    return {"deleted": deleted}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
    )
    uvicorn.run(app, host="0.0.0.0", port=8000)