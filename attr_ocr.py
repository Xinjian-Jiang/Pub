from io import BytesIO
from pathlib import Path
import subprocess

import cv2
import numpy as np
from PIL import Image

from data import model_score_jobs, ranges, score_coefficients
from resize import _adb_command, ratio_to_screen


TEMPLATE_DIR = Path("离线数字模板")
DIGIT_SIZE = (32, 48)
THRESHOLD = 45
MIN_MATCH_SCORE = 0.55
MIN_CONFIDENCE = 0.10


def get_attr(model=None):
    screenshot = _adb_screenshot()
    templates = _load_templates()
    results = []
    for bbox in ranges:
        crop = _crop_ratio(screenshot, bbox)
        text = _read_digits(crop, templates)
        if not text:
            raise ValueError(f"无法识别数字区域: {bbox}")
        results.append(int(text))
    if model is not None:
        _validate_score(model, results)
    return results


def _adb_screenshot():
    raw = subprocess.check_output(_adb_command("exec-out", "screencap", "-p"))
    return Image.open(BytesIO(raw)).convert("RGB")


def _crop_ratio(screenshot, bbox):
    x1, y1 = ratio_to_screen(bbox[0], bbox[1])
    x2, y2 = ratio_to_screen(bbox[2], bbox[3])
    left, right = sorted((x1, x2))
    top, bottom = sorted((y1, y2))
    return screenshot.crop((left, top, right + 1, bottom + 1))


def _read_digits(image, templates):
    mask = _digit_mask(image)
    boxes = _digit_boxes(mask)
    digits = []
    for digit_index, box in enumerate(boxes):
        digit_image = _crop_digit(mask, box)
        digit = _match_digit(digit_image, templates)
        if digit is not None:
            digits.append(digit)
    return "".join(digits)


def _digit_mask(image):
    gray = np.array(image.convert("L"))
    _, mask = cv2.threshold(gray, THRESHOLD, 255, cv2.THRESH_BINARY)
    kernel = np.ones((2, 2), np.uint8)
    return cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)


def _digit_boxes(mask):
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if h >= 8 and w >= 3:
            boxes.extend(_split_wide_box(mask, (x, y, w, h)))
    return sorted(boxes, key=lambda box: box[0])


def _split_wide_box(mask, box):
    x, y, w, h = box
    if w <= h * 0.9:
        return [box]
    expected = round(w / 16)
    if expected > 1:
        return _split_box_evenly(mask, box, expected)

    region = mask[y:y + h, x:x + w]
    columns = np.count_nonzero(region, axis=0)
    blank_columns = columns <= max(1, int(h * 0.08))
    splits = []
    start = None
    for index, is_blank in enumerate(blank_columns):
        if is_blank and start is None:
            start = index
        elif not is_blank and start is not None:
            if index - start >= 2:
                splits.append((start + index) // 2)
            start = None
    if start is not None and w - start >= 2:
        splits.append((start + w) // 2)

    parts = []
    left = 0
    for split in splits:
        if split - left >= 3:
            parts.append((left, split))
        left = split
    if w - left >= 3:
        parts.append((left, w))

    result = []
    for left, right in parts:
        sub = region[:, left:right]
        sub_contours, _ = cv2.findContours(sub, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in sub_contours:
            sx, sy, sw, sh = cv2.boundingRect(contour)
            if sh >= 8 and sw >= 3:
                result.append((x + left + sx, y + sy, sw, sh))
    return result or [box]


def _split_box_evenly(mask, box, count):
    x, y, w, h = box
    result = []
    for index in range(count):
        left = round(w * index / count)
        right = round(w * (index + 1) / count)
        sub = mask[y:y + h, x + left:x + right]
        contours, _ = cv2.findContours(sub, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            continue
        sx, sy, sw, sh = cv2.boundingRect(np.vstack(contours))
        if sh >= 8 and sw >= 3:
            result.append((x + left + sx, y + sy, sw, sh))
    return result or [box]


def _crop_digit(mask, box):
    x, y, w, h = box
    pad = 2
    left = max(0, x - pad)
    top = max(0, y - pad)
    right = min(mask.shape[1], x + w + pad)
    bottom = min(mask.shape[0], y + h + pad)
    digit = mask[top:bottom, left:right]
    return cv2.resize(digit, DIGIT_SIZE, interpolation=cv2.INTER_AREA)


def _load_templates():
    templates = {}
    for path in TEMPLATE_DIR.glob("*.png"):
        digit = path.stem[0]
        if digit.isdigit():
            image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
            if image is not None:
                templates.setdefault(digit, []).append(
                    (path, cv2.resize(image, DIGIT_SIZE, interpolation=cv2.INTER_AREA))
                )
    if not templates:
        raise ValueError(f"没有找到数字模板: {TEMPLATE_DIR}")
    return templates


def _match_digit(digit, templates):
    best_digit = None
    best_score = -1.0
    best_other_digit = None
    best_other_score = -1.0
    for value, digit_templates in templates.items():
        digit_score = max(
            float(cv2.matchTemplate(digit, template, cv2.TM_CCOEFF_NORMED).max())
            for _, template in digit_templates
        )
        if digit_score > best_score:
            best_other_digit = best_digit
            best_other_score = best_score
            best_digit = value
            best_score = digit_score
        elif digit_score > best_other_score:
            best_other_digit = value
            best_other_score = digit_score
    if best_digit is None:
        raise ValueError("无法匹配数字")
    confidence = (best_score - best_other_score) / best_score if best_score else -1.0
    if best_score < MIN_MATCH_SCORE:
        return None
    if confidence < MIN_CONFIDENCE:
        return None
    return best_digit


def _validate_score(model, values):
    if len(values) != 8:
        raise ValueError(f"属性数量异常: {values}")
    job = model_score_jobs.get(model)
    if job is None:
        raise ValueError(f"没有模型评分职业映射: {model}")
    coefficients = score_coefficients[job]
    calculated = sum(value * coefficient for value, coefficient in zip(values[:7], coefficients))
    shown = values[7]
    if 300 <= shown <= 1050 or shown > 2000:
        raise ValueError(f"评分落入异常区间: model={model} job={job} score={shown} attrs={values[:7]}")
    if int(calculated) != shown:
        raise ValueError(
            f"评分校验失败: model={model} job={job} attrs={values[:7]} "
            f"calculated={calculated:.3f} int={int(calculated)} shown={shown}"
        )
