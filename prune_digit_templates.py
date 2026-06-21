from pathlib import Path
import shutil

import cv2


TEMPLATE_DIR = Path("数字模板")
BACKUP_DIR = Path("数字模板_剔除")
DIGIT_SIZE = (32, 48)
KEEP_COUNT = 10


def main():
    groups = _load_groups()
    BACKUP_DIR.mkdir(exist_ok=True)
    for digit, items in sorted(groups.items()):
        if len(items) <= KEEP_COUNT:
            print(f"{digit}: {len(items)} <= {KEEP_COUNT}, skip")
            continue
        keep = _select_templates(digit, items, groups)
        keep_paths = {path for path, _ in keep}
        removed = []
        for path, _ in items:
            if path not in keep_paths:
                target = _backup_path(path)
                shutil.move(str(path), str(target))
                removed.append(target)
        print(f"{digit}: keep {len(keep)}, move {len(removed)}")


def _load_groups():
    groups = {}
    for path in TEMPLATE_DIR.glob("*.png"):
        digit = path.stem[0]
        if not digit.isdigit():
            continue
        image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if image is None:
            continue
        image = cv2.resize(image, DIGIT_SIZE, interpolation=cv2.INTER_AREA)
        groups.setdefault(digit, []).append((path, image))
    return groups


def _select_templates(digit, items, groups):
    scores = []
    other_items = []
    for other_digit, other_templates in groups.items():
        if other_digit != digit:
            other_items.extend(other_templates)
    for path, image in items:
        other = _best_score(image, other_items)
        scores.append((other, path, image))
    scores.sort(key=lambda item: item[0])
    return [(path, image) for _, path, image in scores[:KEEP_COUNT]]


def _best_score(image, items):
    if not items:
        return 0.0
    return max(_match_score(image, other_image) for _, other_image in items)


def _match_score(image, template):
    return float(cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED).max())


def _backup_path(path):
    target = BACKUP_DIR / path.name
    if not target.exists():
        return target
    index = 1
    while True:
        target = BACKUP_DIR / f"{path.stem}_{index}{path.suffix}"
        if not target.exists():
            return target
        index += 1


if __name__ == "__main__":
    main()
