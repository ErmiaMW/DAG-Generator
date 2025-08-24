# utils/plots.py
from __future__ import annotations
from pathlib import Path
from typing import Iterable, List
import matplotlib.pyplot as plt
import pandas as pd


DEFAULT_METRICS: List[str] = ["n", "fat", "regular", "density", "jump", "ccr"]


def _ensure_outdir(outdir: Path) -> Path:
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    return outdir


def plot_metric_over_files(df: pd.DataFrame, metric: str, outdir: Path) -> Path:
    """
    یک نمودار ساده‌ی مقدار متریک بر حسب ایندکس فایل‌ها می‌کشد.
    محور x: شماره نمونه (مرتب شده بر اساس نام فایل)
    محور y: مقدار متریک
    """
    outdir = _ensure_outdir(outdir)
    if metric not in df.columns:
        raise ValueError(f"Metric '{metric}' not found in dataframe columns: {list(df.columns)}")

    y = df[metric].values
    x = range(1, len(y) + 1)

    plt.figure(figsize=(25, 10))
    plt.scatter(list(x), list(y), marker="o")
    plt.title(f"{metric} over .gv files")
    plt.xlabel("graph index (sorted by file path)")
    plt.ylabel(metric)
    plt.grid(True, linestyle="--", alpha=0.4)
    out_path = outdir / f"{metric}.png"
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    return out_path


def plot_all_metrics(df: pd.DataFrame, outdir: Path, metrics: Iterable[str] = DEFAULT_METRICS) -> List[Path]:
    """
    برای همه‌ی متریک‌ها نمودار ذخیره می‌کند.
    """
    saved: List[Path] = []
    for m in metrics:
        saved.append(plot_metric_over_files(df, m, outdir))
    return saved
