import pandas as pd
import os

def generate_final_grouped_sample(input_file, output_file, total_sample=356):
    if not os.path.exists(input_file):
        print(f"Error: File {input_file} tidak ditemukan!")
        return

    # 1. Load Dataset
    df = pd.read_csv(input_file)
    
    # 2. Definisikan Proporsi Sesuai Data Asli
    proportions = {
        'positif': 0.50,
        'negatif': 0.307,
        'netral': 0.193
    }

    print("=== Rincian Rencana Sampling (Stratified) ===")
    print(f"Total Populasi: {len(df)} data")
    print(f"Target Sampel: {total_sample} data\n")

    # 3. Proses Sampling Per Kelas
    sampled_list = []
    summary_data = []

    # Urutan tetap: Positif, Negatif, Netral
    for sentiment in ['positif', 'negatif', 'netral']:
        weight = proportions[sentiment]
        
        # Hitung jumlah sampel untuk kelas ini
        n_target = int(round(total_sample * weight))
        
        # Ambil data dari dataset asli
        class_data = df[df['Sentiment'] == sentiment]
        n_available = len(class_data)
        
        # Ambil sampel (n_target)
        sample_class = class_data.sample(n=min(n_available, n_target), random_state=42)
        sampled_list.append(sample_class)
        
        # Simpan rincian untuk ditampilkan
        summary_data.append({
            'Kelas': sentiment.capitalize(),
            'Proporsi (%)': f"{weight*100:.1f}%",
            'Jumlah Target': n_target,
            'Tersedia': n_available
        })

    # Gabungkan semua (berdasarkan urutan kelas, tidak di-shuffle)
    sampled_df = pd.concat(sampled_list)

    # Tampilkan Tabel Rincian di Terminal
    summary_df = pd.DataFrame(summary_data)
    print(summary_df.to_string(index=False))
    print("-" * 45)
    print(f"Total Data Berhasil Dibuat: {len(sampled_df)}\n")

    # 4. Tambahkan Kolom Manual Label & Rapikan
    sampled_df['Manual_Label'] = ""
    cols = ['Username', 'Rating', 'Sentiment', 'Manual_Label', 'Review', 'Cleaned_Review', 'Date']
    sampled_df = sampled_df[[c for c in cols if c in sampled_df.columns]]

    # 5. Simpan ke Excel dengan Format Rapi
    try:
        writer = pd.ExcelWriter(output_file, engine='xlsxwriter')
        sampled_df.to_excel(writer, index=False, sheet_name='Validasi_356')

        workbook  = writer.book
        worksheet = writer.sheets['Validasi_356']

        # Formatting
        header_fmt = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1, 'align': 'center'})
        wrap_fmt = workbook.add_format({'text_wrap': True, 'valign': 'top', 'font_size': 10})
        input_fmt = workbook.add_format({'bg_color': '#FFFF00', 'border': 2, 'valign': 'top', 'bold': True})

        # Atur Lebar Kolom
        worksheet.set_column('A:A', 15)      # Username
        worksheet.set_column('B:C', 10)      # Rating & Sentiment
        worksheet.set_column('D:D', 18, input_fmt)  # Manual_Label (Kuning)
        worksheet.set_column('E:F', 55, wrap_fmt)   # Review & Cleaned
        worksheet.set_column('G:G', 15)      # Date
        
        worksheet.freeze_panes(1, 0) # Freeze baris pertama

        for col_num, value in enumerate(sampled_df.columns.values):
            worksheet.write(0, col_num, value, header_fmt)

        writer.close()
        print(f"File Berhasil Dibuat: {output_file}")

    except Exception as e:
        print(f"Gagal memformat Excel: {e}")
        sampled_df.to_csv('backup_validasi.csv', index=False)

# Jalankan
generate_final_grouped_sample(
    input_file='robust_data/dataset/trimmed_sentiment_dataset.csv', 
    output_file='Validasi_Manual_356_Proporsional.xlsx'
)