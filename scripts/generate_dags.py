# scripts/generate_dags_c.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse, os, random, subprocess, sys, time, json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import yaml
import re

NODE_RE = re.compile(r'^(\s*)(\d+)\s+\[size="(\d+)",\s*alpha="([0-9.]+)"\s*\](\s*)$')
CMD_RE = re.compile(r'^\s*//\s.*\bdaggen\b.*$', re.IGNORECASE)

def run_cmd(cmd: str) -> str:
    p = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"[daggen failed]\nCMD: {cmd}\nSTDERR:\n{p.stderr.strip()}")
    return p.stdout

def sample_uniform(lo, hi): return random.uniform(float(lo), float(hi))
def sample_int(lo, hi): return random.randint(int(lo), int(hi))

def tier_range_label(lo, hi): return f"{int(lo)}-{int(hi)}"

def build_cmd(daggen_bin: str, n: int, ccr: float, fat: float, density: float,
              regular: float, jump: float, mindata: int, maxdata: int) -> str:
    # نکته: -n کوتاه؛ بقیه long-opts
    return (
        f'{daggen_bin} --dot '
        f'--ccr {ccr:.3f} '
        f'--fat {fat:.3f} '
        f'--regular {regular:.3f} '
        f'--density {density:.3f} '
        f'--jump {jump:.3f} '
        f'--mindata {int(mindata)} '
        f'--maxdata {int(maxdata)} '
        f'-n {int(n)}'
    )

# def strip_cmd_line(dag_out: str) -> str:
#     lines = dag_out.splitlines()
#     kept = [ln for ln in lines if not CMD_RE.match(ln)]
#     return "\n".join(kept) + ("\n" if kept and not kept[-1].endswith("\n") else "")
def file_header(tier: str, mode: str, n: int, ccr: float, fat: float, density: float,
                regular: float, jump: float, mindata: int, maxdata: int) -> str:
    return (
        f"// DAG (tier={tier}, mode={mode}, n={n}, ccr={ccr:.3f}, fat={fat:.3f}, "
        f"density={density:.3f}, regular={regular:.3f}, jump={jump:.3f}, "
        f"mindata={mindata}, maxdata={maxdata})\n"
    )

def add_expect_size_to_nodes(dag_text: str, use_alpha: bool = False) -> str:
    """
    اگر use_alpha=False: expect_size = size // 2   (سازگار با مقاله)
    اگر use_alpha=True : expect_size = int(round(size * (1 - alpha)))  (رویکرد معنادار/modern)
    """
    out_lines = []
    for line in dag_text.splitlines():
        m = NODE_RE.match(line)
        if m:
            indent, node_id, size_str, alpha_str, trail = m.groups()
            size  = int(size_str)
            alpha = float(alpha_str)
            if use_alpha:
                expect_size = max(1, int(round(size * (1.0 - alpha))))
            else:
                expect_size = size // 2
            # بازنویسی خط نود با expect_size
            new_line = f'{indent}{node_id} [size="{size}", alpha="{alpha:.2f}", expect_size="{expect_size}"]{trail}'
            out_lines.append(new_line)
        else:
            out_lines.append(line)
    return "\n".join(out_lines) + ("\n" if not dag_text.endswith("\n") else "")
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/presets_c.yaml")
    ap.add_argument("--outdir", default="dags")
    ap.add_argument("--workers", type=int, default=os.cpu_count())
    ap.add_argument("--seed", type=int, default=None)  # فقط برای نمونه‌گیری داخل پایتون
    args = ap.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    random.seed(args.seed if args.seed is not None else cfg["global"].get("seed_base", 4242))

    daggen_bin = os.path.expandvars(cfg["global"]["daggen_bin"])
    if not Path(daggen_bin).exists():
        print(f"[FATAL] daggen binary not found at: {daggen_bin}", file=sys.stderr)
        sys.exit(1)

    graphs_per = int(cfg["global"]["graphs_per_subfolder"])
    subs_per   = int(cfg["global"]["subfolders_per_tier"])

    out_root = Path(args.outdir); out_root.mkdir(parents=True, exist_ok=True)

    label_map = {
        "1-easy":   tier_range_label(*cfg["tiers"]["1-easy"]["n"]),
        "2-normal": tier_range_label(*cfg["tiers"]["2-normal"]["n"]),
        "3-complex":tier_range_label(*cfg["tiers"]["3-complex"]["n"]),
    }

    jobs = []
    for tier, spec in cfg["tiers"].items():
        tier_root = out_root / tier
        tier_root.mkdir(parents=True, exist_ok=True)

        for sub_idx in range(1, subs_per + 1):
            mode = "compute" if sub_idx <= subs_per // 2 else "data"
            tag  = 'c' if mode == "compute" else 'd'
            sub  = tier_root / f"offload_{tier}_{tag}{sub_idx:02d}"
            sub.mkdir(parents=True, exist_ok=True)

            # پارامترهای مشترک tier
            n_lo, n_hi       = spec["n"]
            fat_lo, fat_hi   = spec["fat"]
            den_lo, den_hi   = spec["density"]
            reg_lo, reg_hi   = spec["regular"]
            j_lo, j_hi       = spec["jump"]

            preset = spec[mode]
            ccr_lo, ccr_hi   = preset["ccr"]
            mindata          = int(preset["mindata"])
            maxdata          = int(preset["maxdata"])

            for j in range(1, graphs_per + 1):
                n        = sample_int(n_lo, n_hi)
                fat      = sample_uniform(fat_lo, fat_hi)
                density  = sample_uniform(den_lo, den_hi)
                regular  = sample_uniform(reg_lo, reg_hi)
                jump     = sample_uniform(j_lo, j_hi)
                ccr      = sample_uniform(ccr_lo, ccr_hi)

                cmd = build_cmd(daggen_bin, n, ccr, fat, density, regular, jump, mindata, maxdata)
                out_name = f"random.{label_map[tier]}.{j}.gv"
                out_path = sub / out_name
                jobs.append((cmd, tier, mode, n, ccr, fat, density, regular, jump, mindata, maxdata, out_path))

    ok = 0
    def _do_job(job):
        cmd, tier, mode, n, ccr, fat, density, regular, jump, mindata, maxdata, out_path = job
        raw = run_cmd(cmd)
        # raw = strip_cmd_line(raw)
        # اضافه کردن هدر یک‌خطی در ابتدای فایل
        raw = add_expect_size_to_nodes(raw, use_alpha=False)  # برای سازگاری با مقاله، False بماند
        hdr = file_header(tier, mode, n, ccr, fat, density, regular, jump, mindata, maxdata)
        Path(out_path).write_text(hdr + raw, encoding="utf-8")

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(_do_job, jb) for jb in jobs]
        for idx, f in enumerate(as_completed(futs), 1):
            try:
                f.result(); ok += 1
            except Exception as e:
                print("[ERR]", e, file=sys.stderr)
            if idx % 100 == 0:
                print(f"[prog] {idx}/{len(jobs)}")

    print(f"[DONE] generated {ok}/{len(jobs)} DAGs under {out_root}")

if __name__ == "__main__":
    main()
