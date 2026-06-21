#!/usr/bin/env bash
python3 - <<'PY'
from resize import window_init
from recognize import get_attr

window_init()
print("attr", get_attr(1))
PY
