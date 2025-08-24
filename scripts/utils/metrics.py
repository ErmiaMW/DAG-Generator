# utils/metrics.py
from __future__ import annotations
import re
from pathlib import Path
from typing import Dict, Optional, List
import pandas as pd


# الگوی استخراج پارامترها از خطی که شامل فلگ‌های daggen است.
# نمونه‌ی هدف:
# --ccr 0.317 --fat 0.864 --regular 0.282 --density 0.667 --jump 0.302 --mindata 1048576 --maxdata 16777216 -n 46
_PARAM_PATTERN = re.compile(
    r"--ccr\s+(?P<ccr>\d*\.?\d+)\s+"
    r"--fat\s+(?P<fat>\d*\.?\d+)\s+"
    r"--regular\s+(?P<regular>\d*\.?\d+)\s+"
    r"--density\s+(?P<density>\d*\.?\d+)\s+"
    r"--jump\s+(?P<jump>\d*\.?\d+)\s+"
    r"(?:--mindata\s+(?P<mindata>\d+)\s+--maxdata\s+(?P<maxdata>\d+)\s+)?"
    r"-n\s+(?P<n>\d+)",
    flags=re.IGNORECASE | re.MULTILINE | re.DOTALL,
)


def _extract_from_text(text: str) -> Optional[Dict[str, float]]:
    """
    از کل محتوای فایل جست‌وجو می‌کند تا اولین رخداد خط پارامترها را بیابد.
    """
    m = _PARAM_PATTERN.search(text)
    if not m:
        return None
    g = m.groupdict()

    # فقط مقادیری که لازم داریم (طبق خواسته)
    return {
        "ccr": float(g["ccr"]),
        "fat": float(g["fat"]),
        "regular": float(g["regular"]),
        "density": float(g["density"]),
        "jump": float(g["jump"]),
        "n": int(g["n"]),
        # mindata/maxdata را نمی‌ریزیم چون قرار نیست تحلیل شوند.
    }


def parse_gv_file(path: Path) -> Optional[Dict[str, float]]:
    """
    پارامترهای موردنیاز را از یک فایل .gv استخراج می‌کند.
    برمی‌گرداند: dict یا None اگر الگو پیدا نشود.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None

    data = _extract_from_text(text)
    return data


def build_dataset(root: Path) -> pd.DataFrame:
    """
    همه‌ی فایل‌های .gv را از زیرشاخه‌های root پیدا می‌کند و
    دیتافریم متریک‌ها را می‌سازد.
    ستون‌ها: file, ccr, fat, regular, density, jump, n
    """
    root = Path(root)
    rows: List[Dict] = []
    for gv_path in sorted(root.rglob("*.gv")):
        rec = parse_gv_file(gv_path)
        if rec is not None:
            rec["file"] = str(gv_path.relative_to(root))
            rows.append(rec)

    if not rows:
        return pd.DataFrame(columns=["file", "ccr", "fat", "regular", "density", "jump", "n"])

    df = pd.DataFrame(rows, columns=["file", "ccr", "fat", "regular", "density", "jump", "n"])
    # ترتیب را بر اساس مسیر فایل ثابت می‌کنیم:
    df = df.sort_values("file").reset_index(drop=True)
    return df
