"""
Скрипт для сбора тегов из JSON-файлов (параметров Vanessa Automation) и
проверки их наличия в .feature файлах.

Параметры запуска:
    python collect_and_check_tags.py -j <json_dir> -f <features_dir> -m <mask> [-o <out>]

    -j, --json       Путь к директории с JSON файлами (обязательно)
    -f, --features   Путь к директории с .feature файлами (обязательно)
    -m, --mask       Маска для поиска JSON файлов (обязательно)
    -o, --output     Путь к файлу-отчёту (по умолчанию tags_report.txt)
    -h, --help       Показать справку

Теги берутся из JSON-параметров (поля "СписокТеговОтбор" и
"СписокТеговИсключение") у файлов, имя которых содержит <mask>, после чего
проверяется их наличие в .feature файлах.

Подробный отчёт (со сгруппированными по тегам файлами) сохраняется в файл.
В консоль выводятся только итоги: всего файлов, с тегами, без тегов.

Если параметры не заданы (или заданы не все) — они запрашиваются у
пользователя интерактивно.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

DEFAULT_OUTPUT = "tags_report.txt"

# Поля JSON-параметров VA, из которых берутся теги.
TAGS_FIELDS = ["СписокТеговОтбор", "СписокТеговИсключение"]


def find_files(directory: str, extension: str) -> list[Path]:
    """Рекурсивно найти все файлы с заданным расширением в директории."""
    files = []
    for root, _, files_list in os.walk(directory):
        for file in files_list:
            if file.lower().endswith(extension):
                files.append(Path(root) / file)
    return sorted(files)


def find_feature_files(directory: str) -> list[Path]:
    """Рекурсивно найти все .feature файлы в директории."""
    return find_files(directory, ".feature")


def find_json_files(directory: str) -> list[Path]:
    """Рекурсивно найти все .json файлы в директории."""
    return find_files(directory, ".json")


def read_tags_from_json(json_files: list[Path], mask: str) -> dict[str, dict]:
    """Собрать теги из JSON-файлов, имя которых содержит mask (без учёта регистра).

    Возвращает словарь {тег: {"sources": {имена JSON-файлов}, "exclude_only": bool}},
    где exclude_only=True означает, что тег встречается только в поле
    "СписокТеговИсключение" и не относится к тегам отбора.
    """
    mask_low = mask.lower()
    tags_meta: dict[str, dict] = {}
    for file_path in json_files:
        if mask_low not in file_path.name.lower():
            continue
        try:
            # utf-8-sig корректно читает и с BOM, и без него.
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                data = json.load(f)
        except Exception as e:
            print(f"Ошибка чтения JSON {file_path}: {e}")
            continue
        if not isinstance(data, dict):
            continue
        for field in TAGS_FIELDS:
            value = data.get(field)
            if not isinstance(value, list):
                continue
            for tag in value:
                if not tag:
                    continue
                key = str(tag).strip()
                meta = tags_meta.setdefault(key, {"sources": set(), "exclude_only": True})
                meta["sources"].add(file_path.name)
                if field == "СписокТеговОтбор":
                    meta["exclude_only"] = False
    return tags_meta


def check_tags_in_file(file_path: Path, search_tags: set) -> list[tuple[str, bool]]:
    """Проверить, какие теги из списка присутствуют в файле (без учёта регистра).

    Возвращает список кортежей (тег, точное_совпадение_регистра): тег считается
    найденным независимо от регистра, но второй элемент указывает, записан ли он
    в файле ровно так же, как в настройках.
    """
    found = []
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            content = f.read()
        for tag in search_tags:
            # Полное совпадение тега по границам слова: после @tag не должно идти
            # буквы, цифры или "_" (иначе @Metazon "поймает" @Metazon_pack).
            pattern = re.escape(f"@{tag}") + r"(?![A-Za-z0-9_])"
            if re.search(pattern, content, re.IGNORECASE):
                exact = re.search(pattern, content) is not None
                found.append((tag, exact))
    except Exception as e:
        print(f"Ошибка чтения файла {file_path}: {e}")
    return found


def _rel_path(file_path: Path, directory: str) -> Path:
    return file_path.relative_to(Path(directory).parent) if directory != "." else file_path


def build_report(search_tags: set, tag_to_files: dict, files_without_tags: list,
                 feature_files: list, directory: str, json_info: str,
                 with_tags_count: int, tags_source: dict) -> str:
    """Формирует текст подробного отчёта, сгруппированного по тегам."""
    lines = []
    lines.append("Отчёт о проверке тегов")
    lines.append("=" * 40)
    lines.append(f"Директория .feature: {directory}")
    if json_info:
        lines.append(json_info)
    lines.append(f"Всего файлов: {len(feature_files)}")
    lines.append(f"С тегами: {with_tags_count}")
    lines.append(f"Без тегов: {len(files_without_tags)}")
    lines.append("")

    def render_tags(tag_list, empty_note="(нет)"):
        rendered = []
        for tag in tag_list:
            meta = tags_source.get(tag, {})
            sources = ", ".join(sorted(meta.get("sources", [])))
            items = tag_to_files.get(tag, [])
            rendered.append(f"Тег: {tag} - {sources}")
            if items:
                rendered.append(f"  Файлов: {len(items)}")
                for file_path, exact in items:
                    line = f"  - {_rel_path(file_path, directory)}"
                    if not exact:
                        line += f"  (тег @{tag} отличается по регистру от настройки)"
                    rendered.append(line)
            else:
                rendered.append("  (не найден ни в одном файле)")
            rendered.append("")
        if not rendered:
            rendered.append(empty_note)
            rendered.append("")
        return rendered

    include_tags = [t for t in sorted(search_tags) if not tags_source.get(t, {}).get("exclude_only", True)]
    exclude_tags = [t for t in sorted(search_tags) if tags_source.get(t, {}).get("exclude_only", True)]

    lines.append("=== Тесты для запуска ===")
    lines.append("")
    lines.extend(render_tags(include_tags))

    lines.append("=== Исключены из запуска ===")
    lines.append("")
    lines.extend(render_tags(exclude_tags))

    lines.append("=== Файлы без тегов запуска ===")
    lines.append("")
    if files_without_tags:
        for f in files_without_tags:
            lines.append(f"- {_rel_path(f, directory)}")
    else:
        lines.append("(нет)")
    lines.append("")

    return "\n".join(lines)


def process_check(feature_files: list[Path], search_tags: set, directory: str,
                  output_path: str, json_info: str = "", tags_source: dict = None):
    """Проверка тегов, запись отчёта в файл; в консоль — только итоги."""
    tags_source = tags_source if tags_source is not None else {}
    if not feature_files:
        print("Не найдено ни одного .feature файла")
        sys.exit(1)

    files_with_tags = []
    files_without_tags = []
    for file_path in feature_files:
        found = check_tags_in_file(file_path, search_tags)
        if found:
            files_with_tags.append((file_path, found))
        else:
            files_without_tags.append(file_path)

    # Группировка файлов по тегам (с признаком точного совпадения регистра).
    tag_to_files = {}
    for file_path, found in files_with_tags:
        for tag, exact in found:
            tag_to_files.setdefault(tag, []).append((file_path, exact))

    with_tags = len({fp for fp, _ in files_with_tags})

    report = build_report(search_tags, tag_to_files, files_without_tags,
                          feature_files, directory, json_info, with_tags, tags_source)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report + "\n")

    # В консоль — только итоги.
    print(f"Всего файлов: {len(feature_files)}")
    print(f"С тегами: {with_tags}")
    print(f"Без тегов: {len(files_without_tags)}")
    print(f"Результат сохранён в файл: {output_path}")


def run(args: argparse.Namespace):
    """Основной режим: теги из JSON-параметров по маске."""
    if not os.path.isdir(args.json):
        print(f"Ошибка: директория JSON '{args.json}' не существует")
        sys.exit(1)
    if not os.path.isdir(args.features):
        print(f"Ошибка: директория .feature '{args.features}' не существует")
        sys.exit(1)

    json_files = find_json_files(args.json)
    json_files = [p for p in json_files if args.mask.lower() in p.name.lower()]
    if not json_files:
        print(f"В '{args.json}' не найдено JSON-файлов по маске '{args.mask}'")
        sys.exit(1)

    tags_source = read_tags_from_json(json_files, args.mask)
    if not tags_source:
        print("Теги не найдены в JSON-файлах")
        sys.exit(1)

    search_tags = set(tags_source)

    feature_files = find_feature_files(args.features)
    json_info = (f"JSON-файлы по маске '{args.mask}': "
                 f"{len(json_files)} ({', '.join(p.name for p in json_files[:5])})")
    process_check(feature_files, search_tags, args.features, args.output,
                  json_info, tags_source)


def parse_cli_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="collect_and_check_tags.py",
        description="Сбор тегов из JSON-параметров VA и проверка их в .feature файлах.")
    parser.add_argument("-j", "--json", help="Путь к директории с JSON файлами (обязательно)")
    parser.add_argument("-f", "--features", help="Путь к директории с .feature файлами (обязательно)")
    parser.add_argument("-m", "--mask", help="Маска для поиска JSON файлов (обязательно)")
    parser.add_argument("-o", "--output", default=DEFAULT_OUTPUT,
                        help=f"Путь к файлу-отчёту (по умолчанию {DEFAULT_OUTPUT})")
    return parser.parse_args()


def _ask(param_name: str, description: str) -> str:
    value = input(f"Введите {description}: ").strip()
    if not value:
        print(f"Ошибка: не указан параметр {param_name}")
        sys.exit(2)
    return value


def main():
    args = parse_cli_args()

    # Недостающие параметры запрашиваются у пользователя.
    if not args.json:
        args.json = _ask("-j", "путь к директории с JSON файлами")
    if not args.features:
        args.features = _ask("-f", "путь к директории с .feature файлами")
    if not args.mask:
        args.mask = _ask("-m", "маску для поиска JSON файлов")

    run(args)


if __name__ == "__main__":
    main()
