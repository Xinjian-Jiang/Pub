import pyautogui
import random
import time
from data import *

def click(place, t):
    x = random.randint(place[0], place[2])
    y = random.randint(place[1], place[3])
    # print(f"点击位置: ({x}, {y})")
    pyautogui.moveTo(x, y, duration=0)
    pyautogui.click()
    time.sleep(t)