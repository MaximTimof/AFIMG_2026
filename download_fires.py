import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin, urlparse
import re

# Папка для сохранения PDF-файлов внутри репозитория
DOWNLOAD_DIR = "fire_reports"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def get_target_url():
    current_date = datetime.now().strftime("%Y-%m-%d")
    return f"http://planet.iitp.ru/index.php?page_type=oper_prod&page=fire_report&start_date=2026-01-01&end_date={current_date}&region=all"

def download_new_pdfs():
    target_url = get_target_url()
    print(f"Проверка страницы: {target_url}")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(target_url, headers=headers, timeout=10)
        response.raise_for_status()
        response.encoding = 'utf-8'  # Явно указываем кодировку
    except requests.RequestException as e:
        print(f"Ошибка при запросе к главной странице: {e}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Сохраняем HTML для отладки
    with open('debug_page.html', 'w', encoding='utf-8') as f:
        f.write(response.text)
    print("HTML страницы сохранен в debug_page.html для анализа")
    
    # Пробуем разные способы поиска ссылок на PDF
    all_links = []
    
    # 1. Все ссылки, заканчивающиеся на .pdf
    pdf_links = [a for a in soup.find_all('a') if a.get('href', '').lower().endswith('.pdf')]
    all_links.extend(pdf_links)
    
    # 2. Ссылки с атрибутами data-* (могут содержать пути к файлам)
    data_links = [a for a in soup.find_all('a') if a.get('data-file') or a.get('data-url')]
    all_links.extend(data_links)
    
    # 3. Все ссылки, которые могут содержать download или file в href
    file_links = [a for a in soup.find_all('a') if 'download' in a.get('href', '').lower() or 
                  'file' in a.get('href', '').lower() or 'pdf' in a.get('href', '').lower()]
    all_links.extend(file_links)
    
    # 4. Ищем скрипты, которые могут генерировать ссылки
    scripts = soup.find_all('script')
    for script in scripts:
        if script.string:
            # Ищем URL с .pdf в скриптах
            pdf_urls = re.findall(r'https?://[^\s"\']+\.pdf', script.string)
            for url in pdf_urls:
                # Создаем фиктивную ссылку для обработки
                fake_a = soup.new_tag('a')
                fake_a['href'] = url
                filename = url.split('/')[-1]
                fake_a.string = filename
                all_links.append(fake_a)

    # Удаляем дубликаты
    unique_links = []
    seen_hrefs = set()
    for link in all_links:
        href = link.get('href', '')
        if href and href not in seen_hrefs:
            seen_hrefs.add(href)
            unique_links.append(link)

    print(f"Найдено потенциальных ссылок на PDF: {len(unique_links)}")
    
    # Выводим все найденные ссылки для диагностики
    for i, a in enumerate(unique_links[:10]):  # Показываем первые 10
        href = a.get('href', '')
        text = a.get_text().strip()
        print(f"  {i+1}. href: {href}, text: '{text}'")
    
    pdf_count = 0

    for a in unique_links:
        href = a.get('href', '').strip()
        filename = a.get_text().strip()
        
        if not href:
            continue
            
        # Если filename пустой, пытаемся извлечь имя из href
        if not filename:
            filename = href.split('/')[-1]
        
        # Проверяем, что это PDF (либо по расширению, либо по тексту ссылки)
        is_pdf = (filename.lower().endswith('.pdf') or 
                  '.pdf' in href.lower() or 
                  'pdf' in filename.lower())
        
        if not is_pdf:
            continue
        
        # Формируем полное имя файла
        if not filename.lower().endswith('.pdf'):
            if '.pdf' in filename:
                # Берем часть до .pdf
                filename = filename.split('.pdf')[0] + '.pdf'
            else:
                filename = filename + '.pdf'
        
        # Очищаем имя файла от недопустимых символов
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        local_path = os.path.join(DOWNLOAD_DIR, filename)
        
        # Скачиваем только если файла еще нет
        if not os.path.exists(local_path):
            # Формируем полный URL
            if href.startswith('http'):
                file_url = href
            elif href.startswith('//'):
                file_url = 'http:' + href
            else:
                # Используем базовый URL страницы
                base_url = "http://planet.iitp.ru"
                if href.startswith('/'):
                    file_url = base_url + href
                else:
                    file_url = urljoin(target_url, href)
            
            print(f"Обнаружен новый отчет: {filename}")
            print(f"Скачивание по ссылке: {file_url}")
            
            try:
                file_response = requests.get(file_url, headers=headers, timeout=30)
                
                # Проверяем содержимое
                content_type = file_response.headers.get('Content-Type', '').lower()
                
                # Если получили HTML вместо PDF, возможно нужна авторизация или редирект
                if 'text/html' in content_type:
                    print(f"  Предупреждение: получен HTML вместо PDF (возможно, требуется авторизация или ссылка недоступна)")
                    # Сохраняем HTML для анализа
                    debug_file = f"debug_{filename}.html"
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(file_response.text)
                    print(f"  HTML сохранен в {debug_file}")
                    continue
                
                if file_response.status_code == 200:
                    # Проверяем, что это действительно PDF (начинается с %PDF)
                    if file_response.content[:4] == b'%PDF':
                        with open(local_path, 'wb') as f:
                            f.write(file_response.content)
                        print(f"  ✓ Успешно сохранен: {filename} ({len(file_response.content)} байт)")
                        pdf_count += 1
                    else:
                        print(f"  ✗ Файл не является PDF (первые байты: {file_response.content[:20]})")
                else:
                    print(f"  ✗ Ошибка {file_response.status_code} при скачивании")
                    
            except Exception as e:
                print(f"  ✗ Ошибка при скачивании {filename}: {e}")
        else:
            print(f"Файл {filename} уже существует, пропускаем")
                
    print(f"\nРабота завершена. Успешно добавлено новых файлов: {pdf_count}")
    print(f"Проверьте файл debug_page.html для анализа структуры страницы")

if __name__ == "__main__":
    download_new_pdfs()
