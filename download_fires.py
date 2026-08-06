import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
# http://planet.iitp.ru/index.php?page_type=oper_prod&page=fire_report&start_date=2026-01-01&end_date=2026-08-06&region=all
# Папка для сохранения PDF-файлов внутри репозитория
DOWNLOAD_DIR = "fire_reports"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Изменено по вашему запросу: правильный базовый домен сайта
BASE_FILE_URL = "http://planet.iitp.ru/index.php?page_type=oper_prod&page=fire_report&start_date=2026-01-01&end_date=" 

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
    
    # Ищем все ссылки на странице
    for link in soup.find_all('a', href=True):
        href = link['href']
        
        # Очищаем href от возможных GET-параметров, чтобы вытащить имя файла
        clean_href = href.split('?')[0]
        filename = os.path.basename(clean_href)
        
        # Проверяем, что ссылка действительно ведет на PDF
        if filename.endswith('.pdf'):
            local_path = os.path.join(DOWNLOAD_DIR, filename)
            
            # Скачиваем только новые файлы, которых еще нет в репозитории
            if not os.path.exists(local_path):
                # Если ссылка относительная (например, "images/pdf/..."), склеиваем с базовым доменом
                if href.startswith('http'):
                    file_url = href
                elif href.startswith('/'):
                    file_url = BASE_FILE_URL + href.lstrip('/')
                else:
                    file_url = BASE_FILE_URL + href
                    
                print(f"Найден новый файл: {filename}. Скачивание...")
                
                try:
                    file_response = requests.get(file_url, headers=headers, timeout=20)
                    if file_response.status_code == 200:
                        with open(local_path, 'wb') as f:
                            f.write(file_response.content)
                        print(f"Успешно скачан: {filename}")
                        pdf_count += 1
                    else:
                        print(f"Не удалось скачать {filename} (Статус сервера: {file_response.status_code})")
                except Exception as e:
                    print(f"Ошибка при скачивании {filename}: {e}")
                    
    print(f"Работа завершена. Скачано новых файлов: {pdf_count}")

if __name__ == "__main__":
    download_new_pdfs()
