import datetime
import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data.fetch import fetch_game_pks, fetch_box_score

def backfill(start_date, end_date):
    current = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
    end     = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
    total_days = (end - current).days + 1
    day_num = 0

    print(f"\n=== Backfilling {start_date} to {end_date} ({total_days} days) ===\n")

    while current <= end:
        date_str = current.strftime('%Y-%m-%d')
        day_num += 1
        print(f"[{day_num}/{total_days}] {date_str}", end=' ... ', flush=True)

        try:
            pks = fetch_game_pks(date_str)
            if pks:
                for pk in pks:
                    for attempt in range(3):
                        try:
                            fetch_box_score(pk, date_str)
                            break
                        except Exception as e:
                            if attempt < 2:
                                print(f"retry {attempt+1} game {pk}...", end=' ', flush=True)
                                time.sleep(3)
                            else:
                                print(f"skipped game {pk} after 3 attempts")
                print(f"{len(pks)} games")
            else:
                print("no games")
        except Exception as e:
            print(f"ERROR: {e} — skipping day")

        time.sleep(1.5)
        current += datetime.timedelta(days=1)

    print("\n=== Backfill complete ===\n")

if __name__ == '__main__':
    # Resume from April 1 since March 25-31 already saved
    backfill('2026-04-01', '2026-04-29')
