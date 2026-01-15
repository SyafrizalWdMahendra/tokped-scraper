import time
import pandas as pd
import re
import nltk
import random
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
import os
# Download NLTK resources (Cukup sekali run)
# nltk.download('punkt')
# nltk.download('stopwords')
# nltk.download('wordnet')


class ReviewScraper:
    def __init__(self):
        options = Options()
        # options.add_argument("--headless")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option(
            "excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        self.driver = webdriver.Chrome(options=options)
        self.data = []
        self.stop_words = set(stopwords.words('indonesian'))
        self.lemmatizer = WordNetLemmatizer()

    def clean_text(self, text: str) -> str:
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\d+', '', text)
        text = text.lower()
        return text.strip()

    def get_review_data(self, container, source_url) -> dict:
        try:
            # 1. Username
            username = "Anonymous"
            user_elem = container.find(
                'span', attrs={'data-testid': 'proName'})
            if not user_elem:
                user_elem = container.find(
                    'span', class_=re.compile(r'name', re.I))
            if user_elem:
                username = user_elem.text

            # 2. Rating (Ambil dari aria-label bintang)
            rating = "5"
            rating_elem = container.find(
                'div', attrs={'data-testid': 'icnStarRating'})
            if rating_elem:
                try:
                    rating = rating_elem.get('aria-label').split(' ')[1]
                except:
                    pass

            # 3. Ulasan Text
            ulasan = ""
            ulasan_elem = container.find(
                'span', attrs={'data-testid': 'lblItemUlasan'})
            if not ulasan_elem:
                ulasan_elem = container.find('span', attrs={'data-testid': ''})
            if ulasan_elem:
                ulasan = ulasan_elem.text

            # Fallback jika ulasan kosong
            if not ulasan:
                paragraphs = container.find_all('p')
                for p in paragraphs:
                    if len(p.text) > 10 and "WIB" not in p.text:
                        ulasan = p.text
                        break

            # 4. Tanggal
            waktu_komentar = "Unknown"
            date_elem = container.find(
                'p', class_=re.compile(r'timestamp|date', re.I))
            if date_elem:
                waktu_komentar = date_elem.text
            else:
                for span in container.find_all('p'):
                    if 'WIB' in span.text or 'lalu' in span.text:
                        waktu_komentar = span.text
                        break

            # VALIDASI: Jangan simpan jika kosong
            if not ulasan:
                return None

            ulasan_cleaned = self.clean_text(ulasan)

            return {
                'Source_URL': source_url,
                'Username': username,
                'Review': ulasan,
                'Cleaned_Review': ulasan_cleaned,
                'Rating': rating,
                'Date': waktu_komentar
            }
        except Exception as e:
            return None

    def toggle_filter(self, rating: str, action: str, max_retries: int = 2):
        """
        Logika Baru:
        1. Coba cari elemen dengan Timeout SINGKAT (2 detik).
        2. Jika TimeoutException -> Artinya filter tidak ada (0 review) -> RETURN FALSE (Jangan Retry).
        3. Jika Error Klik -> Baru lakukan Retry.
        """
        print(f"   ...Mencoba {action} filter Bintang {rating}...")

        # Scroll agar elemen masuk viewport
        self.driver.execute_script("window.scrollBy(0, 400);")
        time.sleep(1)

        # STRATEGI XPATH
        strategies = [
            # Spesifik Tokped baru
            f"//label[contains(@for, 'rating') and .//text()='{rating}']",
            f"//label[.//text()='{rating}' and .//*[name()='img' or name()='svg']]",
            f"//*[text()='Rating']/ancestor::div[2]//label[contains(., '{rating}')]",
            f"//label[text()='{rating}']"
        ]

        for attempt in range(max_retries):
            found_element = None

            # Coba cari elemen dengan salah satu strategi
            for xpath in strategies:
                try:
                    # Timeout dipendekkan ke 2 detik agar cepat skip jika tidak ada
                    found_element = WebDriverWait(self.driver, 2).until(
                        EC.presence_of_element_located((By.XPATH, xpath))
                    )

                    # Cek apakah visible & clickable
                    if found_element.is_displayed():
                        # Cek apakah disabled (kelas CSS atau atribut)
                        if "disabled" in found_element.get_attribute("class") or found_element.get_attribute("disabled"):
                            print(
                                f"   [SKIP] Filter Bintang {rating} ada tapi DISABLED (Non-aktif).")
                            return False

                        # Jika elemen ketemu, siap diklik
                        break
                    else:
                        found_element = None  # Ketemu di DOM tapi hidden
                except TimeoutException:
                    continue  # Coba strategi xpath berikutnya

            # HASIL PENCARIAN
            if found_element:
                try:
                    # KLIK!
                    self.driver.execute_script(
                        "arguments[0].click();", found_element)
                    print(
                        f"   [SUKSES] Filter Bintang {rating} berhasil di-{action}!")
                    time.sleep(3)  # Tunggu loading data
                    return True
                except Exception as click_error:
                    if attempt < max_retries - 1:
                        print(
                            f"   [RETRY {attempt + 1}] Elemen ada tapi gagal klik. Mencoba lagi...")
                        time.sleep(2)
                        continue
                    else:
                        print(
                            f"   [ERROR] Gagal klik filter setelah retry: {click_error}")
                        return False
            else:
                # PENTING: Jika di attempt pertama tidak ketemu di semua strategi,
                # asumsikan filter TIDAK ADA. Jangan retry.
                print(
                    f"   [SKIP] Filter Bintang {rating} TIDAK DITEMUKAN (Mungkin 0 ulasan). Lanjut.")
                return False

        return False

    def scrape_pages_current_view(self, url, current_rating_context):
        page_number = 1
        empty_page_count = 0

        while True:
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            containers = soup.find_all(
                "div", attrs={'data-testid': 'reviewCard'})

            if not containers:
                containers = soup.find_all("article")

            if not containers:
                # Double check: kadang loading lambat
                time.sleep(2)
                soup = BeautifulSoup(self.driver.page_source, "html.parser")
                containers = soup.find_all(
                    "div", attrs={'data-testid': 'reviewCard'})

                if not containers:
                    print(
                        f"      [INFO] Halaman {page_number} kosong. Berhenti pagination.")
                    break

            found_new = False
            for container in containers:
                review_data = self.get_review_data(container, url)
                if review_data:
                    # Validasi Rating sesuai Filter
                    if current_rating_context != "ALL" and review_data['Rating'] != current_rating_context:
                        continue

                    if review_data not in self.data:
                        self.data.append(review_data)
                        found_new = True

            if found_new:
                print(
                    f"      + Halaman {page_number} ok (Filter: {current_rating_context}). Total: {len(self.data)}")
                empty_page_count = 0
            else:
                print(f"      . Halaman {page_number} tidak ada data baru.")
                empty_page_count += 1
                if empty_page_count >= 2:  # Stop jika 2 halaman berturut-turut zonk
                    print(
                        "      [STOP] 2 halaman tanpa data baru. Pindah filter.")
                    break

            # Navigasi Next Button
            try:
                next_button = self.driver.find_element(
                    By.CSS_SELECTOR, "button[aria-label^='Laman berikutnya']")
                if not next_button.is_enabled():
                    break

                self.driver.execute_script(
                    "arguments[0].click();", next_button)
                time.sleep(random.uniform(2, 4))
                page_number += 1
            except:
                break

    def scrape_single_product(self, url: str):
        print(f"\n--- Memproses URL: {url} ---")
        try:
            self.driver.get(url)
            time.sleep(4)
            self.driver.execute_script("window.scrollBy(0, 800);")
            time.sleep(2)

            # TARGET: Negatif (1,2) & Netral (3)
            target_filters = ['1', '2', '3']

            for rating in target_filters:
                # 1. KLIK FILTER
                success = self.toggle_filter(rating, action="CHECK")

                if success:
                    # 2. SCRAPE
                    self.scrape_pages_current_view(
                        url, current_rating_context=rating)

                    # 3. UNCHECK (PENTING: Gunakan logic toggle yang sama)
                    # Scroll dikit ke atas biar tombol filter kelihatan lagi
                    self.driver.execute_script("window.scrollBy(0, -300);")
                    time.sleep(1)

                    uncheck_success = self.toggle_filter(
                        rating, action="UNCHECK")
                    if not uncheck_success:
                        # Jika gagal uncheck, refresh page adalah jalan ninja
                        print(
                            "   [REFRESH] Gagal uncheck, refresh halaman untuk reset filter...")
                        self.driver.refresh()
                        time.sleep(4)
                        self.driver.execute_script("window.scrollBy(0, 800);")
                else:
                    # Jika toggle CHECK gagal/tidak ketemu -> LANJUT ke rating berikutnya
                    # Tidak perlu scrape, tidak perlu uncheck
                    continue

                time.sleep(1)

        except Exception as e:
            print(f"   [ERROR FATAL URL] {e}")

    def label_data(self, df: pd.DataFrame) -> pd.DataFrame:
        df['Sentiment'] = df['Rating'].apply(lambda x: 'positif' if float(
            x) >= 4 else ('netral' if float(x) == 3 else 'negatif'))
        return df

    def run(self, url_list: list) -> None:
        print(f"Total {len(url_list)} URL antrian.")
        for idx, url in enumerate(url_list, 1):
            print(f"Proses {idx}/{len(url_list)}...")
            self.scrape_single_product(url)

        self.driver.quit()

        if self.data:
            # 1. Siapkan Data Baru
            df_new = pd.DataFrame(self.data)
            df_new = self.label_data(df_new)
            
            filename = 'dataset_fix_balanced.csv'
            
            # 2. Cek apakah file sudah ada (Smart Merge Logic)
            if os.path.exists(filename):
                try:
                    print(f"\n[INFO] File '{filename}' ditemukan. Membaca data lama...")
                    df_old = pd.read_csv(filename)
                    
                    # Gabungkan data lama dan baru
                    df_combined = pd.concat([df_old, df_new], ignore_index=True)
                    
                    # 3. Hapus Duplikat
                    # Kita anggap duplikat jika Username, Review (yang sudah dibersihkan), dan Tanggal sama persis
                    total_before = len(df_combined)
                    df_combined.drop_duplicates(subset=['Username', 'Cleaned_Review', 'Date'], keep='first', inplace=True)
                    total_after = len(df_combined)
                    
                    print(f"   - Data Lama: {len(df_old)}")
                    print(f"   - Data Baru (Scraping saat ini): {len(df_new)}")
                    print(f"   - Duplikat Dibuang: {total_before - total_after}")
                    
                    df_final = df_combined
                except Exception as e:
                    print(f"[WARNING] Gagal membaca file lama ({e}). Membuat file baru.")
                    df_final = df_new
            else:
                print(f"\n[INFO] File '{filename}' belum ada. Membuat file baru.")
                df_final = df_new

            # 4. Simpan Hasil Akhir
            print("\n=== TOTAL DATASET SETELAH UPDATE ===")
            print(df_final['Sentiment'].value_counts())
            
            df_final.to_csv(filename, index=False)
            print(f"Data berhasil disimpan/diupdate ke: {filename}")
        else:
            print("\n[!] Tidak ada data baru yang didapatkan dari sesi ini.")

def main():
    target_urls = [
        "https://www.tokopedia.com/acer-jakarta/acer-aspire-lite-14-al14-32p-38re-intel-core-3-n355-8-512gb-ssd-windows-11-ohs-14-inch-wuxga-ips-light-silver-fresh-blue-and-nude-pink-1733363505829020820/review",
        "https://www.tokopedia.com/gugellaptop/thinkpad-t470s-thinkpad-t470s-thinkpad-t470s-t470s-1731511946279159074/review",
        "https://www.tokopedia.com/apollonotebook/laptop-lenovo-thinkpad-x260-core-i5-second-terjangkau-bergaransi-1730699649080657038/review",
        "https://www.tokopedia.com/agresid/lenovo-ideapad-slim-3-14-i3-1315-8gb-512gb-w11-ohs-14-0-fhd-blit-1731231402520380483/review",
        "https://www.tokopedia.com/wei-1/laptop-hp-14-em0332au-em0333au-ryzen-3-7320u-8gb-512gb-ssd-14-fhd-win11-ohs-1731073555487884763/review",
        "https://www.tokopedia.com/starjayaelectronic/laptop-touchscreen-lenovo-thinkpad-t470s-core-i7-gen-6-8gb-256gb-1733591315677349803/review",
        "https://www.tokopedia.com/collinsofficial/asus-vivobook-go-14-e410ka-n4500-8gb-256gb-intel-uhd-14-fhd-w11-ohs-ram-8gb-e283b/review",
        "https://www.tokopedia.com/amolilaptop/amoli-laptop11-6-inc-ram-8gb-256gb-ssd-laptop-kantor-windows-10-11-intel-celeron-processor-n4020-ultra-clear-ips-layar-penuh-win10-11-tipis-dan-ringan-1730000559508523466/review",
        "https://www.tokopedia.com/agreshpauthorized/laptop-hp-14s-amd-ryzen-3-7320u-8gb-512-ssd-14-0fhd-w11-ohs-1731554642575787170/review",
        "https://www.tokopedia.com/tokohapedia-idn/apple-macbook-pro-m1-pro-2021-14-512gb-1tb-space-gray-silver-promo-resmi-512-space-grey-3b709/review",
        "https://www.tokopedia.com/royalltech/laptop-acer-aspire-lite-ag14-al14-al1-intel-i5-13500h-i3-n355-16gb-ram-512gb-ssd-14-wuxga-ips-windows-11-ohs-1733266507626153463/review",
        "https://www.tokopedia.com/hosanacomp/laptop-lenovo-ideapad-slim-3-ryzen-3-7320u-8gb-512gb-ssd-win11-ohs-1731184790045426732/review",
        "https://www.tokopedia.com/onestopgaming/apple-macbook-pro-m4-chip-14-inch-ssd-1tb-512gb-ram-16gb-24gb-resmi-apple-1732222963331663106/review",
        "https://www.tokopedia.com/protechcom/tecno-megabook-t1-14-ryzen-5-7430u-16gb-512gb-14-w11-1731615804633810848/review",
        "https://www.tokopedia.com/apollonotebook/laptop-dell-e4310-core-i5-second-murah-bergaransi-1731138515921044622/review",
        "https://www.tokopedia.com/oceanla/lenovo-thinkpad-t490-intel-core-i7-l-i5-gen-8th-ram-32gb-ultrabook-i5-gen-8-16gb-ssd-512gb-6fff1/review",
        "https://www.tokopedia.com/protechcom/asus-vivobook-14-a1405va-i5-13420h-16gb-512gb-14-wuxga-w11-ohs-m365-1731191938883422112/review",
        "https://www.tokopedia.com/collinsofficial/asus-vivobook-14-a1405va-i5-13420h-16gb-ssd-512gb-14-wuxga-iris-xe-w11-ohs-1732714762818127047/review",
        "https://www.tokopedia.com/distri-laptop/axioo-hype-1-celeron-n4020-4gb-8gb-128gb-384gb-14-hd-w11-1731287921301751309/review",
        "https://www.tokopedia.com/axiooslimbook/laptop-axioo-hype-5-amd-ryzen-5-7430u-8gb-256gb-windows-11-pro-1731092562779669871/review",
        "https://www.tokopedia.com/specialistlaptop/promo-laptop-lenovo-x250-core-i5-5300u-ssd-256-8gb-murah-garansi-mulus-ram-8gb-hdd-500/review",
        "https://www.tokopedia.com/gardaku/apple-macbook-air-series-m2-m3-m4-chip-13-inch-ram-8gb-16gb-256gb-512gb-ssd-1732477353178138390/review",
        "https://www.tokopedia.com/sinarmulia/lenovo-ideapad-slim-3i-i5-13420h-512gb-ssd-8gb-16gb-wuxga-ips-win11-ohs-1731539518315071263/review",
        "https://www.tokopedia.com/wei-1/acer-aspire-lite-14-al14-31p-intel-n100-8gb-256gb-512gb-ssd-14-wuxga-ips-w11-ohs-1731240630630909403/review",
        "https://www.tokopedia.com/protechcom/asus-vivobook-14-a1404va-i3-1315u-8gb-512gb-14-fhd-ohs-w11-ddr4-8gb-05e3e/review",
        "https://www.tokopedia.com/gaminglaptopid/laptop-asus-zenbook-14-oled-um3406ha-touch-amd-ryzen-7-8840hs-16gb-512gb-windows-11-14-inch-1731200295547995755/review",
        "https://www.tokopedia.com/collinsofficial/apple-macbook-air-m4-2025-13-inch-16-256gb-16-512gb-24-512gb-gpu-8core-10core-resmi-ibox-1733912388791993543/review",
        "https://www.tokopedia.com/distri-laptop/axioo-mybook-hype-5-amd-ryzen-5-ram-8gb-256gb-ssd-14-fhd-win11-1731441317863720461/review",
        "https://www.tokopedia.com/oceanla/laptop-lenovo-thinkpad-t460s-t470s-intel-i5-i7-ram-20gb-murah-bergaransi-1733509135021213476/review",
        "https://www.tokopedia.com/oceanla/laptop-lenovo-thinkpad-x270-x260-x250-x240-x230-ram-16gb-ssd-1tb-ultrabook-murah-1733484675192293156/review",
        "https://www.tokopedia.com/decacom/asus-vivobook-s15-oled-ultra-9-185h-ultra-7-155h-16gb-1tb-w11-15-qhd-3k-s5506ma-1732723078640732127/review",
    ]

    scraper = ReviewScraper()
    scraper.run(target_urls)


if __name__ == "__main__":
    main()
