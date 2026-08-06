import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin, urlparse
import re
import sys

# Папка для сохранения PDF-файлов (относительный путь)
DOWNLOAD_DIR = "fire_reports"

def ensure_directory():
    """Создает директорию, если её нет"""
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    print(f"Директория для сохранения: {os.path.abspath(DOWNLOAD_DIR)}")

def get_target_url():
    """Формирует URL для парсинга"""
    current_date = datetime.now().strftime("%Y-%m-%d")
    return f"http://planet.iitp.ru/index.php?page_type=oper_prod&page=fire_report&start_date=2026-07-01&end_date={current_date}&region=all"

def download_new_pdfs():
    """Основная функция скачивания PDF-файлов"""
    
    # Создаем директорию
    ensure_directory()
    
    target_url = get_target_url()
    print(f"Проверка страницы: {target_url}")
    
    # Заголовки для имитации браузера
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    }
    
    try:
        response = requests.get(target_url, headers=headers, timeout=30)
        response.raise_for_status()
        response.encoding = 'utf-8'
        print(f"Статус ответа: {response.status_code}")
        print(f"Длина HTML: {len(response.text)} символов")
    except requests.RequestException as e:
        print(f"❌ Ошибка при запросе к главной странице: {e}")
        return

    # Парсим HTML
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Сохраняем HTML для отладки (полезно в GitHub Actions)
    with open('debug_page.html', 'w', encoding='utf-8') as f:
        f.write(response.text)
    print("✅ HTML страницы сохранен в debug_page.html")
    
    # Ищем все ссылки
    all_links = []
    
    # 1. Ссылки с классом file-link
    file_links = soup.find_all('a', class_='file-link')
    all_links.extend(file_links)
    
    # 2. Все ссылки, содержащие .pdf
    pdf_links = [a for a in soup.find_all('a') 
                 if a.get('href', '').lower().endswith('.pdf')]
    all_links.extend(pdf_links)
    
    # 3. Ссылки с атрибутами, указывающими на файлы
    data_links = [a for a in soup.find_all('a') 
                  if a.get('data-file') or a.get('data-url') or a.get('download')]
    all_links.extend(data_links)
    
    # 4. Ищем ссылки в скриптах
    scripts = soup.find_all('script')
    for script in scripts:
        if script.string:
            # Ищем URL с .pdf в скриптах
            pdf_urls = re.findall(r'https?://[^\s"\'<>]+\.pdf', script.string)
            for url in pdf_urls:
                fake_a = soup.new_tag('a')
                fake_a['href'] = url
                fake_a.string = url.split('/')[-1]
                all_links.append(fake_a)
    
    # Удаляем дубликаты
    unique_links = []
    seen_hrefs = set()
    for link in all_links:
        href = link.get('href', '')
        if href and href not in seen_hrefs:
            seen_hrefs.add(href)
            unique_links.append(link)
    
    print(f"🔍 Найдено уникальных ссылок: {len(unique_links)}")
    
    # Выводим первые 10 ссылок для диагностики
    print("Первые 10 найденных ссылок:")
    for i, a in enumerate(unique_links[:10]):
        href = a.get('href', '')
        text = a.get_text().strip()[:50]  # Ограничиваем длину текста
        print(f"  {i+1}. href: {href[:100]}... text: '{text}'")
    
    pdf_count = 0
    downloaded_files = []

    for a in unique_links:
        href = a.get('href', '').strip()
        filename = a.get_text().strip()
        
        if not href:
            continue
        
        # Проверяем, что это PDF
        is_pdf = ('.pdf' in href.lower() or 
                  (filename and '.pdf' in filename.lower()) or
                  'pdf' in href.lower())
        
        if not is_pdf:
            continue
        
        # Формируем имя файла
        if not filename or filename == href:
            filename = href.split('/')[-1]
            if '?' in filename:
                filename = filename.split('?')[0]
        
        # Убеждаемся, что имя заканчивается на .pdf
        if not filename.lower().endswith('.pdf'):
            if '.pdf' in filename.lower():
                # Берем часть до .pdf
                pdf_pos = filename.lower().find('.pdf')
                filename = filename[:pdf_pos + 4]
            else:
                filename = filename + '.pdf'
        
        # Очищаем имя файла от недопустимых символов
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        # Если имя слишком длинное, обрезаем
        if len(filename) > 200:
            name, ext = os.path.splitext(filename)
            filename = name[:196] + ext
        
        local_path = os.path.join(DOWNLOAD_DIR, filename)
        abs_path = os.path.abspath(local_path)
        
        # Проверяем, существует ли файл
        if os.path.exists(local_path):
            print(f"⏭️ Файл {filename} уже существует, пропускаем")
            continue
        
        # Формируем полный URL
        if href.startswith('http://') or href.startswith('https://'):
            file_url = href
        elif href.startswith('//'):
            file_url = 'http:' + href
        else:
            base_url = "http://planet.iitp.ru"
            if href.startswith('/'):
                file_url = base_url + href
            else:
                file_url = urljoin(target_url, href)
        
        print(f"📄 Обнаружен новый отчет: {filename}")
        print(f"   Ссылка: {file_url}")
        
        try:
            # Скачиваем файл
            file_response = requests.get(file_url, headers=headers, timeout=60, stream=True)
            
            # Проверяем статус
            if file_response.status_code != 200:
                print(f"   ❌ Ошибка {file_response.status_code}")
                continue
            
            content_type = file_response.headers.get('Content-Type', '').lower()
            content_length = file_response.headers.get('Content-Length')
            
            # Проверяем, не HTML ли это
            if 'text/html' in content_type:
                print(f"   ⚠️ Получен HTML вместо PDF (возможно, требуется авторизация)")
                # Сохраняем HTML для анализа
                debug_file = f"debug_{filename.replace('.pdf', '')}.html"
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(file_response.text[:1000])  # Сохраняем только начало
                print(f"   HTML сохранен в {debug_file}")
                continue
            
            # Скачиваем содержимое
            content = file_response.content
            
            # Проверяем, что это действительно PDF
            if len(content) < 100:
                print(f"   ❌ Файл слишком маленький ({len(content)} байт)")
                continue
                
            if content[:4] != b'%PDF':
                print(f"   ❌ Файл не является PDF (первые байты: {content[:20]})")
                # Проверяем, может это ZIP или другой формат
                if content[:2] == b'PK':
                    print(f"   Возможно, это ZIP-архив, переименовываем...")
                    filename = filename.replace('.pdf', '.zip')
                    local_path = os.path.join(DOWNLOAD_DIR, filename)
                else:
                    continue
            
            # Сохраняем файл
            with open(local_path, 'wb') as f:
                f.write(content)
            
            file_size = len(content)
            print(f"   ✅ Успешно сохранен: {filename} ({file_size} байт)")
            pdf_count += 1
            downloaded_files.append(filename)
            
        except requests.Timeout:
            print(f"   ❌ Таймаут при скачивании {filename}")
        except requests.RequestException as e:
            print(f"   ❌ Ошибка при скачивании {filename}: {e}")
        except Exception as e:
            print(f"   ❌ Неожиданная ошибка: {e}")
    
    # Итоговый отчет
    print("\n" + "="*50)
    print(f"📊 РЕЗУЛЬТАТЫ:")
    print(f"   Всего найдено ссылок: {len(unique_links)}")
    print(f"   Скачано новых PDF: {pdf_count}")
    if downloaded_files:
        print(f"   Скачанные файлы:")
        for f in downloaded_files:
            print(f"     - {f}")
    
    # Проверяем содержимое директории
    try:
        files_in_dir = os.listdir(DOWNLOAD_DIR)
        print(f"   Всего файлов в директории: {len(files_in_dir)}")
        if files_in_dir:
            print(f"   Примеры файлов:")
            for f in files_in_dir[:5]:
                file_path = os.path.join(DOWNLOAD_DIR, f)
                size = os.path.getsize(file_path)
                print(f"     - {f} ({size} байт)")
    except Exception as e:
        print(f"   ❌ Ошибка при проверке директории: {e}")
    
    print("="*50)
    
    # Возвращаем количество скачанных файлов для использования в GitHub Actions
    return pdf_count

if __name__ == "__main__":
    try:
        count = download_new_pdfs()
        print(f"\n✅ Скрипт завершен. Скачано файлов: {count}")
        sys.exit(0 if count >= 0 else 1)
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        sys.exit(1)
