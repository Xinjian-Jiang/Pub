import os
import re
import subprocess
import time

GAME_PACKAGE = os.environ.get("GAME_PACKAGE", "com.taojin.dungeon2")
WAYDROID_ADB = "192.168.240.112:5555"
GAME_BOUNDS = None

def _adb_command(*args):
    command = ["adb"]
    serial = os.environ.get("ADB_SERIAL")
    if serial:
        command.extend(["-s", serial])
    command.extend(args)
    return command

def _start_adb_server():
    subprocess.run(["adb", "start-server"], check=True)

def _start_waydroid():
    result = subprocess.run(
        ["waydroid", "status"],
        capture_output=True,
        text=True,
    )
    if "Session:\tRUNNING" not in result.stdout:
        subprocess.Popen(
            ["waydroid", "show-full-ui"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(5)

def _has_adb_device():
    result = subprocess.run(
        ["adb", "devices"],
        check=True,
        capture_output=True,
        text=True,
    )
    return any(line.strip().endswith("\tdevice") for line in result.stdout.splitlines())

def _ensure_adb_device():
    _start_waydroid()
    _start_adb_server()
    if _has_adb_device():
        return

    subprocess.run(["adb", "connect", WAYDROID_ADB], check=False, capture_output=True, text=True)
    for _ in range(20):
        if _has_adb_device():
            return
        time.sleep(0.5)

    raise RuntimeError(f"adb 没有在线设备，已尝试连接 {WAYDROID_ADB}")

def _get_screen_size():
    _ensure_adb_device()
    result = subprocess.run(
        _adb_command("shell", "wm", "size"),
        check=True,
        capture_output=True,
        text=True,
    )
    match = re.findall(r"(\d+)x(\d+)", result.stdout)
    if not match:
        raise RuntimeError("无法从 adb shell wm size 获取屏幕尺寸")
    width, height = match[-1]
    return int(width), int(height)

def window_init():
    global GAME_BOUNDS

    _ensure_adb_device()

    result = subprocess.run(
        _adb_command("shell", "dumpsys", "window", "windows"),
        check=True,
        capture_output=True,
        text=True,
    )
    pattern = rf"Window #\d+ Window\{{[^\n]*{re.escape(GAME_PACKAGE)}[^\n]*\}}:.*?mBounds=Rect\((\d+), (\d+) - (\d+), (\d+)\)"
    match = re.search(pattern, result.stdout, re.S)
    if match:
        GAME_BOUNDS = tuple(map(int, match.groups()))
        return GAME_BOUNDS

    match = re.search(r"mCurrentFocus=Window\{[^\n]*\s(\S+)/\S+.*?mBounds=Rect\((\d+), (\d+) - (\d+), (\d+)\)", result.stdout, re.S)
    if match:
        GAME_BOUNDS = tuple(map(int, match.groups()[1:]))
        return GAME_BOUNDS

    screen_width, screen_height = _get_screen_size()
    game_width = round(screen_height * 9 / 16)
    left = round((screen_width - game_width) / 2)
    GAME_BOUNDS = (left, 0, left + game_width, screen_height)
    return GAME_BOUNDS

def _require_game_bounds():
    if GAME_BOUNDS is None:
        raise RuntimeError("游戏窗口边界未初始化，请先调用 window_init()")
    return GAME_BOUNDS

def ratio_to_screen(x, y):
    left, top, right, bottom = _require_game_bounds()
    screen_x = round(left + x * (right - left - 1))
    screen_y = round(top + y * (bottom - top - 1))
    return screen_x, screen_y

def screen_to_ratio(x, y):
    left, top, right, bottom = _require_game_bounds()
    ratio_x = (x - left) / (right - left - 1)
    ratio_y = (y - top) / (bottom - top - 1)
    return max(0, min(1, ratio_x)), max(0, min(1, ratio_y))
