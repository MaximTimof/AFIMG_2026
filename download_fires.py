import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# Папка для сохранения PDF-файлов внутри репозитория
DOWNLOAD_DIR = "fire_reports"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Базовая ссылка сайта для скачивания (подставьте точный URL, если он отличается)
BASE_FILE_URL = "http://planet.iitp.ru" 

def get_target_url():
    # Автоматически берет текущую дату
    current_date = datetime.now().strftime("%Y-%m-%d")
    return f"http://planet.iitp.ru{current_date}&region=all"

def download_new_pdfs():
    url = get_target_url()
    print(f"Проверка страницы: {url}")
    
    try:
        # User-Agent, чтобы сайт не блокировал запросы от GitHub
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Ошибка при запросе к сайту: {e}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    pdf_count = 0
    
    for link in soup.find_all('a', href=True):
        href = link['href']
        
        if href.endswith('.pdf'):
            filename = os.path.basename(href)
            local_path = os.path.join(DOWNLOAD_DIR, filename)
            
            # Скачиваем только если файла еще нет в папке репозитория
            if not os.path.exists(local_path):
                file_url = href if href.startswith('http') else BASE_FILE_URL + href
                print(f"Найден новый файл: {filename}. Скачивание...")
                
                try:
                    file_response = requests.get(file_url, headers=headers, timeout=20)
                    if file_response.status_code == 200:
                        with open(local_path, 'wb') as f:
                            f.write(file_response.content)
                        print(f"Успешно скачан: {filename}")
                        pdf_count += 1
                    else:
                        print(f"Не удалось скачать {filename} (Статус: {file_response.status_code})")
                except Exception as e:
                    print(f"Ошибка при скачивании {filename}: {e}")
                    
    print(f"Работа завершена. Скачано новых файлов: {pdf_count}")

if __name__ == "__main__":
    download_new_pdfs()
