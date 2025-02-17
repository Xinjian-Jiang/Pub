from PIL import Image
import pytesseract
import pyscreenshot as ImageGrab
from collections import Counter
import os
import pyautogui
import cv2
import numpy as np
from data import *
import keyboard

pytesseract.pytesseract.tesseract_cmd = r"D:\\Programs\\Tesseract\\tesseract.exe"

def SS():
    screen = ImageGrab.grab()
    r, g, b = screen.getpixel((151, 315))
    if r - g >100 and r - b > 100:
        return 1
    r, g, b = screen.getpixel((309, 315))
    if r - g >100 and r - b > 100:
        return 2
    r, g, b = screen.getpixel((467, 315))
    if r - g >100 and r - b > 100:
        return 3
    return 0

def get_attr():
    results = []
    for bbox in ranges:
        x1, y1, x2, y2 = bbox
        screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
        text = pytesseract.image_to_string(screenshot, config='--psm 7 digits')
        results.append(int(text.strip().replace(".","")))
    return results

def get_model():
    screenshot = pyautogui.screenshot(region=(150, 265, 262, 328))
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

def check(back):
    if keyboard.is_pressed('space'):
        return False
    if back == get_back():
        return True
    return False

def get_back():
    screenshot = pyautogui.screenshot(region=(0, 37, 562, 802))
    screenshot = screenshot.convert('RGB')
    screenshot_np = np.array(screenshot)
    screenshot_gray = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2GRAY)
    best_match = None
    highest_score = 0.0
    for file_name in os.listdir("场景"):
        if file_name.lower().endswith('.bmp'):
            file_path = os.path.join("场景", file_name)
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

def get_job():
    def most_similar_string(target):
        def calculate_similarity(str1, str2):
            counter1, counter2 = Counter(str1), Counter(str2)
            intersection = counter1 & counter2
            return sum(intersection.values())
        string_array = ["战士","法师","刺客","圣职","火枪手","野蛮人"]
        most_similar = None
        highest_similarity = -1
        for candidate in string_array:
            similarity = calculate_similarity(target, candidate)
            if similarity > highest_similarity:
                highest_similarity = similarity
                most_similar = candidate
        return most_similar
    bbox=[189, 197, 374, 224]
    screenshot = ImageGrab.grab(bbox=bbox)
    screenshot = screenshot.convert("L")
    text = pytesseract.image_to_string(screenshot, lang='chi_sim', config='--psm 7')
    text = text.strip().replace(" ", "")
    return most_similar_string(text)