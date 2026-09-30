#!/usr/bin/env python3
"""Проверка соединения с GitLab API.

При запуске проверяет доступность GitLab API.
Базовый URL — из env GITLAB_API_URL (см. functions.get_gitlab_url).
Токен берётся через functions.get_gitlab_token() (env GITLAB_TOKEN →
settings). Если токен невалиден, запрашивает новый перед выполнением
запросов.
"""

import os
import sys
import json
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from functions import get_gitlab_token, get_gitlab_url

GITLAB_URL = get_gitlab_url()
API_BASE = f"{GITLAB_URL}/api/v4"


def get_token() -> str | None:
    """Получить токен GitLab (env GITLAB_TOKEN → settings)."""
    token = get_gitlab_token()
    return token or None


def prompt_token() -> str:
    """Запросить токен у пользователя."""
    print("\n🔑 Токен GitLab не найден или невалиден.")
    print("   Его можно получить здесь:")
    print(f"   {GITLAB_URL}/-/user_settings/personal_access_tokens")
    print()
    token = input("   Введите токен: ").strip()
    if not token:
        print("❌ Токен не введён. Завершение.")
        sys.exit(1)
    return token


def check_api(token: str | None) -> bool:
    """Проверить доступность GitLab API. Возвращает True, если всё ок."""
    headers = {
        "User-Agent": "check-gitlab-api/1.0",
    }
    if token:
        headers["PRIVATE-TOKEN"] = token

    print(f"\n🌐 Проверка соединения с {GITLAB_URL}...")
    try:
        req = Request(f"{API_BASE}/version", headers=headers)
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            print(f"   ✅ GitLab доступен. Версия: {data.get('version', 'неизвестно')}")
            return True
    except HTTPError as e:
        if e.code == 401:
            print(f"   ❌ Ошибка авторизации (401). Токен недействителен.")
            return False
        print(f"   ❌ HTTP ошибка {e.code}: {e.reason}")
        return False
    except URLError as e:
        print(f"   ❌ Не удалось подключиться: {e.reason}")
        return False
    except (OSError, json.JSONDecodeError) as e:
        print(f"   ❌ Ошибка: {e}")
        return False


def main() -> None:
    print(f"{'='*50}")
    print(f"  🔍 Проверка подключения к GitLab API")
    print(f"  {GITLAB_URL}")
    print(f"{'='*50}")

    token = get_token()

    # Пробуем без токена (публичная информация)
    if not token:
        print("\n📭 Токен не найден.")
        print("   Пробуем анонимный запрос (может быть ограничен)...")
        if check_api(None):
            print("\n✅ Анонимный доступ работает. Токен не требуется.")
            return
        print("\n❌ Анонимный доступ не работает — запрашиваем токен.")
        token = prompt_token()
    else:
        print(f"\n🔑 Токен найден (первые 8 символов: {token[:8]}...)")
        if check_api(token):
            print("\n✅ Соединение с GitLab API успешно установлено.")
            return
        print("\n❌ Текущий токен не работает — запрашиваем новый.")
        token = prompt_token()

    # Финальная проверка с новым токеном
    if token:
        if check_api(token):
            print("\n✅ Соединение с GitLab API успешно установлено.")
        else:
            print("\n❌ Соединение не удалось даже с новым токеном.")
            sys.exit(1)


if __name__ == "__main__":
    main()
