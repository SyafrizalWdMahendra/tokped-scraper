import pandas as pd
import os


def check_sentiment_counts():
    # 1. Konfigurasi Nama File
    file_utama = 'data/dataset/dataset_fix.csv'          # File lama (mayoritas positif)
    # File baru (hasil filter bintang 1-3)
    file_baru = 'data/dataset/dataset_balanced.csv'

    dfs = []  # List untuk menampung dataframe agar bisa dihitung totalnya nanti

    # === CEK FILE 1 (UTAMA) ===
    if os.path.exists(file_utama):
        print(f"--- Menganalisis File: {file_utama} ---")
        df1 = pd.read_csv(file_utama)
        print(f"Total Baris: {len(df1)}")
        print("Sebaran Sentimen:")
        print(df1['Sentiment'].value_counts())
        dfs.append(df1)
    else:
        print(f"[!] File {file_utama} tidak ditemukan.")

    print("\n" + "="*30 + "\n")

    # === CEK FILE 2 (BARU/BALANCED) ===
    if os.path.exists(file_baru):
        print(f"--- Menganalisis File: {file_baru} ---")
        df2 = pd.read_csv(file_baru)
        print(f"Total Baris: {len(df2)}")
        print("Sebaran Sentimen:")
        print(df2['Sentiment'].value_counts())
        dfs.append(df2)
    else:
        print(f"[!] File {file_baru} tidak ditemukan.")

    print("\n" + "="*30 + "\n")

    # === SIMULASI PENGGABUNGAN (TOTAL) ===
    if len(dfs) == 2:
        print("--- SIMULASI JIKA DIGABUNG (MERGED) ---")
        df_total = pd.concat(dfs, ignore_index=True)

        # Cek Duplikat (Penting!)
        # Kita cek duplikat berdasarkan isi review dan username agar akurat
        duplicate_count = df_total.duplicated(
            subset=['Review', 'Username']).sum()

        print(f"Total Data Mentah: {len(df_total)}")
        print(f"Potensi Duplikat: {duplicate_count} data")

        # Hitung sebaran bersih (tanpa duplikat)
        df_bersih = df_total.drop_duplicates(subset=['Review', 'Username'])
        print("\n>>> KOMPOSISI AKHIR (SETELAH BERSIH DUPLIKAT):")
        print(df_bersih['Sentiment'].value_counts())

        # Hitung Persentase
        total_final = len(df_bersih)
        if total_final > 0:
            print("\n>>> PERSENTASE:")
            counts = df_bersih['Sentiment'].value_counts()
            for sentiment, count in counts.items():
                pct = (count / total_final) * 100
                print(f"{sentiment}: {pct:.2f}%")
    else:
        print("[!] Tidak bisa menghitung total karena salah satu file hilang.")


if __name__ == "__main__":
    check_sentiment_counts()
