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
            
            filename = 'dataset_fix_balanced_4.csv'
            
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
        "https://www.tokopedia.com/royalltech/laptop-hp-14-intel-i3-1315-8gb-512gb-w11-ohs-m365b-14-fhd-backlit-copilot-ep0261tu-ep0266tu-ep0269tu-1732399907078243831/review",
        "https://www.tokopedia.com/kalealaptop/laptop-lenovo-thinkpad-x280-core-i5-gen-7-ram-8-ssd-256-mulus-no-minus-x280-i3gen8-ram-8-ssd-128-336b0/review",
        "https://www.tokopedia.com/teknotrend/laptop-asus-vivobook-14-m1405ya-ryzen-7-7730u-512gb-ssd-16gb-ips-win11-1731262196140246978/review",
        "https://www.tokopedia.com/tokehlaptop/thinkpad-x390-i7-gen-8-thinkpad-x390-i5-gen-8-thinkpad-x390-1732687744696419831/review",
        "https://www.tokopedia.com/kaitocorner/bekas-laptop-lenovo-thinkpad-x280-core-i5-i7-gen-7-8-layar-12-5-inch-second-berkualitas-garansi-1729987821854820115/review",
        "https://www.tokopedia.com/specialistlaptop/laptop-lenovo-thinkpad-t480s-core-i7-8th-gen-ram-16gb-ssd-touchscreen-1731728721558275518/review",
        "https://www.tokopedia.com/gugellaptop/thinkpad-t14-gen-2-ryzen-thinkpad-t14-gen-1-ryzen-thinkpad-t14-g1-g2-1731426880048563490/review",
        "https://www.tokopedia.com/dwicompany/apple-macbook-pro-m3-14-16-inch-max-2024-8gb-18gb-36gb-48gb-512gb-1tb-1734061706103063564/review",
        "https://www.tokopedia.com/royalltech/laptop-hp-pavilion-aero-13-ryzen-7-8840-16gb-ram-ssd-1tb-13-3-wuxga-ips-windows-11-ohs-garansi-2-tahun-adp-laptop-ultrabook-ringan-1734445122094401015/review",
        "https://www.tokopedia.com/kalealaptop/laptop-lenovo-thinkpad-yoga-x380-core-i7-gen-8-ram-16-ssd-512-mulus-core-i5-gen-8-ram-8-ssd-256/review",
        "https://www.tokopedia.com/lenovolegion/lenovo-loq-essential-15iax9e-i5-12450hx-rtx3050-6gb-16gb-512gb-w11-ohs-m365b-15-6fhd-144hz-100srgb-blit-2y-prem-2adp-gry-1733518859327604428/review",
        "https://www.tokopedia.com/88-laptop/laptop-t490-core-i7-nvdia-mx250-touchscreen-ram-16gb-ssd-up-1tb-best-grade-1733741707736549019/review",
        "https://www.tokopedia.com/brankaslaptop/lenovo-thinkpad-t460-t470-t480-t490-l560-l570-x13-t14-t14s-second-original-dan-murah-1732859566066468209/review",
        "https://www.tokopedia.com/laptopvalley/laptop-lenovo-thinkpad-x260-core-i3-i5-gen-6-murah-dan-berkualitas-x260-i5-6-ram-4-ssd-128-72d4d/review",
        "https://www.tokopedia.com/sinarmulia/lenovo-yoga-slim-7i-ultra-7-155h-1tb-ssd-16gb-oled-wuxga-100-srgb-touch-win11-ohs-1731687248497837855/review",
        "https://www.tokopedia.com/sinarmulia/lenovo-yoga-slim-7i-ultra-5-226v-512gb-ssd-16gb-wuxga-oled-100-srgb-win11-ohs-1731812525684655903/review",
        "https://www.tokopedia.com/winselindo/apple-macbook-pro-14-16-inch-m2-pro-m2-max-ram-16gb-1732954922820404983/review",
        "https://www.tokopedia.com/gateway/lenovo-ideapad-slim-3-14-core-i7-13620h-i5-13420h-16gb-512gb-ssd-win11-ohs-14-inch-wuxga-ips-1732721250061157813/review",
        "https://www.tokopedia.com/intelstore-id/laptop-infinix-inbook-x2-2025-i5-1334-8gb-16gb-512gb-win11-14-fhd-1731860798190486954/review",
        "https://www.tokopedia.com/ismile-indonesia/apple-macbook-air-m2-13-garansi-resmi-8-512gb-16-512gb-1732525365931640715/review",
        "https://www.tokopedia.com/specialistlaptop/laptop-lenovo-thinkpad-t14-g2-core-i5-gen-11-ram-16gb-ssd-512-fhd-ips-win-11-ssd-nvme-256gb-16-gb-e5705/review",
        "https://www.tokopedia.com/alvinluo-shop/spek-tinggi-laptop-hp-elitebook-830-g5-core-i7-gen8-ram-16gb-ssd-512-840-g3-i5-6th-8gb-256gb-d6225/review",
        "https://www.tokopedia.com/oceanla/lenovo-thinkpad-t470s-intel-core-i7-gen-7-ram-8gb-256gb-mulus-like-new-t470s-i7gen7-8gb-ssd-256gb/review",
        "https://www.tokopedia.com/specialistlaptop/laptop-lenovo-thinkpad-t490-core-i7-8th-gen-ram-16gb-ssd-512-fhd-ips-ssd-256gb-16-gb-98043/review",
        "https://www.tokopedia.com/gugellaptop/thinkpad-t460s-thinkpad-t460s-thinkpad-t460s-t460s-1731426867889669410/review",
        "https://www.tokopedia.com/gateway/hp-14-laptop-ryzen-7-7730-ryzen-5-7530-ryzen-3-7320-16gb-512gb-ssd-14-inch-fhd-ips-1732453478513214901/review",
        "https://www.tokopedia.com/alienwareofficial/asus-vivobook-go-14-e1404ga-i3-n305-8gb-256gb-512gb-w11-ohs-m365b-14-0fhd-1732845916722332947/review",
        "https://www.tokopedia.com/wei-1/lenovo-ideapad-slim-3-ryzen-3-7320u-8gb-512gb-ssd-14-fhd-win11-ohs-1731326129899996635/review",
        "https://www.tokopedia.com/protechcom/hp-laptop-14-em0321au-em0332au-em0333au-ryzen-3-7320u-512gb-14-fhd-ips-w11-ohs-1731191939035334560/review",
        "https://www.tokopedia.com/teknotrend/axioo-mybook-hype-3-g11-intel-i3-1125g4-8gb-256gb-14-fhd-1734290285505382338/review",
        "https://www.tokopedia.com/alvinluo-shop/laptop-acer-n4000-4gb-1tb-14-win10-bergaransi-4gb-1tb/review",
        "https://www.tokopedia.com/gaminglaptopid/laptop-hp-14-ryzen-5-7530-8gb-512gb-w11-ohs-14-fhd-ips-1732627659899569771/review",
        "https://www.tokopedia.com/kaitocorner/bekas-laptop-lenovo-thinkpad-x1-yoga-gen-1-2-3-4-6-7-core-i5-14-touchscreen-360-second-berkualitas-bergaransi-1734254189372933907/review",
        "https://www.tokopedia.com/kalealaptop/laptop-lenovo-thinkpad-x260-core-i5-i7-gen-6-ram8-ssd256-super-murah-core-i5-gen-6-ram-4-ssd-128/review",
        "https://www.tokopedia.com/intelstore-id/laptop-lenovo-ideapad-slim-3i-14iru8-i3-1315u-8gb-512gb-ssd-14-fhd-w11-ohs-1733841534087234986/review",
        "https://www.tokopedia.com/gameridos/acer-travelmate-p40-i5-1335-16gb-512gb-w11-ohs-m365b-14-0wuxga-ips-1733032591360231009/review",
        "https://www.tokopedia.com/spacetech/asus-vivobook-14-a1405va-i5-13420h-16gb-512gb-ssd-14-wuxga-ips-win11-ohs-1731462023376832121/review",
        "https://www.tokopedia.com/agresid/acer-aspire-lite-14-al14-i3-n355-8gb-512gb-w11-ohs-14-0-fhd-ips-1731231329234158659/review",
        "https://www.tokopedia.com/spacetech/lenovo-ideapad-slim-3-i3-1315u-8gb-256gb-512gb-ssd-14-fhd-win11-ohs-1733122378085205625/review",
        "https://www.tokopedia.com/oceanla/laptop-slim-lenovo-thinkpad-t490s-intel-core-i7-i5-gen-8-16gb-murah-i7-gen-8-16gb-ssd-256gb-5eb3d/review",
        "https://www.tokopedia.com/laptopchoice/laptop-lenovo-thinkpad-x270-core-i3-i5-i7-layar-12-5-inch-murah-x270-i5gen6-ram4gb-ssd128gb-dfe9/review",
        "https://www.tokopedia.com/alvinluo-shop/laptop-lenovo-yoga-x380-touchscreen-i7-gen-8-berkualitas-spek-tinggi-1730860433623517127/review",
        "https://www.tokopedia.com/karyacitra/laptop-second-laptop-bekas-lenovo-thinkpad-t14-gen-2-i7-1165g7-ram-24gb-512gb-ssd-fhd-ips-win11pro-1730896898238351119/review",
        "https://www.tokopedia.com/spacetech/asus-vivobook-s14-s3407va-core-5-210h-16gb-1tb-ssd-14-2k-ips-win11-ohs-1732930166298805881/review",
        "https://www.tokopedia.com/haercom/acer-aspire-lite-14-al14-i3-n355-8gb-512gb-windows-11-pro-office-14-inch-wuxga-1731005169928537961/review",
        "https://www.tokopedia.com/sinarmulia/lenovo-ideapad-slim-3i-i5-13420h-512gb-ssd-8gb-16gb-wuxga-ips-win11-ohs-1731539466132227871/review",
        "https://www.tokopedia.com/gateway/lenovo-ideapad-slim-3-14-i5-13420h-16gb-512gb-w11-ohs-14-wuxga-ips-1731471601809720757/review",
        "https://www.tokopedia.com/gateway/laptop-tecno-megabook-k15s-ryzen-5-7430-8gb-512gb-windows-11-15-6-fhd-ips-1732721436989294005/review",
        "https://www.tokopedia.com/teknotrend/lenovo-ideapad-slim-3-14arp10-ryzen-5-7535hs-ram-16gb-512gb-ssd-windows-11-ohs-office-365-basic-14-inch-wuxga-ips-1734400825301764034/review",
        "https://www.tokopedia.com/winselindo/ibox-apple-macbook-air-m2-chip-2023-15-inch-512gb-256gb-ram-8gb-resmi-256gb-inter-starlight-f25e6/review",
        "https://www.tokopedia.com/specialistlaptop/laptop-lenovo-thinkpad-x280-core-i7-8650u-ram-16gb-ssd-win-10-original-ssd-128gb-16-gb/review",
        "https://www.tokopedia.com/royalltech/laptop-asus-zenbook-14-oled-ux3405ca-touch-intel-ultra-9-285h-32gb-1tb-ssd-w11-office-14-0fhd-1734229443254846967/review",
        "https://www.tokopedia.com/collinsofficial/apple-macbook-pro-14-m5-chip-16gb-24gb-ram-512gb-1tb-ssd-10-core-resmi-ibox-1733623681375700167/review",
        "https://www.tokopedia.com/spacetech/acer-aspire-go-ag14-72p-core-5-120u-16gb-512gb-ssd-14-wuxga-ips-win11-ohs-1733539867385235065/review",
    ]

    scraper = ReviewScraper()
    scraper.run(target_urls)


if __name__ == "__main__":
    main()
