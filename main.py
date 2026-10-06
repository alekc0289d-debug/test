import argparse
import json
import logging
import time
import traceback
from datetime import timedelta, timezone

from apscheduler.schedulers.blocking import BlockingScheduler

from crypto import decrypt
from emaktab import CaptchaRequired, LoginFailed, fetch_data, login
from captcha_flow import process_answered
from config import settings
from firebase_client import (
    mark_error,
    next_queue,
    read_credentials,
    save_captcha_to_queue,
    save_cookies,
    save_sync,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("worker")

CLASS_ID = settings.class_id
BATCH = settings.batch_size


def sync_one(sid):
    log.info("=" * 60)
    log.info("BOSHLANDI: %s", sid)
    log.info("=" * 60)

    try:
        c = read_credentials(sid)
        log.info("Credential o'qildi: %s", c.get("login"))
    except Exception as e:
        log.error("Credential o'qishda xato:")
        log.error(traceback.format_exc())
        return {"sid": sid, "status": "cred_error"}

    ck = (
        json.loads(decrypt(c["cookiesEncrypted"]))
        if c.get("cookiesEncrypted")
        else []
    )
    log.info("Cookie soni: %s", len(ck))

    m = "cookie"
    try:
        try:
            log.info("Cookie bilan urinish...")
            r = fetch_data(ck)
            log.info("Cookie ishladi")
        except LoginFailed as lf:
            log.info("Cookie ishlamadi: %s", lf)
            log.info("Login-parol bilan urinish...")
            try:
                lr = login(c["login"], decrypt(c["passwordEncrypted"]))
                log.info("Login muvaffaqiyatli")
                ck, m = lr.cookies, "login"
                r = fetch_data(ck)
                save_cookies(sid, ck)
            except CaptchaRequired:
                raise
            except Exception as inner:
                log.error("Login xatosi:")
                log.error(traceback.format_exc())
                raise inner

        save_sync(sid, r, m)
        log.info("OK %s (%s baho)", sid, len(r["grades"]))
        return {"sid": sid, "status": "success"}

    except CaptchaRequired as e:
        log.warning("CAPTCHA aniqlandi: %s", sid)
        try:
            save_captcha_to_queue(
                sid,
                e.captcha_image or "",
                e.cookies or [],
                e.hidden_fields or {},
                e.login or c["login"],
                e.password or decrypt(c["passwordEncrypted"]),
                e.captcha_input_selector,
            )
            log.warning("CAPTCHA navbatga saqlandi: %s", sid)
        except Exception as ex:
            log.error("Captcha saqlashda xato:")
            log.error(traceback.format_exc())
        mark_error(sid, "captcha_required", str(e))
        return {"sid": sid, "status": "captcha_required"}

    except Exception as e:
        log.error("=" * 60)
        log.error("TO'LIQ XATO: %s", sid)
        log.error("=" * 60)
        log.error("Xato turi: %s", type(e).__name__)
        log.error("Xato matni: %s", str(e))
        log.error("-" * 60)
        log.error("TRACEBACK:")
        log.error(traceback.format_exc())
        log.error("=" * 60)
        mark_error(sid, "error", type(e).__name__)
        return {"sid": sid, "status": "error"}


def sync_queue(limit=BATCH, class_id=CLASS_ID):
    q = next_queue(limit, class_id)
    log.info("=" * 60)
    log.info("NAVBAT: %s ta (sinf: %s)", len(q), class_id)
    log.info("=" * 60)
    for it in q:
        sync_one(it.id)
        time.sleep(5)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--test", action="store_true")
    p.add_argument("--student-id")
    p.add_argument("--class", dest="class_id", default=CLASS_ID)
    p.add_argument("--once", action="store_true")
    p.add_argument("--captcha", action="store_true",
                   help="Admin panelda javob berilgan captchalarni qayta ishlash")
    a = p.parse_args()

    if a.test:
        if not a.student_id:
            p.error("--student-id kerak")
        sync_one(a.student_id)
        return

    if a.captcha:
        log.info("Captcha yechildi: %s ta", process_answered(sync_one))
        return

    if a.once:
        sync_queue(BATCH, a.class_id)
        return

    s = BlockingScheduler(timezone=timezone(timedelta(hours=5)))
    s.add_job(
        sync_queue,
        "cron",
        hour="*",
        minute=0,
        id="hourly",
        max_instances=1,
        coalesce=True,
    )
    s.add_job(
        lambda: process_answered(sync_one),
        "interval",
        minutes=3,
        id="captcha_answers",
        max_instances=1,
        coalesce=True,
    )
    log.info("Worker (sinf: %s, %s ta/soat)", a.class_id, BATCH)
    s.start()


if __name__ == "__main__":
    main()