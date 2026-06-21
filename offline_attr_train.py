from pathlib import Path
import shutil
from concurrent.futures import ThreadPoolExecutor
import os

import cv2
import numpy as np
from PIL import Image

import attr_ocr
from data import ranges


IMAGE_DIR = Path("训练截图")
TEMPLATE_DIR = Path("离线数字模板")
TEMPLATES_PER_DIGIT = 10


def train_from_pngs(image_dir=IMAGE_DIR, template_dir=TEMPLATE_DIR):
    image_dir = Path(image_dir)
    template_dir = Path(template_dir)
    samples = _collect_samples(image_dir)
    selected = _select_templates(samples, TEMPLATES_PER_DIGIT)
    _write_templates(selected, template_dir)
    templates = _templates_from_samples(selected)
    errors = _verify_images(image_dir, templates)
    if errors:
        for path, expected, actual in errors:
            print(f"FAIL {path.name}: expected={expected} actual={actual}")
        raise ValueError(f"离线识别失败: {len(errors)} 张")
    print(f"OK images={len(_image_paths(image_dir))} digit_samples={len(samples)} templates={len(selected)}")
    print(f"templates={template_dir}")


def recognize_local_png(path, template_dir=TEMPLATE_DIR):
    templates = _load_template_dir(Path(template_dir))
    return _recognize_image(Image.open(path).convert("RGB"), templates)


def _collect_samples(image_dir):
    samples = []
    errors = []
    for path in _image_paths(image_dir):
        expected = _expected_from_name(path)
        image = Image.open(path).convert("RGB")
        for range_index, text in enumerate(expected):
            crop = _crop_ratio_local(image, ranges[range_index])
            mask = attr_ocr._digit_mask(crop)
            boxes = attr_ocr._digit_boxes(mask)
            if len(boxes) != len(text):
                errors.append((path.name, range_index, text, len(boxes), boxes))
                continue
            for digit_index, (digit, box) in enumerate(zip(text, boxes)):
                digit_image = attr_ocr._crop_digit(mask, box)
                samples.append((digit, path.stem, range_index, digit_index, digit_image))
    if errors:
        for error in errors:
            print("SEGMENT_FAIL", error)
        raise ValueError(f"数字分割失败: {len(errors)} 个区域")
    return samples


def _verify_images(image_dir, templates):
    errors = []
    for path in _image_paths(image_dir):
        expected = [int(value) for value in _expected_from_name(path)]
        actual = _recognize_image(Image.open(path).convert("RGB"), templates)
        if actual != expected:
            errors.append((path, expected, actual))
    return errors


def _select_templates(samples, count):
    matrix = _build_similarity_matrix(samples)
    labels = [sample[0] for sample in samples]
    by_digit = {str(index): [] for index in range(10)}
    for index, sample in enumerate(samples):
        by_digit[sample[0]].append(index)

    selected = []
    for digit, candidate_indices in by_digit.items():
        chosen_indices = _select_digit_templates(digit, candidate_indices, labels, matrix, count)
        chosen = [samples[index] for index in chosen_indices]
        if len(chosen) != count:
            raise ValueError(f"数字 {digit} 只选出 {len(chosen)} 个模板")
        selected.extend(chosen)
        print(f"select {digit}: {len(chosen)}")
    return selected


def _build_similarity_matrix(samples):
    images = [sample[4] for sample in samples]
    size = len(images)
    matrix = np.eye(size, dtype=np.float32)

    def compute_row(row):
        values = []
        image = images[row]
        for col in range(row + 1, size):
            score = cv2.matchTemplate(image, images[col], cv2.TM_CCOEFF_NORMED).max()
            values.append((col, float(score)))
        return row, values

    workers = min(os.cpu_count() or 1, 32)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for row, values in executor.map(compute_row, range(size)):
            for col, score in values:
                matrix[row, col] = score
                matrix[col, row] = score
    return matrix


def _select_digit_templates(digit, candidates, labels, matrix, count):
    selected = []
    remaining = candidates[:]
    while remaining and len(selected) < count:
        best = None
        for candidate in remaining:
            trial = selected + [candidate]
            score = _selection_score(digit, trial, labels, matrix)
            if best is None or score < best[0]:
                best = (score, candidate)
        selected.append(best[1])
        remaining.remove(best[1])
    return selected


def _selection_score(digit, selected, labels, matrix):
    errors = 0
    confidence_loss = 0.0
    other_indices = [index for index, label in enumerate(labels) if label != digit]
    for sample_index, sample_digit in enumerate(labels):
        own = _best_matrix_score(matrix, sample_index, selected)
        other = _best_matrix_score(matrix, sample_index, other_indices)
        if sample_digit == digit:
            if own <= other:
                errors += 1
                confidence_loss += other - own
            else:
                confidence_loss += 1.0 - own
        else:
            if own >= other:
                errors += 1
                confidence_loss += own - other
    return errors, confidence_loss


def _best_matrix_score(matrix, sample_index, template_indices):
    if not template_indices:
        return -1.0
    return float(matrix[sample_index, template_indices].max())


def _recognize_image(image, templates):
    values = []
    for bbox in ranges:
        crop = _crop_ratio_local(image, bbox)
        text = attr_ocr._read_digits(crop, templates)
        values.append(int(text))
    return values


def _write_templates(samples, template_dir):
    if template_dir.exists():
        shutil.rmtree(template_dir)
    template_dir.mkdir()
    counters = {str(index): 0 for index in range(10)}
    for digit, stem, range_index, digit_index, image in samples:
        index = counters[digit]
        counters[digit] += 1
        path = template_dir / f"{digit}_{index:04d}_{stem}_{range_index}_{digit_index}.png"
        cv2.imwrite(str(path), image)


def _templates_from_samples(samples):
    templates = {}
    for digit, stem, range_index, digit_index, image in samples:
        name = f"{digit}_{stem}_{range_index}_{digit_index}"
        templates.setdefault(digit, []).append((Path(name), image))
    return templates


def _load_template_dir(template_dir):
    templates = {}
    for path in template_dir.glob("*.png"):
        digit = path.stem[0]
        if not digit.isdigit():
            continue
        image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if image is not None:
            image = cv2.resize(image, attr_ocr.DIGIT_SIZE, interpolation=cv2.INTER_AREA)
            templates.setdefault(digit, []).append((path, image))
    if not templates:
        raise ValueError(f"没有离线模板: {template_dir}")
    return templates


def _crop_ratio_local(image, bbox):
    width, height = image.size
    x1 = round(bbox[0] * width)
    y1 = round(bbox[1] * height)
    x2 = round(bbox[2] * width)
    y2 = round(bbox[3] * height)
    left, right = sorted((x1, x2))
    top, bottom = sorted((y1, y2))
    return image.crop((left, top, right + 1, bottom + 1))


def _expected_from_name(path):
    parts = path.stem.split("_")
    if len(parts) != len(ranges) or not all(part.isdigit() for part in parts):
        raise ValueError(f"文件名不符合 力_魔_技_速_体_甲_抗_分.png: {path.name}")
    return parts


def _image_paths(image_dir):
    return sorted(Path(image_dir).glob("*.png"))


if __name__ == "__main__":
    train_from_pngs()
