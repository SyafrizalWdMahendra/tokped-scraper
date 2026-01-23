
import joblib
import sys
import time
import pandas as pd
from pathlib import Path
from xgboost import XGBClassifier
from sklearn.model_selection import GridSearchCV
from sklearn.feature_selection import SelectKBest, chi2
from sklearn.metrics import classification_report, confusion_matrix
from imblearn.pipeline import Pipeline as ImbPipeline 
from imblearn.over_sampling import SMOTE

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
DATA_DIR = PROJECT_ROOT / "data"

# PERUBAHAN PENTING:
# Kita load data MURNI (TF-IDF), bukan data yang sudah di-SMOTE secara manual.
PATHS = {
    "X_train": DATA_DIR / "tokenize" / "train" / "X_train_tfidf.pkl", # Data TF-IDF Asli
    "y_train": DATA_DIR / "tokenize" / "train" / "y_train.pkl",       # Label Asli
    "X_test":  DATA_DIR / "tokenize" / "test" / "X_test_tfidf.pkl",   # Data Test TF-IDF Asli
    "y_test":  DATA_DIR / "tokenize" / "test" / "y_test.pkl",
    "le":      DATA_DIR / "tokenize" / "label_encoder.pkl",
}

print("--- MENYIAPKAN TRAINING SCENARIO 3 (PIPELINE: SMOTE + CHI2 + XGBOOST) ---")

data = {}
for name, path in PATHS.items():
    if not path.exists():
        print(f"❌ ERROR: File tidak ditemukan → {path}")
        print("Pastikan kamu me-load file TF-IDF murni, bukan file output SMOTE manual.")
        sys.exit(1)
    data[name] = joblib.load(path)
    print(f"✅ Loaded: {path}")

X_train, y_train = data["X_train"], data["y_train"]
X_test, y_test = data["X_test"], data["y_test"]
le = data["le"]

print(f"\nDimensi Training Awal (Sebelum SMOTE/Chi2): {X_train.shape}")
# Harusnya jumlah fiturnya masih banyak (misal: 5000+)

# ==========================================
# DEFINISI PIPELINE
# ==========================================
# Inilah "Jantung" Skenario 3 kamu.
# Pipeline ini membungkus 3 proses menjadi 1 kesatuan agar tidak bocor.
pipeline = ImbPipeline([
    ('smote', SMOTE(random_state=42)),              # Langkah 1: SMOTE
    ('selector', SelectKBest(score_func=chi2, k=1000)), # Langkah 2: Chi-Square (Ambil 1000 fitur terbaik)
    ('clf', XGBClassifier(                          # Langkah 3: XGBoost
        objective='multi:softprob',
        num_class=3,
        random_state=42,
        eval_metric='mlogloss',
        use_label_encoder=False
    ))
])

# ==========================================
# SETTING GRID SEARCH
# ==========================================
# Perhatikan penulisan parameter: harus pakai prefix "clf__" (nama langkah di pipeline)
param_grid = {
    'clf__learning_rate': [0.1, 0.2],
    'clf__max_depth': [5, 7],
    'clf__n_estimators': [100, 200],
    'clf__subsample': [0.8, 1.0],
    # Opsional: Kamu bahkan bisa tuning jumlah fitur chi-square juga!
    # 'selector__k': [500, 1000, 1500] 
}

# Inisialisasi Grid Search
grid_search = GridSearchCV(
    estimator=pipeline,     # Masukkan pipeline, bukan model XGBoost langsung
    param_grid=param_grid,
    cv=3,                   # 3-Fold Cross Validation
    scoring='f1_macro',     # Metrik paling penting untuk imbalance data
    n_jobs=-1,
    verbose=2
)

# ==========================================
# EKSEKUSI
# ==========================================
print("\n🔥 MULAI TRAINING DENGAN PIPELINE...")
print("Logika: Split CV -> SMOTE (Data Train Fold) -> Chi2 -> XGBoost -> Validasi")
start_time = time.time()

# Fit dijalankan pada data MURNI. Pipeline yang akan mengurus SMOTE di dalamnya.
grid_search.fit(X_train, y_train)

end_time = time.time()
duration = end_time - start_time
print(f"\n✅ SELESAI! Waktu proses: {duration/60:.2f} menit")

# ==========================================
# HASIL & EVALUASI
# ==========================================
best_model = grid_search.best_estimator_

print("\n" + "="*40)
print("HASIL TERBAIK")
print("="*40)
print(grid_search.best_params_)

# Cek fitur yang terpilih (Optional/Advanced)
# Kita bisa melihat fitur mana yang dipilih oleh Chi-Square
try:
    selected_mask = best_model.named_steps['selector'].get_support()
    print(f"\nJumlah fitur yang digunakan: {sum(selected_mask)} dari {X_train.shape[1]}")
except:
    pass

print("\n" + "="*40)
print("EVALUASI PADA DATA TEST (UNSEEN DATA)")
print("="*40)

# Prediksi ke Data Test
# Pipeline otomatis melakukan transformasi (Chi-Square) ke data test sebelum prediksi
# (SMOTE tidak dilakukan ke data test, pipeline otomatis tahu itu)
y_pred = best_model.predict(X_test)

# Kembalikan ke label asli
y_test_label = le.inverse_transform(y_test)
y_pred_label = le.inverse_transform(y_pred)

print("\nClassification Report:")
print(classification_report(y_test_label, y_pred_label))

print("\nConfusion Matrix:")
print(confusion_matrix(y_test_label, y_pred_label))

# Simpan Model Pipeline Lengkap
MODEL_DIR = PROJECT_ROOT / "models"
MODEL_DIR.mkdir(exist_ok=True)

model_path = MODEL_DIR / "pipeline_scenario3.pkl"
joblib.dump(best_model, model_path)

print(f"\n💾 Model Pipeline disimpan ke: {model_path}")
print("Gunakan file ini untuk prediksi di aplikasi nanti (otomatis handle chi-square selection)")