# 1. Gunakan base image Python yang stabil
FROM python:3.10-slim

# 2. Atur direktori kerja di dalam container
WORKDIR /app

# 3. Copy file requirements dulu (biar build lebih cepat kalau ada perubahan kode)
COPY requirements.txt .

# 4. Install library yang dibutuhkan
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy semua file proyek ke dalam container
COPY . .

# 6. Jalankan FastAPI menggunakan Uvicorn
# Hugging Face Spaces secara default menggunakan port 7860
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]