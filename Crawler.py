import os
import re
import time
import json
import requests
from urllib.parse import urlparse, unquote

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


START_URL = "https://www.justice.gov/epstein/doj-disclosures/data-set-1-files"
SAVE_DIR = r"C:\Users\youruser\Desktop\JE-Files"  ######################################### Put folder path here INSIDE the quotes 
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
WAIT_SECONDS = 20
REQUEST_DELAY = 0.3
PROGRESS_FILE = "progress.json"
DOWNLOADED_LOG = "downloaded.json"


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def load_json_file(path: str, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default


def save_json_file(path: str, data) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_state() -> tuple[dict, set[str]]:
    progress = load_json_file(PROGRESS_FILE, {"last_url": START_URL})
    downloaded = set(load_json_file(DOWNLOADED_LOG, []))
    return progress, downloaded


def save_progress(current_url: str) -> None:
    save_json_file(PROGRESS_FILE, {"last_url": current_url})


def save_downloaded(downloaded: set[str]) -> None:
    save_json_file(DOWNLOADED_LOG, sorted(downloaded))


def sanitize_filename(name: str) -> str:
    name = unquote(name)
    name = re.sub(r'[<>:"/\\|?*]+', "_", name).strip()
    return name[:220] if name else "file"


def get_extension(url: str) -> str:
    return os.path.splitext(urlparse(url).path)[1].lower()


def is_allowed_file(url: str) -> bool:
    return get_extension(url) in ALLOWED_EXTENSIONS


def filename_from_url(url: str) -> str:
    name = os.path.basename(urlparse(url).path)
    return sanitize_filename(name or "file")


def download_file(url: str, folder: str, downloaded_log: set[str]) -> None:
    ensure_dir(folder)
    filename = filename_from_url(url)
    filepath = os.path.join(folder, filename)

    if url in downloaded_log or os.path.exists(filepath):
        print(f"[skip] {filename}")
        downloaded_log.add(url)
        save_downloaded(downloaded_log)
        return

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://www.justice.gov/epstein"
    }

    try:
        with requests.get(url, headers=headers, stream=True, timeout=60) as resp:
            resp.raise_for_status()
            content_type = resp.headers.get("Content-Type", "").lower()

            if not (
                "pdf" in content_type
                or "png" in content_type
                or "jpeg" in content_type
                or "jpg" in content_type
                or is_allowed_file(url)
            ):
                print(f"[skip-content-type] {url} ({content_type})")
                return

            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

        downloaded_log.add(url)
        save_downloaded(downloaded_log)
        print(f"[downloaded] {filename}")
        time.sleep(REQUEST_DELAY)

    except Exception as e:
        print(f"[failed] {url} -> {e}")


def click_age_gate_if_present(driver) -> None:
    possible_xpaths = [
        "//button[normalize-space()='Yes']",
        "//input[@type='button' and @value='Yes']",
        "//a[normalize-space()='Yes']",
        "//*[self::button or self::a][contains(., 'Yes')]",
    ]

    for xpath in possible_xpaths:
        try:
            elem = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            elem.click()
            time.sleep(1.5)
            print("[age-gate] clicked Yes")
            return
        except Exception:
            pass


def get_current_dataset_name(driver) -> str:
    try:
        h1 = driver.find_element(By.TAG_NAME, "h1").text.strip()
        return sanitize_filename(h1.replace(" Files", ""))
    except Exception:
        return "Unknown_Data_Set"


def collect_file_links(driver) -> list[str]:
    links = []
    anchors = driver.find_elements(By.TAG_NAME, "a")

    for a in anchors:
        href = a.get_attribute("href")
        if href and is_allowed_file(href):
            links.append(href)

    return list(dict.fromkeys(links))


def find_next_page_button(driver):
    xpaths = [
        "//a[normalize-space()='Next']",
        "//a[contains(., 'Next')]",
    ]
    for xpath in xpaths:
        try:
            return driver.find_element(By.XPATH, xpath)
        except Exception:
            pass
    return None


def find_next_dataset_button(driver):
    xpaths = [
        "//a[contains(., 'Next Data Set')]",
    ]
    for xpath in xpaths:
        try:
            return driver.find_element(By.XPATH, xpath)
        except Exception:
            pass
    return None


def safe_click(driver, element) -> None:
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
    time.sleep(0.5)
    driver.execute_script("arguments[0].click();", element)
    time.sleep(2)


def main():
    ensure_dir(SAVE_DIR)
    progress, downloaded_log = load_state()

    print("Choose startup mode:")
    print("1 = Restart from beginning and check for missed files")
    print("2 = Continue from your last saved spot")
    choice = input("Enter 1 or 2: ").strip()

    if choice == "1":
        start_url = START_URL
        print("[mode] Restarting from the beginning. Already downloaded files will be skipped.")
    else:
        start_url = progress.get("last_url", START_URL)
        print(f"[mode] Continuing from: {start_url}")

    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(options=chrome_options)

    seen_pages = set()

    try:
        driver.get(start_url)
        click_age_gate_if_present(driver)

        while True:
            current_url = driver.current_url
            save_progress(current_url)

            dataset_name = get_current_dataset_name(driver)
            dataset_folder = os.path.join(SAVE_DIR, dataset_name)
            ensure_dir(dataset_folder)

            page_key = f"{dataset_name}::{current_url}"
            if page_key in seen_pages:
                print("[stop] page already processed")
                break
            seen_pages.add(page_key)

            print(f"\n[dataset] {dataset_name}")
            print(f"[page] {current_url}")

            links = collect_file_links(driver)
            print(f"[found-files] {len(links)}")

            for url in links:
                download_file(url, dataset_folder, downloaded_log)

            next_btn = find_next_page_button(driver)

            if next_btn:
                print("[nav] clicking Next page")
                safe_click(driver, next_btn)
                click_age_gate_if_present(driver)
                continue

            next_dataset_btn = find_next_dataset_button(driver)
            if next_dataset_btn:
                print("[nav] clicking Next Data Set")
                safe_click(driver, next_dataset_btn)
                click_age_gate_if_present(driver)
                continue

            print("[done] no more Next page or Next Data Set")
            break

    finally:
        driver.quit()

    print(f"\nFinished. Tracked downloaded files: {len(downloaded_log)}")


if __name__ == "__main__":
    main()
