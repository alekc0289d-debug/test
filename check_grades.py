from collections import Counter

from firebase_client import db


def main():
    gs = list(
        db()
        .collection("grades")
        .where("source", "==", "emaktab")
        .stream()
    )
    bs = Counter()
    bsub = Counter()
    for g in gs:
        d = g.to_dict()
        bs[d.get("studentId", "?")] += 1
        bsub[d.get("subject", "?")] += 1
    print("\nSTATISTIKA\n" + "=" * 50)
    print("\nOquvchilar:")
    for s, n in sorted(bs.items()):
        print(f"  {s}: {n} ta")
    print("\nFanlar:")
    for s, n in sorted(bsub.items()):
        print(f"  {s}: {n} ta")
    print(f"\nJAMI: {sum(bs.values())} ta baho")


if __name__ == "__main__":
    main()