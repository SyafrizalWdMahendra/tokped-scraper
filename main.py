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
    "https://www.tokopedia.com/studioponsel/apple-macbook-air-m3-2024-13-inch-512gb-256gb-ram-16gb-1730958539678254399/review",
    "https://www.tokopedia.com/collinsofficial/asus-vivobook-go-14-e1404ga-i3-n305-8gb-ssd-256-512gb-14-fhd-w11-ohs-ssd-256gb-7d4bd/review",
    "https://www.tokopedia.com/axiooslimbook/laptop-axioo-hype-10-n4020-8gb-256gb-windows-10-pro-normal-dos-11f61/review",
    "https://www.tokopedia.com/advanstore/free-tas-advan-soulmate-x-14-ips-fhd-amd-3020e-4gb-128gb-free-windows-11-original-laptop-notebook-upgradeable-1733887140422125415/review",
    "https://www.tokopedia.com/agresid/asus-vivobook-14-a1404va-i3-1315-8gb-512gb-w11-ohs-14-0fhd-1731231392455689283/review",
    "https://www.tokopedia.com/intelgamingid/acer-aspire-lite-14-al14-i3-n355-8gb-512gb-w11-ohs-14-0fhd-ips-37p-36aw-1731571585509393728/review",
    "https://www.tokopedia.com/protechcom/tecno-megabook-t1-14-ryzen-5-7430u-16gb-512gb-14-w11-1732064921439668128/review",
    "https://www.tokopedia.com/teknotrend/apple-macbook-air-m2-chip-13-8gb-256gb-512gb-ssd-silver-512gb-apple-89ca1/review",
    "https://www.tokopedia.com/spacetech/infinix-inbook-x2-2025-i3-1315u-8gb-256gb-ssd-14-fhd-100-srgb-win11-1731385878083110521/review",
    "https://www.tokopedia.com/rogsstoreid/laptop-lenovo-v14-g4-core-i3-1315u-16gb-512gb-ssd-14-intel-uhd-1732830831630124364/review",
    "https://www.tokopedia.com/intelstore-id/laptop-lenovo-v14-g4-iru-core-i3-1315u-8gb-256ssd-14-fhd-w11-1733386294732096938/review",
    "https://www.tokopedia.com/amd-id/asus-vivobook-14-m1405ya-ryzen-7-7730u-16gb-512gb-w11-ohs-14-0wuxga-vips-1729896393440265595/review",
    "https://www.tokopedia.com/gitechlaptop/laptop-lenovo-thinkpad-t470-t480-t490-t14-core-i7-ram-32gb-ssd-1tb-laptop-1730881799003735695/review"
    "https://www.tokopedia.com/dwicompany/apple-macbook-air-m3-8gb-16gb-24gb-2024-256gb-512gb-1tb-13-15-inch-1732537202757829644/review",
    "https://www.tokopedia.com/amd-id/asus-vivobook-go-15-e1504fa-ryzen-5-7520-16gb-512gb-w11-ohs-m365b-15-6fhd-1732291174656214395/review",
    "https://www.tokopedia.com/teknotrend/laptop-asus-vivobook-go-14-e1404fa-amd-ryzen-3-7320u-8gb-256gb-512gb-14-fhd-1731262196135397314/review",
    "https://www.tokopedia.com/hp/laptop-hp-intel-core-i3-uhd-4gb-8gb-ram-512gb-ssd-silver-windows-11-home-14-inch-garansi-2-tahun-official-1732138607355594627/review",
    "https://www.tokopedia.com/collinsofficial/lenovo-ideapad-slim-3-i3-1315u-ram-8gb-256gb-512gb-ssd-14-fhd-w11-ohs-1732497278775755975/review",
    "https://www.tokopedia.com/digitalisme/apple-macbook-air-m4-2025-13-inch-24-512gb-16-512gb-10-core-gpu-16-256gb-8-core-gpu-resmi-1733446914166195409/review",
    "https://www.tokopedia.com/bigberry888/apple-macbook-pro-m2-m3-14-16-inch-512gb-1tb-ram-16gb-32gb-18gb-36gb-48gb-1732954912362431974/review",
    "https://www.tokopedia.com/collinsofficial/lenovo-ideapad-slim-3-i5-13420h-8gb-16gb-ddr5-512gb-ssd-14-wuxga-w11-ohs-1731203948778456263/review",
    "https://www.tokopedia.com/thinkpadofficial/lenovo-ideapad-slim-3i-14iru8-core-i3-1315u-8gb-512ssd-windows-11-ohs-14-inch-fhd-laptop-intel-5pid-1732471246595851658/review",
    "https://www.tokopedia.com/toptech/lenovo-v14-g5-irl-core-i3-1315-16gb-512gb-ssd-14-0fhd-w11-1731363639737484404/review",
    "https://www.tokopedia.com/onestopgaming/laptop-axioo-hype-1-intel-celeron-n4020-ram-4gb-8gb-ssd-128gb-14-hd-windows-11-1731304931508651266/review",
    "https://www.tokopedia.com/agreshpauthorized/hp-14-ryzen-5-7530-8gb-512gb-w11-ohs-m365b-14-0fhd-ips-blit-2y-gld-em0531au-1732302025059697826/review",
    "https://www.tokopedia.com/gugellaptop/thinkpad-t495-ryzen-7-pro-3700u-16gb-512gb-vega-2gb-thinkpad-t495-1730790073994217447/review",
    "https://www.tokopedia.com/teknotrend/laptop-axioo-mybook-hype-3-g11-intel-i3-1125g4-8gb-256gb-14-fhd-ips-1731298731986487234/review",
    "https://www.tokopedia.com/royalltech/laptop-lenovo-ideapad-slim-3-14-intel-celeron-n4500-n100-ram-8gb-ssd-512gb-windows-11-office-fhd-laptop-consumer-murah-cepat-ringan-ssd-kencang-ram-besar-anti-panas-cocok-untuk-office-kuliah-zoom-netflix-editing-kerja-harian-1733020603418314231/review",
    "https://www.tokopedia.com/sinarmulia/lenovo-ideapad-slim-3i-i3-1315u-256gb-ssd-8gb-win11-ohs-1731146440050247455/review",
    "https://www.tokopedia.com/collinsofficial/asus-vivobook-go-14-e1404ga-i3-n305-8gb-ssd-256-512gb-14-fhd-w11-ohs-1731003949706151111/review",
    "https://www.tokopedia.com/tokohapedia-idn/apple-macbook-air-m2-chip-2022-13-256gb-512gb-midnight-silver-inter-256-midnight/review",
    "https://www.tokopedia.com/lenovo-official/lenovo-v14-g4-iru-core-core-i3-1315u-8gb-512gb-w11-ohs-1733870723701310624/review",
    "https://www.tokopedia.com/electrocom/lenovo-thinkpad-x280-touchscreen-i5-gen8-ram-16gb-512gb-ultrabook-1733657196012995842/review",
    "https://www.tokopedia.com/kaitocorner/laptop-lenovo-thinkpad-t480-t480s-core-i5-i7-gen-8-layar-14-inch-1733712642338227987/review",
    "https://www.tokopedia.com/amd-id/asus-expertbook-pm1403cda-ryzen-7-7735hs-16gb-512gb-w11-ohs-m365b-140-fhd-ips-1731712946619385211/review",
    "https://www.tokopedia.com/gameridos/asus-vivobook-go-e410ka-n4500-ram-8gb-ssd-512gb-windows-11-ohs-m365b-14-0fhd-rose-pink-fhd4852m-1731601832835450465/review",
    "https://www.tokopedia.com/redstarelectronic/lenovo-thinkpad-t480s-core-i7-8650u-24gb-ram-512gb-nvme-ssd-tc-full-hd-windows-11-1729822537494135859/review",
    "https://www.tokopedia.com/royalltech/laptop-lenovo-ideapad-slim-3-x-thinkpad-v14-i3-1315u-ram-8gb-512gb-ssd-layar-14-fhd-windows-11-ohs-laptop-kuliah-laptop-kerja-laptop-tahan-banting-1733205589272462839/review",
    "https://www.tokopedia.com/toptech/hp-pavilion-aero-13-bg0111au-i-bg0222au-amd-ryzen-5-8640u-16gb-512gb-ssd-13-3-wuxga-ips-w11-ohs-1731216357464179828/review",
    "https://www.tokopedia.com/teknotrend/laptop-hp-14-ep0260tu-14-ep0261tu-core-i3-1315u-8gb-512gb-14-fhd-intel-uhd-graphics-w11-ohs-1733882228962330562/review",
    "https://www.tokopedia.com/spacetech/acer-aspire-lite-al14-i3-n355-8gb-512gb-ssd-14-wuxga-ips-win11-ohs-1731233517590382201/review",
    ]

    scraper = ReviewScraper()
    scraper.run(target_urls)


if __name__ == "__main__":
    main()
