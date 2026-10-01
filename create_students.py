from datetime import datetime, timezone

from firebase_client import db

STUDENTS = [
    {"id": "student_abc123", "fullName": "Ozodbek Karimov", "classId": "9-A"},
    {"id": "student_def456", "fullName": "Ali Valiyev", "classId": "9-A"},
    {"id": "student_ghi789", "fullName": "Laylo Rahimova", "classId": "9-A"},
    {"id": "student_jkl012", "fullName": "Jasur Toshmatov", "classId": "9-A"},
    {"id": "student_mno345", "fullName": "Dilnoza Yusupova", "classId": "9-A"},
    {"id": "student_pqr678", "fullName": "Sardor Aliyev", "classId": "9-A"},
    {"id": "student_stu901", "fullName": "Madina Tursunova", "classId": "9-A"},
    {"id": "student_vwx234", "fullName": "Bobur Karimov", "classId": "9-A"},
    {"id": "student_yza567", "fullName": "Nilufar Sattorova", "classId": "9-A"},
    {"id": "student_bcd890", "fullName": "Rustam Abdullayev", "classId": "9-A"},
]


def main():
    now = datetime.now(timezone.utc)
    c = db()
    for s in STUDENTS:
        c.collection("students").document(s["id"]).set({
            "fullName": s["fullName"],
            "classId": s["classId"],
            "createdAt": now,
            "updatedAt": now,
        }, merge=True)
        print(f"OK {s['id']}")
    print(f"JAMI: {len(STUDENTS)}")


if __name__ == "__main__":
    main()