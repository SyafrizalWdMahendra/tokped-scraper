"""
STEP 1 — Seleksi Fitur dengan Chi-Square
=========================================
Urutan yang benar:
  Chi-Square HARUS dijalankan SEBELUM SMOTE dan SEBELUM GridSearch.
  Alasan:
  - Chi-Square mengukur hubungan fitur asli vs target asli (distribusi nyata).
  - Jika Chi-Square dijalankan SETELAH SMOTE, fitur dipilih berdasarkan data
    sintetis yang tidak merepresentasikan distribusi sesungguhnya → bias seleksi.
  - Hasilnya disimpan ke disk agar step2 dan step3 bisa memuat langsung.

Output:
  - X_train_selected.pkl  → data train setelah seleksi fitur
  - X_test_selected.pkl   → data test  setelah seleksi fitur (transform only!)
  - selector.pkl          → objek SelectKBest yang sudah fit
  - selected_feature_report.csv → skor chi2 dan p-value tiap fitur terpilih
"""

import joblib
import sys
import numpy as np
import pandas as pd
from pathlib import Path
from scipy.sparse import issparse
from sklearn.feature_selection import SelectKBest, chi2

# ── Path konfigurasi ───────────────────────────────────────────────────────────
SCRIPT_DIR   = Path("robust_data")
TOK_DIR      = SCRIPT_DIR / "tokenize"
OUT_DIR      = SCRIPT_DIR / "selected"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PATHS = {
    "X_train": TOK_DIR / "X_train_tfidf.pkl",
    "y_train": TOK_DIR / "y_train.pkl",
    "X_test":  TOK_DIR / "X_test_tfidf.pkl",
    "y_test":  TOK_DIR / "y_test.pkl",
    "le":      TOK_DIR / "label_encoder.pkl",
}

K_FEATURES = 2000   # jumlah fitur terbaik yang dipilih

# ── Muat data ──────────────────────────────────────────────────────────────────
print("=" * 55)
print("STEP 1 — CHI-SQUARE FEATURE SELECTION")
print("=" * 55)

data = {}
for name, path in PATHS.items():
    if not path.exists():
        print(f"❌ File tidak ditemukan: {path}")
        sys.exit(1)
    data[name] = joblib.load(path)
    print(f"✅ Loaded: {path.name}")

X_train = data["X_train"]
y_train = data["y_train"]
X_test  = data["X_test"]
y_test  = data["y_test"]
le      = data["le"]

print(f"\nDimensi awal  X_train : {X_train.shape}")
print(f"Dimensi awal  X_test  : {X_test.shape}")

# ── Validasi: Chi-Square butuh nilai non-negatif ───────────────────────────────
# TF-IDF secara definisi selalu >= 0, tapi kita cek tetap untuk keamanan.
if issparse(X_train):
    min_val = X_train.min()
else:
    min_val = np.min(X_train)

if min_val < 0:
    print(f"\n⚠️  Nilai minimum: {min_val:.4f} — menggeser ke non-negatif.")
    X_train = X_train - min_val
    X_test  = X_test  - min_val
else:
    print(f"\n✅ Nilai minimum {min_val:.4f} — sudah non-negatif, aman untuk Chi-Square.")

# ── Fit SelectKBest pada DATA TRAIN ASLI (sebelum SMOTE) ──────────────────────
print(f"\nFit SelectKBest(chi2, k={K_FEATURES}) pada X_train asli...")
selector = SelectKBest(score_func=chi2, k=K_FEATURES)

# fit HANYA pada X_train (distribusi asli, bukan sintetis)
selector.fit(X_train, y_train)

# transform X_train dan X_test
X_train_sel = selector.transform(X_train)
X_test_sel  = selector.transform(X_test)   # transform only! tidak fit ulang

print(f"Dimensi setelah seleksi  X_train : {X_train_sel.shape}")
print(f"Dimensi setelah seleksi  X_test  : {X_test_sel.shape}")

# ── Laporan skor fitur terpilih ────────────────────────────────────────────────
support_mask = selector.get_support()
all_scores   = selector.scores_
all_pvalues  = selector.pvalues_

report_df = pd.DataFrame({
    "fitur_index": np.where(support_mask)[0],
    "chi2_score" : all_scores[support_mask],
    "p_value"    : all_pvalues[support_mask],
}).sort_values("chi2_score", ascending=False).reset_index(drop=True)

report_path = OUT_DIR / "selected_feature_report.csv"
report_df.to_csv(report_path, index=False)

print(f"\nTop 10 fitur berdasarkan skor Chi-Square:")
print(report_df.head(10).to_string(index=False))
print(f"\nLaporan lengkap disimpan: {report_path}")

# Fitur yang dibuang (p-value tinggi = tidak signifikan)
n_dropped = X_train.shape[1] - K_FEATURES
print(f"\nFitur dibuang : {n_dropped:,}  (tidak signifikan secara statistik)")
print(f"Fitur tersisa : {K_FEATURES:,}")

# ── Simpan output ──────────────────────────────────────────────────────────────
joblib.dump(X_train_sel, OUT_DIR / "X_train_selected.pkl")
joblib.dump(X_test_sel,  OUT_DIR / "X_test_selected.pkl")
joblib.dump(selector,    OUT_DIR / "selector.pkl")

# Salin y dan le agar step2/3 tidak perlu akses ke folder tokenize
joblib.dump(y_train, OUT_DIR / "y_train.pkl")
joblib.dump(y_test,  OUT_DIR / "y_test.pkl")
joblib.dump(le,      OUT_DIR / "label_encoder.pkl")

print(f"\n💾 Semua output disimpan di: {OUT_DIR}")
print("\n✅ STEP 1 SELESAI — Lanjut ke step2_gridsearch.py")