from io import BytesIO
from PIL import Image
import os
import subprocess
from attr_ocr import get_attr
from resize import _adb_command, ratio_to_screen

def SS():
    screen = _adb_screenshot()
    r, g, b = screen.getpixel(ratio_to_screen(139 / 540, 313 / 1080))
    if r - g >100 and r - b > 100:
        return 1
    r, g, b = screen.getpixel(ratio_to_screen(291 / 540, 313 / 1080))
    if r - g >100 and r - b > 100:
        return 2
    r, g, b = screen.getpixel(ratio_to_screen(442 / 540, 313 / 1080))
    if r - g >100 and r - b > 100:
        return 3
    return 0

def _adb_screenshot():
    raw = subprocess.check_output(_adb_command("exec-out", "screencap", "-p"))
    return Image.open(BytesIO(raw)).convert("RGB")

def _crop_ratio(screenshot, bbox):
    x1, y1 = ratio_to_screen(bbox[0], bbox[1])
    x2, y2 = ratio_to_screen(bbox[2], bbox[3])
    left, right = sorted((x1, x2))
    top, bottom = sorted((y1, y2))
    return screenshot.crop((left, top, right + 1, bottom + 1))

def get_model():
    import cv2
    import numpy as np
    screenshot = _adb_screenshot()
    screenshot = _crop_ratio(screenshot, [0.269531, 0.273083, 0.728516, 0.554470])
    screenshot = screenshot.convert('RGB')  # 确保格式一致
    screenshot_np = np.array(screenshot)  # 转为数组
    screenshot_gray = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2GRAY)  # 转灰度图
    best_match = None
    highest_score = 0.0
    for file_name in os.listdir("模型"):
        if file_name.lower().endswith('.bmp'):
            file_path = os.path.join("模型", file_name)
            bmp_image = Image.open(file_path).convert('RGB')
            bmp_image_np = np.array(bmp_image)
            bmp_image_gray = cv2.cvtColor(bmp_image_np, cv2.COLOR_RGB2GRAY)
            if screenshot_gray.shape != bmp_image_gray.shape:
                bmp_image_gray = cv2.resize(bmp_image_gray, (screenshot_gray.shape[1], screenshot_gray.shape[0]))
            score = cv2.matchTemplate(screenshot_gray, bmp_image_gray, cv2.TM_CCOEFF_NORMED).max()
            if score > highest_score:
                highest_score = score
                best_match = file_name
    return best_match.replace(".bmp","")

