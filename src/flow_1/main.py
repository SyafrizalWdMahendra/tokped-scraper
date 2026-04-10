import sys
import time
import joblib
from pathlib import Path
from xgboost import XGBClassifier
from sklearn.metrics import classification_report, confusion_matrix

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1] 
DATA_DIR = PROJECT_ROOT / "robust_data"

PATHS = {
    "X_train": DATA_DIR / "tokenize" / "X_train_tfidf.pkl",
    "y_train": DATA_DIR / "tokenize" / "y_train.pkl",
    "X_test":  DATA_DIR / "tokenize" / "X_test_tfidf.pkl",
    "y_test":  DATA_DIR / "tokenize" / "y_test.pkl",
    "le":      DATA_DIR / "tokenize" / "label_encoder.pkl",
}

print("\n--- MEMUAT DATA BASELINE ---")
data = {}

try:
    for name, path in PATHS.items():
        file_path = str(path)
        if not path.exists():
            print(f"❌ ERROR: File tidak ditemukan di: {file_path}")
            print(f"   Tips: Cek apakah file '{path.name}' ada di folder '{path.parent}'?")
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

model_baseline = XGBClassifier(
    objective='multi:softprob', 
    num_class=3, 
    random_state=42, 
    eval_metric='mlogloss',
    use_label_encoder=False
)

print("\n🔥 MULAI TRAINING BASELINE (SCENARIO 1)...")
start_time = time.time()

model_baseline.fit(X_train, y_train)

duration = time.time() - start_time
print(f"\n✅ SELESAI! Waktu proses: {duration:.2f} detik")

print("\n" + "="*40)
print("PARAMETER YANG DIGUNAKAN (DEFAULT)")
print("="*40)

all_params = model_baseline.get_params()

key_params = ['learning_rate', 'max_depth', 'n_estimators', 'subsample', 'colsample_bytree']
shown_params = {k: all_params.get(k) for k in key_params}

if shown_params['n_estimators'] is None: shown_params['n_estimators'] = "100 (Default)"
if shown_params['learning_rate'] is None: shown_params['learning_rate'] = "Default"

print(shown_params)
print("(Gunakan nilai ini untuk perbandingan di Bab 4)")

print("\n" + "="*40)
print("HASIL SKENARIO 1 (BASELINE)")
print("="*40)

y_pred = model_baseline.predict(X_test)

y_test_label = le.inverse_transform(y_test)
y_pred_label = le.inverse_transform(y_pred)

print("\nClassification Report:")
print(classification_report(y_test_label, y_pred_label))

print("\nConfusion Matrix:")
print(confusion_matrix(y_test_label, y_pred_label))

model_path = SCRIPT_DIR / 'new_xgboost_scenario1.pkl'
joblib.dump(model_baseline, model_path)
print(f"\n💾 Model baseline disimpan ke: {model_path}")