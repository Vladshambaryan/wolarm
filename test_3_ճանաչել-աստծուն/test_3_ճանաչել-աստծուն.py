import os
import pytest
from playwright.sync_api import sync_playwright
from PIL import Image, ImageChops
import numpy as np

URL = "https://www.wolarm.org/%D5%B3%D5%A1%D5%B6%D5%A1%D5%B9%D5%A5%D5%AC-%D5%A1%D5%BD%D5%BF%D5%AE%D5%B8%D6%82%D5%B6"
ETALON_PATH = "baseline/etalon.png"
CURRENT_PATH = "baseline/current.png"
DIFF_PATH = "baseline/diff.png"



def make_screenshot(path: str):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": 1280, "height": 3000})
        page = context.new_page()
        page.goto(URL)
        page.wait_for_load_state("networkidle")
        page.wait_for_selector("footer", timeout=15000)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(5000)  # Ждём подгрузку динамики
        page.screenshot(path=path, full_page=True)
        browser.close()


def compare_images(img1_path: str, img2_path: str, diff_output: str) -> bool:
    img1 = Image.open(img1_path).convert("RGB")
    img2 = Image.open(img2_path).convert("RGB")

    if img1.size != img2.size:
        print(f"❌ Размеры отличаются: {img1.size} vs {img2.size}")
        # Масштабируем меньшую по высоте, чтобы можно было корректно посчитать разницу
        target_size = (min(img1.size[0], img2.size[0]), min(img1.size[1], img2.size[1]))
        img1_resized = img1.crop((0, 0, *target_size))
        img2_resized = img2.crop((0, 0, *target_size))
        diff = ImageChops.difference(img1_resized, img2_resized)
        diff.save(diff_output)
        return False

    diff = ImageChops.difference(img1, img2)
    np_diff = np.array(diff)

    if np.any(np_diff > 20):
        diff.save(diff_output)
        print(f"❌ Отличия найдены! См. файл: {diff_output}")
        return False

    return True


@pytest.mark.verstka
def test_layout_stability():
    update_baseline = os.getenv("UPDATE_BASELINE", "false").lower() == "true"

    if update_baseline or not os.path.exists(ETALON_PATH):
        os.makedirs(os.path.dirname(ETALON_PATH), exist_ok=True)
        make_screenshot(ETALON_PATH)
        pytest.skip("✔ Эталон создан или обновлён.")

    os.makedirs(os.path.dirname(CURRENT_PATH), exist_ok=True)
    make_screenshot(CURRENT_PATH)

    assert compare_images(ETALON_PATH, CURRENT_PATH, DIFF_PATH), \
        "❗ Вёрстка изменилась. См. файл diff.png."