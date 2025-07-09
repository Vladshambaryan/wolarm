import os                                                  # Работа с файловой системой и переменными окружения

import allure
import pytest                                              # Фреймворк для тестирования
from playwright.sync_api import sync_playwright            # Синхронное API Playwright для управления браузером
from PIL import Image, ImageChops                          # Библиотека Pillow для обработки изображений
import numpy as np                                         # NumPy для численных операций над изображениями

URL = "https://www.wolarm.org/%D5%AF%D5%A1%D5%BA"          # Целевая страница для скриншота
ETALON_PATH = "baseline/etalon.png"                        # Путь к эталонному изображению
CURRENT_PATH = "baseline/current.png"                      # Путь к текущему скриншоту
DIFF_PATH = "baseline/diff.png"                            # Путь к изображению с отличиями


@allure.step("Скриншот страницы 'կապ'")
def make_screenshot(path: str):                            # Делает полноэкранный скриншот страницы
    with sync_playwright() as p:                           # Инициализация Playwright
        browser = p.chromium.launch()                      # Запуск браузера Chromium
        context = browser.new_context(viewport={"width": 1280, "height": 3000})  # Установка размеров окна
        page = context.new_page()                          # Открытие новой вкладки
        page.goto(URL)                                     # Переход на заданный URL
        page.wait_for_load_state("networkidle")            # Ожидание окончания загрузки всех сетевых запросов
        page.wait_for_selector("footer", timeout=15000)    # Ожидание появления футера (как маркера полной загрузки)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")  # Скролл вниз страницы
        page.wait_for_timeout(5000)                        # Ждём, чтобы догрузилась динамика (lazy-load и т.п.)
        page.screenshot(path=path, full_page=True)         # Сохраняем полный скриншот
        browser.close()                                    # Закрываем браузер

@allure.step("Сравнение страницы 'կապ'")
def compare_images(img1_path: str, img2_path: str, diff_output: str) -> bool:
    img1 = Image.open(img1_path).convert("RGB")            # Загружаем первое изображение и конвертируем в RGB
    img2 = Image.open(img2_path).convert("RGB")            # Загружаем второе изображение и конвертируем в RGB

    if img1.size != img2.size:                             # Проверка совпадения размеров изображений
        print(f"❌ Размеры отличаются: {img1.size} vs {img2.size}")
        target_size = (min(img1.size[0], img2.size[0]), min(img1.size[1], img2.size[1]))  # Общая область
        img1_resized = img1.crop((0, 0, *target_size))     # Обрезаем первое изображение
        img2_resized = img2.crop((0, 0, *target_size))     # Обрезаем второе изображение
        diff = ImageChops.difference(img1_resized, img2_resized)  # Разница между изображениями
        diff.save(diff_output)                             # Сохраняем изображение отличий
        return False                                       # Возвращаем, что изображения различаются

    diff = ImageChops.difference(img1, img2)               # Вычисляем разницу между изображениями
    np_diff = np.array(diff)                               # Преобразуем в массив NumPy для анализа

    if np.any(np_diff > 20):                               # Проверка наличия значимых отличий по яркости (порог 20)
        diff.save(diff_output)                             # Сохраняем разницу, если она есть
        print(f"❌ Отличия найдены! См. файл: {diff_output}")
        return False                                       # Возвращаем, что есть отличия

    return True                                            # Изображения совпадают


@pytest.mark.verstka                                       # Маркировка теста для выборочного запуска
def test_layout_stability():                               # Основной тест стабильности верстки
    update_baseline = os.getenv("UPDATE_BASELINE", "false").lower() == "true"  # Проверка флага обновления эталона

    if update_baseline or not os.path.exists(ETALON_PATH): # Если указан флаг или отсутствует эталон
        os.makedirs(os.path.dirname(ETALON_PATH), exist_ok=True)  # Создаём директорию при необходимости
        make_screenshot(ETALON_PATH)                       # Создаём новый эталонный скриншот
        pytest.skip("✔ Эталон создан или обновлён.")       # Пропускаем тест с соответствующим сообщением

    os.makedirs(os.path.dirname(CURRENT_PATH), exist_ok=True)  # Создаём директорию для текущего скриншота
    make_screenshot(CURRENT_PATH)                        # Делаем текущий скриншот

    assert compare_images(ETALON_PATH, CURRENT_PATH, DIFF_PATH), \
        "❗ Вёрстка изменилась. См. файл diff.png."        # Сообщение об ошибке при отличиях
