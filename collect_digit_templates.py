from pathlib import Path
import shutil

import cv2

import attr_ocr
from data import ranges
from resize import window_init


TEMPLATE_DIR = Path("数字模板")
BACKUP_DIR = Path("数字模板_旧命名")
SLOTS_PER_DIGIT = 10
LOW_SCORE_NOTICE = 0.75
MIN_SIM_SQUARE_IMPROVEMENT = 0.01


def main():
    TEMPLATE_DIR.mkdir(exist_ok=True)
    _normalize_fixed_slots()

    window_init()
    screenshot = attr_ocr._adb_screenshot()
    templates = _load_slot_templates()
    saved = []
    replaced = []
    kept = []
    low_score = []

    for range_index, bbox in enumerate(ranges):
        crop = attr_ocr._crop_ratio(screenshot, bbox)
        mask = attr_ocr._digit_mask(crop)
        boxes = attr_ocr._digit_boxes(mask)
        for digit_index, box in enumerate(boxes):
            digit_img = attr_ocr._crop_digit(mask, box)
            digit, score = _best_match(digit_img, templates)
            if digit is None:
                low_score.append((None, range_index, digit_index, box, digit, score))
                continue

            action = _store_if_improves(digit, digit_img, templates)
            if action[0] == "saved":
                saved.append((action[1], range_index, digit_index, box, digit, score))
            elif action[0] == "replaced":
                replaced.append((action[1], action[2], range_index, digit_index, box, digit, score))
            else:
                kept.append((range_index, digit_index, box, digit, score, action[1]))

            if score < LOW_SCORE_NOTICE:
                low_score.append((action[1] if len(action) > 1 else None, range_index, digit_index, box, digit, score))

    _print_result("saved", saved)
    _print_replaced(replaced)
    _print_kept(kept)
    _print_low_score(low_score)


def _normalize_fixed_slots():
    groups = _load_all_templates()
    BACKUP_DIR.mkdir(exist_ok=True)
    for digit, items in groups.items():
        selected = _select_most_distinct(digit, items, groups, SLOTS_PER_DIGIT)
        if selected and len(selected) < SLOTS_PER_DIGIT:
            index = 0
            while len(selected) < SLOTS_PER_DIGIT:
                selected.append(selected[index % len(selected)])
                index += 1
        for path, _ in items:
            _move_unique(path, BACKUP_DIR / path.name)

        for index, (_, image) in enumerate(selected):
            target = TEMPLATE_DIR / _slot_name(digit, index)
            cv2.imwrite(str(target), image)


def _load_all_templates():
    groups = {str(i): [] for i in range(10)}
    for path in TEMPLATE_DIR.glob("*.png"):
        digit = path.stem[0]
        if not digit.isdigit():
            continue
        image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if image is None:
            continue
        image = cv2.resize(image, attr_ocr.DIGIT_SIZE, interpolation=cv2.INTER_AREA)
        groups[digit].append((path, image))
    return groups


def _load_slot_templates():
    templates = {str(i): [] for i in range(10)}
    for digit in templates:
        for index in range(SLOTS_PER_DIGIT):
            path = TEMPLATE_DIR / _slot_name(digit, index)
            if not path.exists():
                continue
            image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
            if image is not None:
                image = cv2.resize(image, attr_ocr.DIGIT_SIZE, interpolation=cv2.INTER_AREA)
                templates[digit].append((path, image))
    return templates


def _store_if_improves(digit, image, templates):
    items = templates.setdefault(digit, [])
    if len(items) < SLOTS_PER_DIGIT:
        path = TEMPLATE_DIR / _slot_name(digit, len(items))
        cv2.imwrite(str(path), image)
        items.append((path, image))
        return ("saved", path)

    current_scores = [(path, _sim_square_sum(digit, item_image, templates)) for path, item_image in items]
    worst_path, worst_score = max(current_scores, key=lambda item: item[1])
    new_score = _sim_square_sum(digit, image, templates)
    if new_score <= worst_score - MIN_SIM_SQUARE_IMPROVEMENT:
        cv2.imwrite(str(worst_path), image)
        templates[digit] = [(path, image if path == worst_path else item_image) for path, item_image in items]
        return ("replaced", worst_path, f"{worst_score:.3f}->{new_score:.3f}")
    return ("kept", f"new_sim_square_sum={new_score:.3f} worst_sim_square_sum={worst_score:.3f}")


def _best_match(digit_img, templates):
    best_digit = None
    best_score = -1.0
    for value, digit_templates in templates.items():
        for _, template in digit_templates:
            score = cv2.matchTemplate(digit_img, template, cv2.TM_CCOEFF_NORMED).max()
            if score > best_score:
                best_digit = value
                best_score = float(score)
    return best_digit, best_score


def _select_most_distinct(digit, items, groups, count):
    if len(items) <= count:
        return items
    scores = [(path, image, _sim_square_sum_from_groups(digit, image, groups)) for path, image in items]
    scores.sort(key=lambda item: item[2])
    return [(path, image) for path, image, _ in scores[:count]]


def _sim_square_sum(digit, image, templates):
    other_items = []
    for other_digit, items in templates.items():
        if other_digit != digit:
            other_items.extend(items)
    return _sum_similarity_square(image, other_items)


def _sim_square_sum_from_groups(digit, image, groups):
    other_items = []
    for other_digit, items in groups.items():
        if other_digit != digit:
            other_items.extend(items)
    return _sum_similarity_square(image, other_items)


def _sum_similarity_square(image, items):
    if not items:
        return 0.0
    return sum(float(cv2.matchTemplate(image, other, cv2.TM_CCOEFF_NORMED).max()) ** 2 for _, other in items)


def _slot_name(digit, index):
    return f"{digit}_{index}.png"


def _move_unique(source, target):
    if not source.exists():
        return
    target.parent.mkdir(exist_ok=True)
    if not target.exists():
        shutil.move(str(source), str(target))
        return
    index = 1
    while True:
        candidate = target.with_name(f"{target.stem}_{index}{target.suffix}")
        if not candidate.exists():
            shutil.move(str(source), str(candidate))
            return
        index += 1


def _print_result(title, rows):
    print(title)
    for path, range_index, digit_index, box, digit, score in rows:
        print(f"{path} range={range_index} digit={digit_index} box={box} as={digit} score={score:.3f}")


def _print_replaced(rows):
    print("replaced")
    for path, change, range_index, digit_index, box, digit, score in rows:
        print(
            f"{path} range={range_index} digit={digit_index} box={box} "
            f"as={digit} score={score:.3f} sim_square_sum={change}"
        )


def _print_kept(rows):
    print("kept")
    for range_index, digit_index, box, digit, score, reason in rows:
        print(f"range={range_index} digit={digit_index} box={box} as={digit} score={score:.3f} {reason}")


def _print_low_score(rows):
    print("low_score")
    for path, range_index, digit_index, box, digit, score in rows:
        print(f"{path} range={range_index} digit={digit_index} box={box} judged={digit} score={score:.3f}")


if __name__ == "__main__":
    main()
