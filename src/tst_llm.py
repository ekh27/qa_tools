"""Служебный тест LLM: проверяет доступ к настроенному LLM-эндпоинту.

Использует те же настройки, что и остальные скрипты: адрес/модель из env
LLM_BASE_URL / LLM_MODEL (см. functions.get_llm_config), токен через
functions.get_llm_token() (env LLM_API_KEY → settings).
"""

from functions import new_chat, get_llm_token, get_llm_config


def main():
    token = get_llm_token()
    base_url, model = get_llm_config()
    print(f"LLM: {base_url} (model={model})")
    if not token:
        print("Токен не задан (LLM_API_KEY или settings); "
              "для локального LLM это обычно не важно.")

    response = new_chat(token, "Привет", "отвечай как пират")
    print("Получен ответ от чата")
    print(response)


if __name__ == "__main__":
    main()
