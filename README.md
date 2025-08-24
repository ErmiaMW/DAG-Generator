# DAG Bench for AV Offloading

## Generate
```bash
python scripts/generate_dags.py --config configs/presets.yaml --outdir dags --workers 8



python scripts/audit_dags.py \
  --roots dags/easy dags/normal dags/complex \
  --ue-hz 1e9 --mec-hz 1e10 --up-mbps 8.5 --dl-mbps 8.5




python scripts/generate_dags.py --config configs/presets.yaml --outdir dags


-->>>>>>>>>>>>.
 python scripts/generate_dags.py --config configs/presets.yaml --outdir dags --workers 8
python scripts/analyze_dataset.py --root dags/ --outdir plots