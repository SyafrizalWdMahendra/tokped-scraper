import time
import pandas as pd
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By

def manual_harvest_v2(keywords, pages=5):
    options = uc.ChromeOptions()
    # options.add_argument("--headless=new") # Jangan nyalakan headless dulu
    
    print("🚀 Membuka Browser...")
    # Menggunakan version_main=None agar otomatis menyesuaikan versi Chrome
    driver = uc.Chrome(options=options, version_main=None) 
    
    collected_urls = []
    # Pola URL Produk yang valid biasanya: tokopedia.com/nama-toko/nama-produk
    ignore_list = [
        "ta.tokopedia.com", # Iklan
        "google", "facebook", "twitter", # Sosmed
        "/search?", "/discovery", "/hot", # Halaman navigasi
        "/help", "/about", "/login", "/cart" # Halaman umum
    ]
    
    base_url = "https://www.tokopedia.com/search?st=product&q={}&page={}"
    
    try:
        for page in range(1, pages + 1):
            target_url = base_url.format(keywords, page)
            print(f"\n[{page}/{pages}] Navigasi ke: {target_url}")
            driver.get(target_url)
            
            # --- INTERVENSI MANUSIA ---
            print("👀 Tunggu loading & Captcha...")
            print("👇 Scroll manual ke paling bawah agar semua produk ter-load!")
            input("⌨️  Jika semua produk sudah terlihat, TEKAN ENTER...")
            # --------------------------
            
            print("   ⚡ Mengambil semua link di layar...")
            
            # AMBIL SEMUA TAG <a> TANPA FILTER RIBET
            elems = driver.find_elements(By.TAG_NAME, "a")
            
            page_urls = []
            for elem in elems:
                try:
                    url = elem.get_attribute('href')
                    
                    # VALIDASI URL:
                    # 1. Harus string dan ada 'tokopedia.com'
                    if not url or "tokopedia.com" not in url:
                        continue
                        
                    # 2. Skip jika ada di ignore_list
                    if any(x in url for x in ignore_list):
                        continue
                    
                    # 3. URL produk biasanya strukturnya: tokopedia.com/{shop}/{product}
                    # Minimal panjang URL > 40 karakter (heuristic sederhana)
                    if len(url) < 35: 
                        continue

                    # Bersihkan URL
                    clean_url = url.split("?")[0]
                    
                    # Cek duplikat lokal di halaman ini
                    final_link = clean_url + "/review"
                    if final_link not in page_urls:
                        page_urls.append(final_link)
                        
                except Exception:
                    continue
            
            print(f"   ✓ Halaman ini dapat {len(page_urls)} link produk valid")
            collected_urls.extend(page_urls)
            
    except Exception as e:
        print(f"Error: {e}")
        # DEBUG: Simpan HTML jika error untuk dicek
        with open("debug_error.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("   ⚠ File debug_error.html telah dibuat untuk pengecekan.")
        
    finally:
        try:
            driver.quit()
        except:
            pass
        
    return list(set(collected_urls))

if __name__ == "__main__":
    keyword = "laptop acer"
    kw_format = keyword.replace(" ", "%20")
    
    final_urls = manual_harvest_v2(kw_format, pages=2)
    
    print(f"\n{'='*30}")
    if final_urls:
        df = pd.DataFrame(final_urls, columns=["url"])
        df.to_csv("urls/target_urls_3.csv", index=False)
        print(f"✅ SUKSES PANEN! {len(final_urls)} URL tersimpan di target_urls_2.csv")
        print("Contoh URL:", final_urls[0])
    else:
        print("❌ Masih 0 URL. Cek file debug_error.html jika ada.")