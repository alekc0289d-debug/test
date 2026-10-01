import argparse
import json

from firebase_client import save_credentials


def main():
    p = argparse.ArgumentParser()
    p.add_argument("path", nargs="?", default="credentials.json")
    a = p.parse_args()
    with open(a.path, encoding="utf-8") as f:
        recs = json.load(f)
    if isinstance(recs, dict):
        recs = [recs]
    for r in recs:
        save_credentials(r["student_id"], r["login"], r["password"], [])
        print(f"OK {r['student_id']}")


if __name__ == "__main__":
    main()