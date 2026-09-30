import argparse
import os
import sys
from openai import OpenAI
from pathlib import Path

# Настройки проекта, загруженные из settings.env (единственный источник —
# переменные окружения ОС НЕ используются).
_SETTINGS: dict[str, str] = {}


def read_file(file_path: str) -> str:
    """Читает содержимое файла и возвращает его как строку."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        print(f"Файл {file_path} не найден.")
        return ""
    except Exception as e:
        print(f"Произошла ошибка при чтении файла: {e}")
        return ""

def write_to_file(file_path: str, content: str) -> None:
    """Записывает содержимое в файл."""
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)
        print(f"Результат успешно записан в файл {file_path}.")
    except Exception as e:
        print(f"Произошла ошибка при записи файла: {e}")

def get_file_content(file_path = None):
    if file_path:
        pass
    else:
        file_path = input("Введите путь к файлу: ")
    file_content = read_file(file_path)
    return file_content, file_path

def get_argument():

    # Парсер аргументов командной строки
    parser = argparse.ArgumentParser(description='Получение аргументов для выполнения скрипта')

    parser.add_argument('-p', '--path', type=str, help='Путь к репозиторию')
    
    parser.add_argument('-f', '--feature', type=str, help='Имя фичи/типа изменения (опционально)')
    
    parser.add_argument('-n', '--name', type=str, help='Имя фичи/типа изменения (опционально)')
    
    parser.add_argument('-ds', '--diff-start', type=str, help='Дата начала diff (опционально)')
    
    parser.add_argument('-dn', '--diff-end', type=str, help='Дата конца diff (опционально)')
    
    # Логический флаг – вывод подробного лога
    parser.add_argument('-v', '--verbose', action='store_true', help='Включить подробный вывод')
    
    # Логический флаг – «сухой прогон», без реальных действий
    parser.add_argument('--dry-run', action='store_true', help='Только проверить параметры, без выполнения')
    
    args = parser.parse_args()

    # Инициализируем переменные как None (если аргумент не передан)
    path: Optional[Path] = None
    feature: Optional[Path] = None
    name: Optional[str] = None
    diff_start: Optional[str] = None
    diff_end: Optional[str] = None

    # Выводим полученные параметры (полезно для отладки)
    if args.path:
        args.path = normalize_path(args.path)
        print(f"Используемый путь к репозиторию: {args.path}")
    if args.feature:
        args.feature = normalize_path(args.feature)
        print(f"Feature: {args.feature}")
    if args.verbose:
        print("Verbose mode включён")
    if args.dry_run:
        print("Dry‑run: действия не будут выполнены")
    if args.name:
        print(f"Имя пользователя: {args.name}")
    if args.diff_start:
        print(f"Время начала ГГГГ-ММ-ДД: {args.diff_start}")
    if args.diff_end:
        print(f"Время завершения ГГГГ-ММ-ДД: {args.diff_end}")

    return args


def normalize_path(raw_path: str) -> Path:
    """
    Приводит строку пути к абсолютному `Path` с разрешёнными символическими ссылками.
    """
    try:
        path_obj = Path(raw_path).expanduser().resolve(strict=False)
        return path_obj
    except Exception as exc:
        raise ValueError(f"Не удалось обработать путь «{raw_path}»: {exc}") from exc

def get_llm_config() -> tuple[str, str]:
    """Возвращает (base_url, model) для LLM.

    Источник — настройки settings.env (LLM_BASE_URL / LLM_MODEL), затем
    дефолты. Ожидается любой OpenAI-совместимый API — подходит и локальный
    сервер (Ollama, LM Studio, vLLM и т.п.), и облачный.
    """
    base_url = _SETTINGS.get("LLM_BASE_URL", "http://localhost:11434/v1")
    model = _SETTINGS.get("LLM_MODEL", "gpt-4o-mini")
    return base_url, model

def get_gitlab_url() -> str:
    """Возвращает базовый URL GitLab (без /api/v4).

    Источник — настройки settings.env (GITLAB_API_URL, например
    'https://gitlab.example.com'), иначе дефолт — https://gitlab.com.
    """
    return _SETTINGS.get("GITLAB_API_URL", "https://gitlab.com")


def get_docs_dir() -> str:
    """Возвращает каталог с шаблонами/чек-листами (для LLM-скриптов).

    Источник — настройки settings.env (DOCS_DIR рядом с запускаемым файлом).
    Если не задана — дефолт: каталог docs рядом с запускаемым файлом (корень
    репозитория для исходников, рядом с .exe для собранных скриптов).
    """
    docs_dir = _SETTINGS.get("DOCS_DIR", "").strip()
    if docs_dir:
        return docs_dir

    here = os.path.dirname(os.path.abspath(__file__))
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)   # рядом с .exe
    else:
        base = os.path.dirname(here)             # корень репозитория (src/..)
    return os.path.join(base, "docs")


def get_docs_file(key: str, default: str) -> str:
    """Полный путь к .md-шаблону/чек-листу в каталоге docs.

    key — ключ настроек, содержащий имя файла шаблона (напр.
    'DOCS_TEMPLATE_DESCRIPTION'); default — имя файла по умолчанию, если
    в настройках не задано. Каталог берётся из настроек (см. get_docs_dir).
    Существование не проверяется.
    """
    filename = _SETTINGS.get(key, "").strip() or default
    return os.path.join(get_docs_dir(), filename)


def get_default_variables_path() -> str:
    """Путь к JSON-файлу с дефолтными переменными пайплайна.

    Источник — настройки settings.env (DEFAULT_VARIABLES_FILE). Если не задана —
    дефолт: run_pipeline_default_variables.json в той же директории, что и
    запускаемый файл (src/ для исходников, рядом с .exe для собранных скриптов).
    """
    path = _SETTINGS.get("DEFAULT_VARIABLES_FILE", "").strip()
    if path:
        return path

    here = os.path.dirname(os.path.abspath(__file__))
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)   # рядом с .exe
    else:
        base = here                              # рядом со скриптом (src/)
    return os.path.join(base, "run_pipeline_default_variables.json")


def get_ca_bundle() -> str:
    """Путь к корневому CA для приватного GitLab (settings.env: CA_BUNDLE).

    Пустая строка, если не задан — тогда используется системный набор CA.
    """
    return _SETTINGS.get("CA_BUNDLE", "").strip()


def get_setting(key: str, default: str = "") -> str:
    """Значение настройки из settings.env (без переменных окружения ОС)."""
    return _SETTINGS.get(key, default).strip()


def _env_candidates() -> list[str]:
    """Кандидаты файла настроек (settings / settings.env) по приоритету.

    Главное правило: настройки лежат в той же директории, что и запускаемый
    файл, — рядом с .py (папка src/) при запуске из исходников и рядом с .exe
    у собранных скриптов. Дополнительно проверяются текущая рабочая директория
    и корень репозитория (обратная совместимость).
    """
    names = ("settings.env", "settings")
    here = os.path.dirname(os.path.abspath(__file__))
    dirs = [here]                       # рядом со скриптом (исходники: src/)
    if getattr(sys, "frozen", False):
        dirs.append(os.path.dirname(sys.executable))  # рядом с .exe
    dirs.append(os.getcwd())            # текущая рабочая директория
    dirs.append(os.path.dirname(here))  # корень репозитория (src/..)
    return [os.path.join(d, n) for d in dirs for n in names]


def _default_env_path() -> str:
    """Первый существующий файл настроек (settings.env / settings)."""
    for candidate in _env_candidates():
        if os.path.exists(candidate):
            return candidate
    return ""


def load_env_file(path: str = None) -> None:
    """Загружает настройки из файла в стиле .env (KEY=VALUE) в _SETTINGS.

    Единственный источник настроек — settings.env; переменные окружения ОС
    не используются. По умолчанию файл ищется по правилу «рядом с запускаемым
    файлом» (см. _env_candidates): src/settings.env для исходников, settings
    рядом с .exe для собранных скриптов. Пустой #-комментарий и пустые строки
    игнорируются. Если файла нет — no-op.
    """
    if path is None:
        path = _default_env_path()
    if not path or not os.path.exists(path):
        return
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key:
                    _SETTINGS[key] = value
    except Exception as e:
        print(f"Предупреждение: не удалось прочитать {path}: {e}")


# Загружаем настройки проекта из settings.env при импорте (если файл есть).
load_env_file()


def get_gitlab_token() -> str:
    """Токен GitLab (settings.env: GITLAB_TOKEN). Может быть пустым."""
    return _SETTINGS.get("GITLAB_TOKEN", "").strip()


def get_llm_token() -> str:
    """Токен LLM (settings.env: LLM_API_KEY). Может быть пустым —
    для локального LLM токен не обязателен."""
    return _SETTINGS.get("LLM_API_KEY", "").strip()


def new_chat(token, prompt: str, system_prompt: str, base_url: str = None, model: str = None) -> str:
    """Отправляет запрос в чат и возвращает ответ.

    Адрес и модель можно передать явно (base_url/model) либо задать в настройках
    LLM_BASE_URL / LLM_MODEL (см. get_llm_config). Для локального LLM токен
    не важен — сервер обычно игнорирует api_key.
    """
    if base_url is None or model is None:
        cfg_base_url, cfg_model = get_llm_config()
        if base_url is None:
            base_url = cfg_base_url
        if model is None:
            model = cfg_model

    cl_res = OpenAI(api_key=token, base_url=base_url)

    chat = cl_res.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model=model,
    )
    return chat.choices[0].message.content

