import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin

# Папка для сохранения PDF-файлов внутри репозитория
DOWNLOAD_DIR = "fire_reports"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
#http://planet.iitp.ru/index.php?page_type=oper_prod&page=fire_report&start_date=2026-01-01&end_date=2026-08-06&region=all
def get_target_url():
    current_date = datetime.now().strftime("%Y-%m-%d")
    return f"http://planet.iitp.ru/index.php?page_type=oper_prod&page=fire_report&start_date=2026-01-01&end_date={current_date}&region=all"

def download_new_pdfs():
    target_url = get_target_url()
    print(f"Проверка страницы: {target_url}")
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(target_url, headers=headers, timeout=3)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Ошибка при запросе к главной странице: {e}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Находим все ссылки на файлы с классом 'file-link' или просто заканчивающиеся на .pdf
    file_links = soup.find_all('a', class_='file-link')
    if not file_links:
        # Резервный поиск, если класс вдруг изменится
        file_links = [a for a in soup.find_all('a') if a.get('href', '').lower().endswith('.pdf')]

    print(f"Найдено ссылок на PDF-файлы на странице: {len(file_links)}")
    pdf_count = 0

    for a in file_links:
        href = a.get('href', '').strip()
        filename = a.get_text().strip()
        
        if not href or not filename.lower().endswith('.pdf'):
            continue
            
        local_path = os.path.join(DOWNLOAD_DIR, filename)
        
        # Скачиваем только если файла еще нет в репозитории
        if not os.path.exists(local_path):
            # Если ссылка начинается с '//', добавляем 'http:' протокол
            if href.startswith('//'):
                file_url = 'http:' + href
            else:
                file_url = urljoin("http://planet.iitp.ru/index.php?page_type=oper_prod&page=fire_report&start_date=2026-01-01&end_date={current_date}&region=all", href)
                
            print(f"Обнаружен новый отчет: {filename}")
            print(f"Скачивание по ссылке: {file_url}")
            
            try:
                file_response = requests.get(file_url, headers=headers, timeout=20)
                content_type = file_response.headers.get('Content-Type', '')
                
                # Защита: проверяем, что это не HTML-страница с ошибкой, а реальный PDF
                if file_response.status_code == 200 and 'html' not in content_type:
                    with open(local_path, 'wb') as f:
                        f.write(file_response.content)
                    print(f"Успешно сохранен: {filename} ({len(file_response.content)} байт)")
                    pdf_count += 1
                else:
                    print(f"Не удалось скачать {filename} (Статус: {file_response.status_code}).")
            except Exception as e:
                print(f"Ошибка при скачивании {filename}: {e}")
                
    print(f"Работа завершена. Успешно добавлено новых файлов: {pdf_count}")

if __name__ == "__main__":
    download_new_pdfs()
