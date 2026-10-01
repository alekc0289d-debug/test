from datetime import datetime, timezone

from firebase_client import db

IDS = [
    "student_abc123",
    "student_def456",
    "student_ghi789",
    "student_jkl012",
    "student_mno345",
    "student_pqr678",
    "student_stu901",
    "student_vwx234",
    "student_yza567",
    "student_bcd890",
]


def main():
    now = datetime.now(timezone.utc)
    c = db()
    for sid in IDS:
        c.collection("emaktab_queue").document(sid).set({
            "studentId": sid,
            "priority": 5,
            "nextAttempt": now,
            "lastAttempt": None,
            "attempts": 0,
            "lastResult": None,
            "errorMessage": "",
        }, merge=True)
        print(f"OK {sid}")
    print(f"JAMI: {len(IDS)}")


if __name__ == "__main__":
    main()