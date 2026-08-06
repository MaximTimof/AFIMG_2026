import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urlparse, parse_qs

# Папка для сохранения PDF-файлов внутри репозитория
DOWNLOAD_DIR = "fire_reports"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Базовый домен сайта
BASE_FILE_URL = "http://planet.iitp.ru/" 

def get_target_url():
    current_date = datetime.now().strftime("%Y-%m-%d")
    return f"http://planet.iitp.ru/index.php?page_type=oper_prod&page=fire_report&start_date=2026-01-01&end_date={current_date}&region=all"

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
    
    for link in soup.find_all('a', href=True):
        href = link['href']
        
        # Разбираем параметры ссылки, так как путь к PDF зашит внутри параметра 'filename'
        parsed_url = urlparse(href)
        query_params = parse_qs(parsed_url.query)
        
        # Проверяем, есть ли в ссылке параметр filename и ведет ли он на pdf
        if 'filename' in query_params:
            relative_pdf_path = query_params['filename'][0]  # Получаем например: images/oper_prod/fire_report/ALTAY_...pdf
            
            if relative_pdf_path.lower().endswith('.pdf'):
                filename = os.path.basename(relative_pdf_path)
                local_path = os.path.join(DOWNLOAD_DIR, filename)
                
                # Скачиваем только новые файлы
                if not os.path.exists(local_path):
                    # Собираем правильный прямой URL: http://iitp.ru
                    file_url = BASE_FILE_URL + relative_pdf_path.lstrip('/')
                    print(f"Найден новый файл: {filename}. Скачивание с {file_url}...")
                    
                    try:
                        file_response = requests.get(file_url, headers=headers, timeout=20)
                        content_type = file_response.headers.get('Content-Type', '')
                        
                        # Проверяем, что скачался реальный файл, а не html-страница ошибки
                        if file_response.status_code == 200 and 'html' not in content_type:
                            with open(local_path, 'wb') as f:
                                f.write(file_response.content)
                            print(f"Успешно скачан: {filename} ({len(file_response.content)} байт)")
                            pdf_count += 1
                        else:
                            print(f"Скачивание {filename} отклонено: неверный ответ сервера (Статус: {file_response.status_code})")
                    except Exception as e:
                        print(f"Ошибка при скачивании {filename}: {e}")
                        
    print(f"Работа завершена. Успешно сохранено новых PDF-файлов: {pdf_count}")

if __name__ == "__main__":
    download_new_pdfs()
