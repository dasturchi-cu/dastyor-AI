#!/usr/bin/env python3
"""
Contabo serverdagi payments jadvalini tozalash va ID sequence ni 0 ga qaytarish.
Ishlatish (Contabo serverda):
    docker exec dastyor-ai python /opt/dastyor-ai/scripts/reset_payments.py
"""
from __future__ import annotations

import sys
import os

# DATA_DIR ni to'g'ri o'rnatish
os.environ.setdefault("DATA_DIR", "/data")
os.environ.setdefault("PRODUCTION", "1")

try:
    from database.connection import get_connection
except ImportError as e:
    print(f"❌ Import xatosi: {e}")
    print("  Docker container ichida ishga tushiryapsizmi?")
    sys.exit(1)

def main() -> None:
    print("=" * 55)
    print("  DASTYOR AI — Payments Reset")
    print("=" * 55)

    with get_connection() as conn:
        # Hozirgi holat
        count = conn.execute("SELECT COUNT(*) FROM payments").fetchone()[0]
        seq_row = conn.execute(
            "SELECT seq FROM sqlite_sequence WHERE name='payments'"
        ).fetchone()
        current_seq = seq_row[0] if seq_row else "yo'q"
        max_id_row = conn.execute("SELECT MAX(id) FROM payments").fetchone()
        max_id = max_id_row[0] if max_id_row and max_id_row[0] is not None else 0

        print(f"\n📊 Hozirgi holat:")
        print(f"   Jami to'lovlar : {count} ta")
        print(f"   Eng katta ID   : {max_id}")
        print(f"   Sequence (auto): {current_seq}")

        if count == 0:
            print("\n✅ To'lovlar jadvali allaqachon bo'sh.")
            print("   Sequence qayta o'rnatilmoqda...")
            conn.execute("DELETE FROM sqlite_sequence WHERE name='payments'")
            print("   ✅ Sequence 0 ga o'rnatildi. Keyingi to'lov #1 bo'ladi.")
            return

        # Tasdiqlash
        print(f"\n⚠️  {count} ta to'lov o'chiriladi. Bu amalni qaytarib bo'lmaydi!")
        answer = input("   Davom etasizmi? (ha/yo'q): ").strip().lower()
        if answer not in ("ha", "h", "yes", "y"):
            print("\n❌ Bekor qilindi.")
            return

        # O'chirish
        conn.execute("DELETE FROM payments")
        conn.execute("DELETE FROM sqlite_sequence WHERE name='payments'")

        # Tekshirish
        new_count = conn.execute("SELECT COUNT(*) FROM payments").fetchone()[0]
        new_seq = conn.execute(
            "SELECT seq FROM sqlite_sequence WHERE name='payments'"
        ).fetchone()

        print(f"\n✅ Muvaffaqiyatli!")
        print(f"   O'chirildi       : {count} ta to'lov")
        print(f"   Qolgan           : {new_count} ta")
        print(f"   Sequence         : {new_seq[0] if new_seq else '0 (tozalandi)'}")
        print(f"   Keyingi to'lov   : #1 dan boshlanadi")

    print("\n" + "=" * 55)
    print("  Tugadi!")
    print("=" * 55)


if __name__ == "__main__":
    main()
