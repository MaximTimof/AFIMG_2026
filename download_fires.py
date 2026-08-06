import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# Папка для сохранения PDF-файлов внутри репозитория
DOWNLOAD_DIR = "fire_reports"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# СТРОГО КОРЕНЬ САЙТА: без параметров, чтобы ссылки склеивались корректно
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
        
        # Безопасно получаем имя файла (избавляемся от параметров внутри href)
        clean_href = href.split('?')[0]
        filename = os.path.basename(clean_href)
        
        # Проверяем, что ссылка действительно ведет на .pdf
        if filename.lower().endswith('.pdf'):
            local_path = os.path.join(DOWNLOAD_DIR, filename)
            
            # Скачиваем только новые файлы
            if not os.path.exists(local_path):
                
                # Точная логика сборки URL для скачивания файла
                if href.startswith('http'):
                    file_url = href
                elif href.startswith('/'):
                    file_url = BASE_FILE_URL + href.lstrip('/')
                else:
                    file_url = BASE_FILE_URL + href
                    
                print(f"Найден новый файл: {filename}. Скачивание...")
                
                try:
                    file_response = requests.get(file_url, headers=headers, timeout=20)
                    
                    # Проверяем, что скачался реальный файл, а не страница ошибки text/html
                    content_type = file_response.headers.get('Content-Type', '')
                    
                    if file_response.status_code == 200 and 'html' not in content_type:
                        with open(local_path, 'wb') as f:
                            f.write(file_response.content)
                        print(f"Успешно скачан: {filename} ({len(file_response.content)} байт)")
                        pdf_count += 1
                    else:
                        print(f"Скачивание {filename} отклонено: неверный формат ответа сервера (возможно, 404 ошибка в виде HTML страницы)")
                except Exception as e:
                    print(f"Ошибка при скачивании {filename}: {e}")
                    
    print(f"Работа завершена. Успешно сохранено новых PDF-файлов: {pdf_count}")

if __name__ == "__main__":
    download_new_pdfs()
