"""
run_all.py — Jalankan seluruh pipeline sekaligus
=================================================
Urutan eksekusi:
  1. step1_feature_selection.py  → Chi-Square pada data asli
  2. step2_gridsearch.py         → SMOTE (dalam CV) + Grid Search XGBoost
  3. step3_evaluation.py         → Evaluasi & visualisasi

Cara pakai:
  python run_all.py
"""

import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path("new_pipeline")

steps = [
    ("STEP 1", SCRIPTS_DIR / "chi2.py"),
    ("STEP 2", SCRIPTS_DIR / "grid_s.py"),
    ("STEP 3", SCRIPTS_DIR / "evaluation.py"),
]

for label, script in steps:
    print(f"\n{'='*55}")
    print(f"▶  Menjalankan {label}: {script.name}")
    print(f"{'='*55}")

    result = subprocess.run(
        [sys.executable, str(script)],
        check=False,
    )

    if result.returncode != 0:
        print(f"\n❌ {label} gagal (exit code {result.returncode}). Pipeline dihentikan.")
        sys.exit(result.returncode)

    print(f"\n✅ {label} selesai.")

print(f"\n{'='*55}")
print("🎉  SELURUH PIPELINE SELESAI")
print(f"{'='*55}")