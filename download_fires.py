import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import date, timedelta

# URL страницы со списком отчетов
# меняю даты вручную чтобы не упало август, потом июль, потом июнь, потом от января по май
# Получаем текущую дату по UTC и дату 7 дней назад

end_date = date.today()
start_date = end_date - timedelta(days=7)

# Формируем итоговую ссылку
TARGET_URL = f"http://planet.iitp.ru/index.php?page_type=oper_prod&page=fire_report&start_date={start_date}&end_date={end_date}&region=all"

# Папка, куда будут сохраняться файлы
OUTPUT_DIR = "downloaded_pdfs"

def download_all_pdfs():
    # Создаем папку для сохранения, если её нет
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"Создана папка: {OUTPUT_DIR}")

    print("Загружаю страницу для парсинга...")
    try:
        response = requests.get(TARGET_URL)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Не удалось загрузить страницу: {e}")
        return

    # Парсим HTML-код страницы
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Ищем все теги <a>, у которых href заканчивается на .pdf
    pdf_links = []
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if href.lower().endswith(".pdf"):
            # Исправляем ссылки вида //planet.iitp.ru... добавляя http:
            if href.startswith("//"):
                full_url = "http:" + href
            else:
                full_url = urljoin(TARGET_URL, href)
            pdf_links.append(full_url)

    total_files = len(pdf_links)
    print(f"Найдено PDF-файлов для скачивания: {total_files}")

    if total_files == 0:
        print("Проверьте структуру страницы, ссылки не найдены.")
        return

    # Скачиваем каждый файл
    for index, url in enumerate(pdf_links, start=1):
        # Извлекаем имя файла из ссылки
        filename = os.path.basename(url)
        save_path = os.path.join(OUTPUT_DIR, filename)
        
        print(f"[{index}/{total_files}] Скачиваю: {filename}...")
        
        try:
            # Скачиваем файл потоком (stream=True) для экономии памяти
            file_response = requests.get(url, stream=True)
            file_response.raise_for_status()
            
            with open(save_path, "wb") as f:
                for chunk in file_response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        
        except requests.exceptions.RequestException as e:
            print(f"❌ Ошибка при скачивании {filename}: {e}")
            continue

    print("\n🎉 Все доступные файлы успешно скачаны!")

if __name__ == "__main__":
    download_all_pdfs()
