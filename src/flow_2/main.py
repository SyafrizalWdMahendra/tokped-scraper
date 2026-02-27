import sys
import time
import joblib
from pathlib import Path
from xgboost import XGBClassifier
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import classification_report, confusion_matrix

# ==========================================
# 1. KONFIGURASI PATH (PATHLIB)
# ==========================================
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1] 
DATA_DIR = PROJECT_ROOT / "data"

print(f"--- INFO PATH SCENARIO 2 ---")
print(f"Project Root: {PROJECT_ROOT}")
print(f"Data Dir:     {DATA_DIR}")

# PATHS = {
#     "X_train": DATA_DIR / "tokenize" / "train" / "X_train_tfidf.pkl", 
#     "y_train": DATA_DIR / "tokenize" / "train" / "y_train.pkl",
#     "X_test":  DATA_DIR / "tokenize" / "test" / "X_test_tfidf.pkl",
#     "y_test":  DATA_DIR / "tokenize" / "test" / "y_test.pkl",
#     "le":      DATA_DIR / "tokenize" / "label_encoder.pkl",
# }

PATHS = {
    "X_train": PROJECT_ROOT / "X_train_tfidf.pkl", 
    "y_train": PROJECT_ROOT / "y_train.pkl",
    "X_test":  PROJECT_ROOT / "X_test_tfidf.pkl",
    "y_test":  PROJECT_ROOT / "y_test.pkl",
    "le":      PROJECT_ROOT / "label_encoder.pkl",
}

# ==========================================
# 2. LOAD DATA
# ==========================================
print("\n--- MEMUAT DATA SCENARIO 2 ---")
data = {}

try:
    for name, path in PATHS.items():
        file_path = str(path)
        if not path.exists():
            print(f"❌ ERROR: File tidak ditemukan di: {file_path}")
            sys.exit()
        data[name] = joblib.load(file_path)
        print(f"✅ Loaded {name}")

except Exception as e:
    print(f"❌ Terjadi kesalahan saat loading: {e}")
    sys.exit()

X_train, y_train = data['X_train'], data['y_train']
X_test, y_test = data['X_test'], data['y_test']
le = data['le']

print(f"\nDimensi Training (Imbalanced): {X_train.shape}")

# ==========================================
# 3. SETUP GRID SEARCH (SAMA DENGAN SKENARIO 3)
# ==========================================
# Kita gunakan range parameter yang SAMA PERSIS dengan Skenario 3
# agar perbandingannya adil (apple-to-apple).
param_grid = {
    'learning_rate': [0.01, 0.1, 0.2],
    'max_depth': [3, 5, 7],
    'n_estimators': [100, 200],
    'subsample': [0.8, 1.0],
    'colsample_bytree': [0.8, 1.0]
}

xgb = XGBClassifier(
    objective='multi:softprob', 
    num_class=3, 
    random_state=42, 
    eval_metric='mlogloss',
    use_label_encoder=False
)

# Gunakan F1-Macro agar Grid Search mencoba adil ke kelas minoritas
grid_search = GridSearchCV(
    estimator=xgb,
    param_grid=param_grid,
    cv=3, 
    scoring='f1_macro', 
    n_jobs=-1, 
    verbose=1
)

# ==========================================
# 4. EKSEKUSI TRAINING
# ==========================================
print("\n🔥 MULAI TRAINING & GRID SEARCH (SCENARIO 2)...")
print("Sedang mencari parameter terbaik untuk data Imbalanced...")
start_time = time.time()

grid_search.fit(X_train, y_train)

duration = time.time() - start_time
print(f"\n✅ SELESAI! Waktu proses: {duration/60:.2f} menit")

# ==========================================
# 5. EVALUASI & SIMPAN
# ==========================================
best_model = grid_search.best_estimator_

print("\n" + "="*40)
print("HASIL TERBAIK (BEST PARAMETERS)")
print("="*40)
print(grid_search.best_params_)

print("\n" + "="*40)
print("HASIL SKENARIO 2 (TUNED MODEL)")
print("="*40)

y_pred = best_model.predict(X_test)

y_test_label = le.inverse_transform(y_test)
y_pred_label = le.inverse_transform(y_pred)

print("\nClassification Report:")
print(classification_report(y_test_label, y_pred_label))

print("\nConfusion Matrix:")
print(confusion_matrix(y_test_label, y_pred_label))

# Simpan Model Skenario 2
model_path = SCRIPT_DIR / 'new_model_xgboost_scenario2.pkl'
joblib.dump(best_model, model_path)
print(f"\n💾 Model Skenario 2 disimpan ke: {model_path}")