import random
import struct
import subprocess
import time
from resize import _adb_command, _get_screen_size, ratio_to_screen, screen_to_ratio

CLICK_MOVE_LIMIT = 10

def click(place, t):
    x = random.uniform(place[0], place[2])
    y = random.uniform(place[1], place[3])
    screen_x, screen_y = ratio_to_screen(x, y)
    # print(f"点击位置: ({x}, {y}) -> ({screen_x}, {screen_y})")
    subprocess.run(_adb_command("shell", "input", "tap", str(screen_x), str(screen_y)), check=True)
    time.sleep(t)

def listen_clicks():
    screen_width, screen_height = _get_screen_size()
    _listen_waydroid_clicks(screen_width, screen_height)

def _screen_coordinate(raw_x, raw_y, screen_width, screen_height):
    if 0 <= raw_x < screen_width and 0 <= raw_y < screen_height:
        return raw_x, raw_y

    fixed_x = raw_x / 256
    fixed_y = raw_y / 256
    if 0 <= fixed_x < screen_width and 0 <= fixed_y < screen_height:
        return round(fixed_x), round(fixed_y)

    return raw_x, raw_y

def _listen_waydroid_clicks(screen_width, screen_height):
    device = "/dev/input/wl_pointer_events"
    raw_x = None
    raw_y = None
    touching = False
    start_x = None
    start_y = None
    max_move = 0
    pending_click = False

    process = subprocess.Popen(
        _adb_command("shell", "cat", device),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    try:
        while True:
            data = process.stdout.read(24)
            if not data or len(data) < 24:
                break

            _, _, event_type, code, value = struct.unpack("<qqHHi", data)

            if event_type == 3 and code in (0, 53):
                raw_x = value
            elif event_type == 3 and code in (1, 54):
                raw_y = value
            elif event_type == 1 and code in (272, 330):
                is_down = value != 0
                if is_down and not touching:
                    start_x = raw_x
                    start_y = raw_y
                    max_move = 0
                elif not is_down and touching:
                    pending_click = True
                touching = is_down
            elif event_type == 3 and code == 57:
                is_down = value != -1
                if is_down and not touching:
                    start_x = raw_x
                    start_y = raw_y
                    max_move = 0
                elif not is_down and touching:
                    pending_click = True
                touching = is_down

            if touching and raw_x is not None and raw_y is not None and start_x is not None and start_y is not None:
                max_move = max(max_move, abs(raw_x - start_x), abs(raw_y - start_y))
            elif touching and raw_x is not None and raw_y is not None:
                start_x = raw_x
                start_y = raw_y
            elif event_type == 0 and code == 0 and pending_click and raw_x is not None and raw_y is not None:
                if max_move <= CLICK_MOVE_LIMIT:
                    x, y = _screen_coordinate(raw_x, raw_y, screen_width, screen_height)
                    ratio_x, ratio_y = screen_to_ratio(x, y)
                    print(f"{ratio_x:.6f} {ratio_y:.6f}", flush=True)
                raw_x = None
                raw_y = None
                start_x = None
                start_y = None
                max_move = 0
                pending_click = False
    finally:
        process.terminate()
