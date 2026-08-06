import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin

# Папка для сохранения PDF-файлов внутри репозитория
DOWNLOAD_DIR = "fire_reports"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Прямой базовый путь к папке с отчетами на сервере НИЦ «Планета»
BASE_FILE_URL = "http://iitp.ru" 

def get_target_url():
    current_date = datetime.now().strftime("%Y-%m-%d")
    return f"http://iitp.ru{current_date}&region=all"

def download_new_pdfs():
    url = get_target_url()
    print(f"Проверка страницы: {url}")
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Ошибка при запросе к сайту: {e}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    pdf_count = 0
    
    # Извлекаем весь текст со страницы и делим его на отдельные слова/строки
    all_text_tokens = soup.get_text().split()
    
    # Создаем список уникальных имен файлов, чтобы избежать дубликатов при парсинге
    discovered_files = set()
    for token in all_text_tokens:
        clean_token = token.strip()
        if clean_token.lower().endswith('.pdf'):
            discovered_files.add(clean_token)
            
    print(f"Найдено упоминаний PDF-файлов на странице: {len(discovered_files)}")
    
    # Запускаем скачивание найденных файлов
    for filename in sorted(discovered_files):
        local_path = os.path.join(DOWNLOAD_DIR, filename)
        
        # Скачиваем только те файлы, которых еще нет в репозитории
        if not os.path.exists(local_path):
            # Безопасно собираем прямую ссылку на файл
            file_url = urljoin(BASE_FILE_URL, filename)
            print(f"Обнаружен новый отчет: {filename}. Скачивание...")
            
            try:
                file_response = requests.get(file_url, headers=headers, timeout=20)
                content_type = file_response.headers.get('Content-Type', '')
                
                # Проверяем, что сервер отдал реальный PDF, а не HTML-страницу ошибки
                if file_response.status_code == 200 and 'html' not in content_type:
                    with open(local_path, 'wb') as f:
                        f.write(file_response.content)
                    print(f"Успешно сохранен: {filename} ({len(file_response.content)} байт)")
                    pdf_count += 1
                else:
                    print(f"Сервер отклонил запрос для {filename} (Статус: {file_response.status_code}). Возможно, файл еще не загружен на сервер.")
            except Exception as e:
                print(f"Ошибка при скачивании {filename}: {e}")
                
    print(f"Работа завершена. Успешно добавлено новых файлов в этот запуск: {pdf_count}")

if __name__ == "__main__":
    download_new_pdfs()
