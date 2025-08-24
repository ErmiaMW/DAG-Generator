# scripts/analyze_dataset.py
from __future__ import annotations
import argparse
from pathlib import Path
from utils.metrics import build_dataset
from utils.plots import plot_all_metrics, DEFAULT_METRICS


def main():
    parser = argparse.ArgumentParser(
        description="تحلیل .gv ها: استخراج n, fat, regular, density, jump, ccr و رسم نمودارها."
    )
    parser.add_argument(
        "--root",
        required=True,
        type=Path,
        help="مسیر روتی که زیر آن فایل‌های .gv ذخیره شده‌اند (مثلاً DAG/).",
    )
    parser.add_argument(
        "--outdir",
        default=Path("plots"),
        type=Path,
        help="پوشه‌ی خروجی برای ذخیره‌ی نمودارها (پیش‌فرض: plots/).",
    )
    parser.add_argument(
        "--save-csv",
        action="store_true",
        help="در صورت ست‌شدن، دیتافریم استخراج‌شده را به CSV هم ذخیره می‌کند.",
    )
    args = parser.parse_args()

    df = build_dataset(args.root)

    if df.empty:
        print(f"[warn] هیچ فایل .gv معتبری زیر مسیر '{args.root}' پیدا نشد.")
        return

    # ذخیره‌ی اختیاری CSV برای بازرسی/استفاده‌های بعدی
    if args.save_csv:
        args.outdir.mkdir(parents=True, exist_ok=True)
        csv_path = args.outdir / "metrics_extracted.csv"
        df.to_csv(csv_path, index=False)
        print(f"[info] CSV saved to: {csv_path}")

    saved = plot_all_metrics(df, args.outdir, DEFAULT_METRICS)
    for p in saved:
        print(f"[ok] plot saved: {p}")

    print(f"[done] processed {len(df)} graphs from root '{args.root}'.")


if __name__ == "__main__":
    main()
