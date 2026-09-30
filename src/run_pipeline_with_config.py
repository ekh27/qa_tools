import os
import sys
import requests
import urllib3
import json
from urllib3.exceptions import InsecureRequestWarning
import argparse  # <-- новый импорт
from typing import Dict, Optional
from functions import get_gitlab_token, get_gitlab_url, get_default_variables_path, get_ca_bundle


# Опциональный корневой CA для приватного GitLab (settings.env: CA_BUNDLE).
# Если не задан — используется системный набор доверенных CA.
_CERT_FILE = get_ca_bundle()


_INSECURE_MODE = False
_DEBUG = False


def _request_with_verify(method: str, url: str, warn_label: str, **kwargs):
    """Выполняет HTTP-запрос с проверкой сертификата.

    Если задана CA_BUNDLE (settings.env) — используется указанный корневой CA.
    При SSL-ошибке (напр. приватный CA не в системном доверенном списке) молча
    переключаемся в «несекьюр»-режим на время работы процесса (TLS при этом
    сохраняется) и один раз коротко сообщаем о подключении без проверки
    сертификата. Подробности ошибки печатаются только с флагом --debug.
    """
    global _INSECURE_MODE
    if not _INSECURE_MODE:
        try:
            kwargs['verify'] = _CERT_FILE if _CERT_FILE else True
            return requests.request(method, url, **kwargs)
        except requests.exceptions.SSLError as e:
            _INSECURE_MODE = True
            # Подавляем InsecureRequestWarning, который urllib3 печатает при
            # verify=False — он выводится по умолчанию и не зависит от --debug.
            urllib3.disable_warnings(InsecureRequestWarning)
            if _DEBUG:
                print(f"[debug] SSL-ошибка ({warn_label}): {type(e).__name__}: {e}")
                print("  CA не распознан; подключаюсь без проверки сертификата.")
    print("Подключение к GitLab без проверки сертификата.")
    kwargs['verify'] = False
    return requests.request(method, url, **kwargs)

# --------------------------- Аргумент‑парсер ---------------------------
def parse_cli_args() -> argparse.Namespace:
    """
    Парсит аргументы командной строки.
    Поддерживается параметр:
        -cf, --config  : путь к JSON‑файлу конфигурации
    """
    parser = argparse.ArgumentParser(
        description="Запуск GitLab pipeline с конфигурацией из JSON‑файла."
    )
    parser.add_argument(
        "-cf",
        "--config",
        dest="config_path",
        type=str,
        help="Путь к конфигурационному JSON‑файлу",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Показывать подробности ошибок подключения/SSL",
    )
    return parser.parse_args()

# --------------------------------------------------------------------

def load_config(file_path: str) -> Dict:
    """
    Загружает конфигурацию из JSON файла.

    :param file_path: Путь к файлу конфигурации
    :return: Словарь с настройками
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)


def check_gitlab_connection() -> bool:
    """
    Проверяет соединение с GitLab API.
    Если соединение не установлено, завершает программу.
    """
    private_token = get_gitlab_token()
    if not private_token:
        print("❌ Токен GitLab не найден. Проверьте GITLAB_TOKEN в settings.env.")
        sys.exit(1)

    url = f"{get_gitlab_url()}/api/v4/version"
    headers = {"PRIVATE-TOKEN": private_token}

    if _DEBUG:
        print(f"[debug] CA_BUNDLE: {_CERT_FILE}")
    try:
        response = _request_with_verify('GET', url, warn_label='GitLab',
                                        headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        print(f"✅ GitLab API доступен (версия: {data.get('version', 'неизвестно')})")
        return True
    except requests.exceptions.SSLError as e:
        print(f"❌ SSL-ошибка (проблема сертификата): {type(e).__name__}: {e}")
        sys.exit(1)
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Ошибка соединения: {type(e).__name__}: {e}")
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"❌ Ошибка авторизации GitLab. Проверьте GITLAB_TOKEN в settings.env. ({e})")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Ошибка при проверке соединения с GitLab: {type(e).__name__}: {e}")
        sys.exit(1)


def run_gitlab_pipeline(
    project_id: int,
    ref: str = 'main',  # Ветка, из которой нужно запустить пайплайн
    variables: Dict[str, str] = None  # Переменные окружения, если нужны
) -> Optional[str]:
    """
    Запускает пайплайн в GitLab через API.

    :param project_id: ID проекта в GitLab
    :param ref: Ветка, из которой нужно запустить пайплайн (по умолчанию 'main')
    :param variables: Словарь переменных окружения для пайплайна
    :return: URL пайплайна или None в случае ошибки
    """

    private_token = get_gitlab_token()

    # Загрузка переменных окружения по умолчанию из файла (путь — из настроек)
    default_variables = load_config(get_default_variables_path())
    
    # Объединение переменных по умолчанию с переданными переменными
    if variables:
        combined_variables = {**default_variables, **variables}
    else:
        combined_variables = default_variables

    # Обработка PATH_TS_FOLDER: подставляем префикс репозитория VA перед отправкой.
    # Префикс берётся из переменной PREFIX_REPO (по умолчанию "/repo_va/"); значение
    # PATH_TS_FOLDER считается относительным путём от корня репозитория VA.
    path_ts_folder = combined_variables.get('PATH_TS_FOLDER')
    if path_ts_folder:
        prefix_repo = (combined_variables.get('PREFIX_REPO', '') or '').strip()
        path_ts_folder = path_ts_folder.replace('\\', '/')
        combined_variables['PATH_TS_FOLDER'] = prefix_repo + path_ts_folder

    url = f"{get_gitlab_url()}/api/v4/projects/{project_id}/pipeline"

    headers = {
        "PRIVATE-TOKEN": private_token
    }

    data = {
        "ref": ref
    }

    # Преобразуем словарь переменных в список словарей
    formatted_variables = [{"key": key, "value": value} for key, value in combined_variables.items()]
    data["variables"] = formatted_variables

    try:
        response = _request_with_verify('POST', url, warn_label='GitLab pipeline',
                                        headers=headers, json=data)
        response.raise_for_status()  # Проверяем успешность запроса

        pipeline_info = response.json()
        web_url = pipeline_info.get('web_url')
        print("Пайплайн успешно запущен!")
        print(web_url)
        return web_url

    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 400:
            print(f"HTTP ошибка 400: Bad Request. Детали: {response.text}")
        else:
            print(f"HTTP ошибка: {http_err}")
    except Exception as err:
        print(f"Произошла ошибка: {err}")

    return None

if __name__ == "__main__":
    try:
        args = parse_cli_args()
        _DEBUG = args.debug

        # Проверка соединения с GitLab перед выполнением
        check_gitlab_connection()

        current_dir = os.getcwd()

        # Если путь к конфигу передан через CLI, используем его,
        # иначе запрашиваем у пользователя (поведение старой версии).
        if args.config_path:
            config_file_path = os.path.abspath(args.config_path)
        else:
            user_input = input("Введите путь к конфигурационному файлу: ").strip()
            config_file_path = os.path.join(current_dir, user_input)

        # Загрузка конфигурации из файла
        variables_config = load_config(config_file_path)

        path_ts_folder = variables_config.get('PATH_TS_FOLDER')
        user_path_ts_folder = input(f"Введите путь к файлу или директории для запуска (по умолчанию '{path_ts_folder}'): ").strip()
        if user_path_ts_folder:
            # Пользователь вводит относительный путь; префикс PREFIX_REPO
            # подставится к PATH_TS_FOLDER при отправке (в run_gitlab_pipeline).
            variables_config['PATH_TS_FOLDER'] = user_path_ts_folder.replace('\\', '/')

        # Извлечение параметров из конфигурации
        project_id = variables_config.get('project_id')
        ref = variables_config.get('ref')
        variables = variables_config

        # Вывод значений project_id и variables
        print(f"project_id: {project_id}")

        # Запрос подтверждения запуска пайплайна
        print(f"data: {variables}, {project_id}, {ref}")
        confirmation = input("Запустить пайплайн? (y/n): ")
        if confirmation.lower() == 'y':
            run_gitlab_pipeline(project_id, ref, variables)
        else:
            print("Пайплайн не запущен.")
    except Exception as e:
        print(f"Произошла ошибка: {e}")
    # finally:
    #     input("Нажмите Enter для завершения...")
