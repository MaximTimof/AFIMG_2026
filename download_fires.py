import os
from datetime import datetime
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

# 1. Формируем URL с текущей датой
current_date = datetime.now().strftime("%Y-%m-%d")
url = f"http://planet.iitp.ru/index.php?page_type=oper_prod&page=fire_report&start_date=2026-01-01&end_date={current_date}&region=all"

# Папка для сохранения файлов
output_folder = "fire_reports"
os.makedirs(output_folder, exist_ok=True)

print(f"Загрузка страницы: {url}")

try:
    # 2. Получаем содержимое страницы
    response = requests.get(url, timeout=15)
    response.raise_for_status()

    # 3. Парсим HTML и ищем ссылки на PDF
    soup = BeautifulSoup(response.text, "html.parser")
    # Ищем все теги <a>, у которых атрибут href заканчивается на .pdf (без учета регистра)
    pdf_links = [
        a["href"]
        for a in soup.find_all("a", href=True)
        if a["href"].lower().endswith(".pdf")
    ]

    if not pdf_links:
        print("PDF-файлы на странице не найдены.")
    else:
        print(f"Найдено файлов для скачивания: {len(pdf_links)}")

        # 4. Скачиваем каждый файл
        for link in pdf_links:
            # Превращаем относительную ссылку в абсолютную, если это необходимо
            file_url = urljoin(url, link)
            filename = os.path.basename(link)
            file_path = os.path.join(output_folder, filename)

            print(f"Скачивание {filename}...", end="", flush=True)

            try:
                file_response = requests.get(file_url, timeout=30)
                file_response.raise_for_status()

                with open(file_path, "wb") as f:
                    f.write(file_response.content)
                print(" Успешно.")
            except Exception as e:
                print(f" Ошибка при скачивании файла: {e}")

    print("\nПроцесс завершен!")

except Exception as e:
    print(f"Ошибка при работе со страницей: {e}")
