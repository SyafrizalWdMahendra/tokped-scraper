import matplotlib.pyplot as plt

def visualize_pie_only():
    # --- 1. DATA ---
    labels = ['Positif', 'Negatif', 'Netral']
    # counts = [2450, 997, 625]
    counts = [1622, 997, 625]
    
    # Menghitung persentase untuk analisis
    total = sum(counts)
    percentages = [(x / total * 100) for x in counts]

    # --- 2. KONFIGURASI PLOT ---
    colors = ['#2ecc71', '#e74c3c', '#95a5a6'] # Hijau, Merah, Abu
    explode = (0.1, 0, 0)  # Memisahkan (explode) bagian Positif agar menonjol
    
    # Membuat Figure
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # --- 3. MEMBUAT PIE CHART ---
    wedges, texts, autotexts = ax.pie(
        counts, 
        explode=explode, 
        labels=labels, 
        colors=colors,
        autopct='%1.1f%%', 
        shadow=True, 
        startangle=140,
        textprops={'fontsize': 12}
    )
    
    # Mempercantik teks persentase
    plt.setp(autotexts, size=14, weight="bold", color="white")
    
    # Judul Grafik
    ax.set_title(f"Distribusi Sentimen (Total Data: {total})", fontsize=16, fontweight='bold')

    # Menyesuaikan margin agar teks tidak terpotong
    plt.subplots_adjust(bottom=0.3)
    
    # Tampilkan
    plt.show()

if __name__ == "__main__":
    visualize_pie_only()