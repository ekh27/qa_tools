import os
import re
import sys
import requests
import urllib3
from urllib3.exceptions import InsecureRequestWarning

from functions import (
    get_gitlab_url,
    get_gitlab_token,
    get_llm_token,
    get_ca_bundle,
    get_setting,
    new_chat,
    write_to_file,
)


# Опциональный корневой CA для приватного GitLab (settings.env: CA_BUNDLE).
_CERT_FILE = get_ca_bundle()


def _request_json(url: str, headers: dict) -> list:
    """GET с учётом CA_BUNDLE (при SSL-ошибке с приватным CA — без проверки)."""
    urllib3.disable_warnings(InsecureRequestWarning)
    try:
        resp = requests.get(url, headers=headers,
                            verify=_CERT_FILE if _CERT_FILE else True, timeout=30)
        resp.raise_for_status()
    except requests.exceptions.SSLError:
        print("Подключение к GitLab без проверки сертификата (CA не распознан).")
        resp = requests.get(url, headers=headers, verify=False, timeout=30)
        resp.raise_for_status()
    return resp.json()


def extract_mr_number() -> int:
    """Извлекает номер Merge Request из URL."""
    url = input("Введите URL MR: ").strip()
    match = re.search(r'/merge_requests/(\d+)', url)
    if match:
        mr_number = int(match.group(1))
        print(f"Номер Merge Request: {mr_number}")
        return mr_number
    print("Merge Request не найден")
    return -1


def get_merge_request_diff(project_id: int, mr_iid: int, private_token: str):
    """
    Возвращает (diff_content, feature_files_list) для указанного MR.

    Базовый URL берётся из настроек (GITLAB_API_URL), а не захардкожен.
    """
    base = get_gitlab_url()
    url = f"{base}/api/v4/projects/{project_id}/merge_requests/{mr_iid}/diffs"
    headers = {"PRIVATE-TOKEN": private_token}

    try:
        diffs = _request_json(url, headers)
    except requests.exceptions.HTTPError as err:
        print(f"HTTP ошибка: {err}")
        return None, None
    except Exception as err:
        print(f"Произошла ошибка: {err}")
        return None, None

    # Объединяем все части diff в одну строку.
    diff_content = "\n".join(d.get("diff", "") for d in diffs)

    # Собираем имена всех файлов, затронутых в изменениях.
    all_files = {d.get("new_path") or d.get("old_path") for d in diffs}
    all_files.discard(None)
    feature_files = {os.path.basename(f) for f in all_files if f.endswith(".feature")}

    diff_content += "\n\nЗатронутые файлы:\n" + "\n".join(sorted(all_files))
    return diff_content, "\n".join(sorted(feature_files))


if __name__ == "__main__":
    # project_id — из настроек (GITLAB_PROJECT_ID), иначе запрашивается.
    project_id = int(get_setting("GITLAB_PROJECT_ID") or 0)
    if not project_id:
        try:
            project_id = int(input("Введите ID проекта GitLab: ").strip())
        except ValueError:
            sys.exit("[ERROR] Неверный ID проекта.")

    mr_iid = extract_mr_number()
    if mr_iid <= 0:
        sys.exit("[ERROR] URL MR не распознан.")

    private_token = get_gitlab_token()
    if not private_token:
        sys.exit("[ERROR] Не найден токен GitLab (GITLAB_TOKEN в settings.env).")

    current_directory = os.getcwd()
    diff_content, file_list_str = get_merge_request_diff(project_id, mr_iid, private_token)
    if not diff_content:
        sys.exit("[ERROR] Diff не получен.")

    print("Diff для Merge Request получен")
    write_to_file(os.path.join(current_directory, "diffMergeRequest.txt"), diff_content)
    write_to_file(os.path.join(current_directory, "diffMergeRequest_name_files.txt"), file_list_str)

    system_prompt = (
        "Ты ассистент по ревью Merge Request. "
        "Ты получаешь на входе DIFF с GITLAB. "
        "Не используй таблицы и Markdown. "
        "При перечислении элементов используй списки."
    )
    prompt = (
        "Посчитай количество изменённых файлов, выведи их имена списком, если указаны.\n"
        "Кратко опиши предоставленный diff.\n\n"
        "Отдельно проверь заме.\n\n"
        f"{diff_content}"
    )

    report = new_chat(get_llm_token(), prompt, system_prompt)
    write_to_file(os.path.join(current_directory, "MergeRequest.txt"), report)
