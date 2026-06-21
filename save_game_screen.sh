#!/usr/bin/env bash
python3 - <<'PY'
from datetime import datetime
from io import BytesIO
from pathlib import Path
import subprocess

from PIL import Image

from resize import window_init, ratio_to_screen, _adb_command


out_dir = Path("测试截图")
out_dir.mkdir(exist_ok=True)

window_init()
raw = subprocess.check_output(_adb_command("exec-out", "screencap", "-p"))
screen = Image.open(BytesIO(raw)).convert("RGB")

left, top = ratio_to_screen(0, 0)
right, bottom = ratio_to_screen(1, 1)
game = screen.crop((left, top, right + 1, bottom + 1))

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
index = 0
while True:
    suffix = f"_{index:03d}" if index else ""
    path = out_dir / f"game_{timestamp}{suffix}.png"
    if not path.exists():
        break
    index += 1

game.save(path)
print(path)
PY
