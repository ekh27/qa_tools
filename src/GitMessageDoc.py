import subprocess
import os
import sys
from functions import get_argument, new_chat, get_llm_token

"""
Программа для генерации и сохранения сообщения о коммите.

Функциональность:
1. Получение списка файлов, подготовленных к коммиту (staged), с указанием их статуса.
2. Получение подробного списка изменений (diff) для всех staged файлов.
3. LLM формирует по diff краткое описание изменений.
4. В файл сохраняется ТОЛЬКО ответ LLM; если ответ пуст/недоступен — список изменённых файлов.

Использование:
- Программа автоматически выполняет все необходимые действия при запуске.
- Файл combined_message.txt создаётся в корневой директории репозитория.
"""


args = get_argument()
REPO_PATH = args.path
if REPO_PATH == None:
    REPO_PATH = input("Введите путь к репозиторию: ")
    

# Функция для разбора файлов по статусам
def get_staged_files_by_status(REPO_PATH):
    try:
        # Меняем текущую директорию на путь к репозиторию
        os.chdir(REPO_PATH)
        
        # Получаем статус и список staged файлов
        staged_files_output = subprocess.check_output(["git", "diff", "--cached", "--name-status"], encoding="UTF-8").strip()
        
        if not staged_files_output:
            return "No staged files to commit"

        # Словарь для хранения файлов по статусам
        files_by_status = {
            "Added": [],
            "Updated": [],
            "Deleted": [],
            "Renamed": [],
            "Copied": [],
            "Unmerged": [],
            "Other": []
        }

        # Разбираем строки вывода
        for line in staged_files_output.splitlines():
            status, file = line.split("\t", 1)
            if status == "A":
                files_by_status["Added"].append(file)
            elif status == "M":
                files_by_status["Updated"].append(file)
            elif status == "D":
                files_by_status["Deleted"].append(file)
            elif status == "R":
                files_by_status["Renamed"].append(file)
            elif status == "C":
                files_by_status["Copied"].append(file)
            elif status == "U":
                files_by_status["Unmerged"].append(file)
            else:
                files_by_status["Other"].append(file)

        return files_by_status

    except subprocess.CalledProcessError as e:
        print(f"Ошибка выполнения git: {e}")
        print("Проверьте, что указанный путь является git-репозиторием (в каталоге есть .git).")
        return None

# Генерация сообщения на основе файлов по статусам
def generate_commit_message_by_status():
    files_by_status = get_staged_files_by_status(REPO_PATH)

    # git завершился с ошибкой (например, REPO_PATH не является git-репозиторием,
    # git уходит в no-index режим: "unknown option `cached'" / usage git diff --no-index).
    # Раньше здесь падали с "AttributeError: 'NoneType' object has no attribute 'items'".
    if files_by_status is None:
        print("Не удалось получить список изменений (путь не является git-репозиторием?).")
        return None

    if isinstance(files_by_status, str):  # Если сообщение об отсутствии изменений
        print(files_by_status)
        return None

    message_lines = []
    for status, files in files_by_status.items():
        if files:  # Добавляем только непустые категории
            message_lines.append(f"{status} files:")
            message_lines.extend(f"- {file}" for file in files)
            message_lines.append("")  # Пустая строка для разделения категорий
    
    return "\n".join(message_lines)

# Генерация подробного списка изменений
def generate_detailed_diff():
    try:
        # Меняем текущую директорию на путь к репозиторию
        os.chdir(REPO_PATH)
        
        # Получаем подробные изменения для всех staged файлов
        detailed_diff_output = subprocess.check_output(["git", "diff", "--cached"], encoding="UTF-8").strip()
        if not detailed_diff_output:
            print("No staged changes to generate detailed diff")
            return None
        return detailed_diff_output
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        return None

# Сохранение сообщения в файл (в корень репозитория, name unchanged)
def save_combined_message_to_file(message: str, filename: str = "combined_message.txt"):
    try:
        repo_root = REPO_PATH
        file_path = os.path.join(repo_root, filename)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(message)
        print(f"Combined message saved to {file_path}")
    except Exception as e:
        print(f"Error saving combined message: {e}")


def check_llm_connection(token: str) -> bool:
    """Проверка доступности LLM-шлюза лёгким тестовым запросом."""
    try:
        new_chat(token, "Ответь одним словом: ОК", "Ты ассистент. Отвечай кратко.")
        return True
    except Exception as e:
        print(f"Не удалось подключиться к LLM: {e}")
        return False


commit_message = generate_commit_message_by_status()
detailed_diff = generate_detailed_diff()

if detailed_diff and commit_message:
    # Проверяем, что LLM-шлюз доступен, до генерации описания: при недоступности
    # LLM выдаём понятную ошибку и ненулевой код выхода, а не «молчаливый» исход
    # без файла результата (расширение VS Code показывает «файл не найден»).
    if not check_llm_connection(get_llm_token()):
        sys.exit(1)
    try:
        prompt = (
                f"Проанализируй изменения и составь краткое описание для комментария по следующему формату:\n"
                f"Первая строка - обобщенное изменение.\n"
                f"Каждый тезис на новой строке с символом '- '.\n"
                f"\n{detailed_diff}"
                )
        system_prompt = (f"Ты ассистент по подготовке отчета, отвечай кратко и по делу. Не используй Markdown и таблицы")
        response = new_chat(get_llm_token(), prompt, system_prompt)
        # Сохраняем ТОЛЬКО ответ LLM; если ответ пуст/недоступен — список
        # изменённых файлов (чтобы файл не оставался пустым).
        message = response.strip() if response and response.strip() else commit_message
        save_combined_message_to_file(message)
    except Exception as e:
        print(f"Ошибка при вызове new_chat: {e}")
        sys.exit(1)
    # finally:
    #     input("Нажмите Enter для завершения...")
else:
    print("Нет изменений для коммита")