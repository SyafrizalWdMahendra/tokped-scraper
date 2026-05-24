"""
STEP 3 — Evaluasi Komprehensif & Interpretasi Model
=====================================================
Memuat model terbaik hasil step2, lalu menjalankan evaluasi lengkap:
  - Classification report per kelas
  - Confusion matrix (numerik + heatmap)
  - ROC-AUC (OvR, macro)
  - Precision-Recall curve per kelas
  - Feature importance dari XGBoost (built-in gain)
  - Perbandingan baseline vs model tuned (jika ada)

Input  : output dari step2_gridsearch.py
Output : evaluation_report.txt, confusion_matrix.png,
         roc_curve.png, feature_importance.png
"""

import joblib
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")   # non-interactive backend (aman untuk server/script)
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    roc_curve,
    precision_recall_curve,
    average_precision_score,
)
from sklearn.preprocessing import label_binarize

# ── Path konfigurasi ───────────────────────────────────────────────────────────
SCRIPT_DIR   = Path("robust_data")
SEL_DIR      = SCRIPT_DIR / "selected"
MODEL_DIR    = SCRIPT_DIR / "models"
EVAL_DIR     = SCRIPT_DIR / "evaluation"
EVAL_DIR.mkdir(parents=True, exist_ok=True)

# ── Muat data & model ──────────────────────────────────────────────────────────
print("=" * 55)
print("STEP 3 — EVALUASI KOMPREHENSIF")
print("=" * 55)

required = {
    "X_test" : SEL_DIR   / "X_test_selected.pkl",
    "y_test" : SEL_DIR   / "y_test.pkl",
    "le"     : SEL_DIR   / "label_encoder.pkl",
    "model"  : MODEL_DIR / "xgboost_scenario3.pkl",
}

data = {}
for name, path in required.items():
    if not path.exists():
        print(f"❌ File tidak ditemukan: {path}")
        sys.exit(1)
    data[name] = joblib.load(path)
    print(f"✅ Loaded: {path.name}")

X_test     = data["X_test"]
y_test     = data["y_test"]
le         = data["le"]
best_model = data["model"]

classes    = le.classes_.astype(str)
n_classes  = len(classes)

y_pred      = best_model.predict(X_test)
y_prob      = best_model.predict_proba(X_test)

y_test_lbl  = le.inverse_transform(y_test).astype(str)
y_pred_lbl  = le.inverse_transform(y_pred).astype(str)

# ── 1. Classification Report ───────────────────────────────────────────────────
print("\n" + "=" * 55)
print("1. CLASSIFICATION REPORT")
print("=" * 55)
report_str = classification_report(y_test_lbl, y_pred_lbl)
print(report_str)

# ── 2. ROC-AUC (One-vs-Rest, macro) ───────────────────────────────────────────
y_test_bin = label_binarize(y_test, classes=np.arange(n_classes))
auc_macro  = roc_auc_score(y_test_bin, y_prob, multi_class="ovr", average="macro")
auc_weighted = roc_auc_score(y_test_bin, y_prob, multi_class="ovr", average="weighted")

print(f"ROC-AUC (macro)    : {auc_macro:.4f}")
print(f"ROC-AUC (weighted) : {auc_weighted:.4f}")

# ── 3. Confusion Matrix heatmap ────────────────────────────────────────────────
cm = confusion_matrix(y_test_lbl, y_pred_lbl, labels=classes)

fig, ax = plt.subplots(figsize=(7, 5))
sns.heatmap(
    cm, annot=True, fmt="d", cmap="Blues",
    xticklabels=classes, yticklabels=classes,
    linewidths=0.5, ax=ax,
)
ax.set_xlabel("Prediksi",  fontsize=12)
ax.set_ylabel("Aktual",    fontsize=12)
ax.set_title("Confusion Matrix — XGBoost Scenario 3", fontsize=13, pad=12)
plt.tight_layout()
cm_path = EVAL_DIR / "confusion_matrix.png"
plt.savefig(cm_path, dpi=150)
plt.close()
print(f"\n📊 Confusion matrix disimpan: {cm_path}")

# ── 4. ROC Curve per kelas ─────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(7, 5))
colors = ["#4C72B0", "#DD8452", "#55A868"]

for i, (cls, color) in enumerate(zip(classes, colors)):
    fpr, tpr, _ = roc_curve(y_test_bin[:, i], y_prob[:, i])
    auc_cls     = roc_auc_score(y_test_bin[:, i], y_prob[:, i])
    ax.plot(fpr, tpr, color=color, lw=2,
            label=f"{cls} (AUC = {auc_cls:.3f})")

ax.plot([0, 1], [0, 1], "k--", lw=1, alpha=0.5, label="Random")
ax.set_xlabel("False Positive Rate", fontsize=11)
ax.set_ylabel("True Positive Rate",  fontsize=11)
ax.set_title("ROC Curve per Kelas (OvR)", fontsize=13, pad=12)
ax.legend(loc="lower right", fontsize=10)
ax.set_xlim([0, 1])
ax.set_ylim([0, 1.02])
plt.tight_layout()
roc_path = EVAL_DIR / "roc_curve.png"
plt.savefig(roc_path, dpi=150)
plt.close()
print(f"📊 ROC curve disimpan     : {roc_path}")

# ── 5. Precision-Recall Curve per kelas ───────────────────────────────────────
fig, ax = plt.subplots(figsize=(7, 5))

for i, (cls, color) in enumerate(zip(classes, colors)):
    precision, recall, _ = precision_recall_curve(y_test_bin[:, i], y_prob[:, i])
    ap = average_precision_score(y_test_bin[:, i], y_prob[:, i])
    ax.plot(recall, precision, color=color, lw=2,
            label=f"{cls} (AP = {ap:.3f})")

ax.set_xlabel("Recall",    fontsize=11)
ax.set_ylabel("Precision", fontsize=11)
ax.set_title("Precision-Recall Curve per Kelas", fontsize=13, pad=12)
ax.legend(loc="upper right", fontsize=10)
ax.set_xlim([0, 1])
ax.set_ylim([0, 1.02])
plt.tight_layout()
pr_path = EVAL_DIR / "precision_recall_curve.png"
plt.savefig(pr_path, dpi=150)
plt.close()
print(f"📊 PR curve disimpan      : {pr_path}")

# ── 6. Feature Importance (XGBoost gain) ──────────────────────────────────────
# best_model adalah ImbPipeline → ambil step 'clf' untuk akses XGBClassifier
xgb_clf = best_model.named_steps["clf"]
importances = xgb_clf.feature_importances_   # gain-based

top_n = 25
top_idx = np.argsort(importances)[::-1][:top_n]
top_imp = importances[top_idx]
top_lbl = [f"fitur_{i}" for i in top_idx]   # ganti dengan nama asli jika tersedia

fig, ax = plt.subplots(figsize=(8, 7))
colors_bar = plt.cm.viridis(np.linspace(0.2, 0.85, top_n))
bars = ax.barh(range(top_n), top_imp[::-1], color=colors_bar[::-1])
ax.set_yticks(range(top_n))
ax.set_yticklabels(top_lbl[::-1], fontsize=9)
ax.set_xlabel("Importance (gain)", fontsize=11)
ax.set_title(f"Top {top_n} Feature Importance — XGBoost", fontsize=13, pad=12)
ax.invert_yaxis()
plt.tight_layout()
fi_path = EVAL_DIR / "feature_importance.png"
plt.savefig(fi_path, dpi=150)
plt.close()
print(f"📊 Feature importance disimpan: {fi_path}")

# ── 7. Simpan ringkasan evaluasi ke teks ───────────────────────────────────────
summary_lines = [
    "=" * 55,
    "RINGKASAN EVALUASI — XGBoost Scenario 3",
    "=" * 55,
    "",
    "Classification Report:",
    report_str,
    "",
    f"ROC-AUC (macro)    : {auc_macro:.4f}",
    f"ROC-AUC (weighted) : {auc_weighted:.4f}",
    "",
    "Confusion Matrix:",
    pd.DataFrame(
        cm,
        index=[f"Aktual: {c}" for c in classes],
        columns=[f"Pred: {c}" for c in classes],
    ).to_string(),
]

report_path = EVAL_DIR / "evaluation_report.txt"
report_path.write_text("\n".join(summary_lines), encoding="utf-8")
print(f"\n📝 Laporan evaluasi disimpan: {report_path}")

print("\n" + "=" * 55)
print("✅ STEP 3 SELESAI — Semua output ada di folder evaluation/")
print("=" * 55)