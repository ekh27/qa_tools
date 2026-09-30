import argparse
import subprocess
from functions import get_argument, read_file, new_chat, write_to_file, get_llm_token
import os

'''
Скрипт `count_new_files.py` выполняет анализ изменений в Git-репозитории за заданный период времени для конкретного автора. Основные функции скрипта:

1. **Получение информации о новых файлах**:
   - Использует команду `git log` с фильтрами для получения списка новых (`--diff-filter=A`), измененных (`--diff-filter=M`) и перемещенных (`--diff-filter=R`) файлов с расширением `.feature`.
   - Обрабатывает вывод команды, суммируя количество строк, добавленных и удаленных, и собирает информацию о каждом файле.

2. **Обработка результатов**:
   - Исключает перемещенные файлы из списка новых файлов.
   - Классифицирует файлы как новые или исправленные на основе количества изменений.
   - Подсчитывает общее количество добавлений и удалений.

3. **Сохранение результатов**:
   - Сохраняет общую информацию о новых и измененных файлах в файл `new_feature_files_count.txt`.
   - Сохраняет описания коммитов за заданный период в файл `commit_messages.txt`.

4. **Взаимодействие с пользователем**:
   - Запрашивает у пользователя путь к Git-репозиторию
   - Создает директорию для сохранения результатов, если она еще не существует.
   - Переключается в указанную директорию и на указанную ветку.

5. **Обработка ошибок**:
   - Включает обработку ошибок при выполнении команд Git и при записи в файлы, выводя соответствующие сообщения.

Скрипт полезен для анализа активности разработчика в определенном периоде, особенно для отслеживания внесения новых файлов и изменений в существующие.
'''


def get_new_files_details(author, since, until):
    try:
        # Формируем команду для получения списка новых файлов с изменениями
        command_new_files = [
            "git", "log",
            "--author", author,
            "--since", since,
            "--until", until,
            "--numstat",
            "--diff-filter=A",  # Только новые файлы
            "--pretty=format:"
        ]
        
        # Команда для получения списка измененных файлов
        command_modified_files = [
            "git", "log",
            "--author", author,
            "--since", since,
            "--until", until,
            "--numstat",
            "--diff-filter=M",  # Только измененные файлы
            "--pretty=format:"
        ]
        
        # Команда для получения списка перемещенных файлов
        command_renamed_files = [
            "git", "log",
            "--author", author,
            "--since", since,
            "--until", until,
            "--numstat",
            "--diff-filter=R",  # Только перемещенные файлы
            "--pretty=format:"
        ]
        
        # Выполняем команду для новых файлов
        result_new_files = subprocess.run(
            command_new_files,
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8',
            errors='replace'  # Заменяет некорректные символы на заменитель
        )
        output_new_files = result_new_files.stdout
        
        # Выполняем команду для измененных файлов
        result_modified_files = subprocess.run(
            command_modified_files,
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8',
            errors='replace'  # Заменяет некорректные символы на заменитель
        )
        output_modified_files = result_modified_files.stdout
        
        # Выполняем команду для перемещенных файлов
        result_renamed_files = subprocess.run(
            command_renamed_files,
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8',
            errors='replace'  # Заменяет некорректные символы на заменитель
        )
        output_renamed_files = result_renamed_files.stdout
        
        if not output_new_files and not output_modified_files:
            print("Нет новых или измененных файлов за указанный период.")
            return set(), set()

        # Обрабатываем вывод для новых файлов
        new_files = set()
        for line in output_new_files.splitlines():
            if line:
                parts = line.split(maxsplit=2)
                if len(parts) == 3 and parts[2].endswith('.feature'):
                    new_files.add(parts[2])

        # Обрабатываем вывод для измененных файлов
        modified_files = set()
        for line in output_modified_files.splitlines():
            if line:
                parts = line.split(maxsplit=2)
                if len(parts) == 3 and parts[2].endswith('.feature'):
                    modified_files.add(parts[2])

        # Обрабатываем вывод для перемещенных файлов
        renamed_files = set()
        for line in output_renamed_files.splitlines():
            if line:
                parts = line.split(maxsplit=2)
                if len(parts) == 3 and parts[2].endswith('.feature'):
                    renamed_files.add(parts[2])

        # Исключаем перемещенные файлы из списка новых файлов
        new_files -= renamed_files

        return new_files, modified_files

    except subprocess.CalledProcessError as e:
        print(f"Ошибка при выполнении команды Git: {e.stderr}")
        return set(), set()
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        return set(), set()

def save_result_to_file(result, modified_files_count, filename):
    try:
        with open(filename, 'w', encoding='utf-8') as file:
            file.write(f"Количество новых файлов с расширением .feature: {result}\n")
            file.write(f"Количество измененных файлов с расширением .feature: {modified_files_count}\n")
        print(f"Результат сохранен в файл {filename}")
    except IOError as e:
        print(f"Ошибка при записи в файл: {e}")

def save_commit_messages_to_file(author, since, until, filename):
    try:
        # Формируем команду для получения описаний коммитов
        command = [
            "git", "log",
            "--author", author,
            "--since", since,
            "--until", until,
            "--pretty=format:%s%n%n%b",  # Заголовок + тело описания коммита
            "--grep=^Merge branch",  # Фильтруем коммиты с "Merge branch"
            "--invert-grep"          # Инвертируем фильтр
        ]
        
        # Выполняем команду и получаем вывод с явной кодировкой UTF-8
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8',
            errors='replace'  # Заменяет некорректные символы на заменитель
        )
        commit_messages = result.stdout
        
        if not commit_messages:
            print("Нет коммитов за указанный период.")
            return
        
        # Сохраняем описания коммитов в файл
        with open(filename, 'w', encoding='utf-8') as file:
            file.write(commit_messages)
        print(f"Описания коммитов сохранены в файл {filename}")
    
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при выполнении команды Git: {e.stderr}")
    except Exception as e:
        print(f"Произошла ошибка: {e}")

if __name__ == "__main__":

    # Получаем аргументы
    args = get_argument()

    #Если нет аргументов запрашиваем у пользователя путь к директории с Git
    git_directory = args.path
    if git_directory == None:
        git_directory = input("Введите путь к репозиторию: ")            
    print(git_directory)
    # Путь к директории для сохранения результатов
    results_directory = os.path.join(git_directory,"GitMessageOut")
    
    # Создаем директорию для сохранения результатов, если она еще не существует
    if not os.path.exists(results_directory):
        os.makedirs(results_directory)
    
    # Переключаемся в указанную директорию
    try:
        os.chdir(git_directory)
    except FileNotFoundError:
        print(f"Директория {git_directory} не найдена.")
        exit(1)
    except Exception as e:
        print(f"Не удалось перейти в директорию {git_directory}: {e}")
        exit(1)
    
    # Параметры для подсчета новых файлов
    author = args.name
    if author == None:
        author = input("Введите логин: ")
    since = args.diff_start
    if since == None:
        since = input("Введите дату от (Формат ГГГГ-ММ-ДД): ")
    until = args.diff_end
    if until == None:
        until = input("Введите дату до (Формат ГГГГ-ММ-ДД): ")

    result_filename = os.path.join(results_directory, "new_feature_files_count.txt")
    commit_messages_filename = os.path.join(results_directory, "commit_messages.txt")
    output_file_path = os.path.join(results_directory, "output_file_report.txt")

    try:
        # Получаем новые и измененные файлы
        new_files, modified_files = get_new_files_details(author, since, until)

        # Получаем количество новых файлов
        new_files_count = len(new_files)

        # Получаем количество измененных файлов
        modified_files_count = len(modified_files)

        # Сохраняем результат в файл
        save_result_to_file(new_files_count, modified_files_count, result_filename)

        # Сохраняем описания коммитов в файл
        save_commit_messages_to_file(author, since, until, commit_messages_filename)

        commit_messages_data = read_file(commit_messages_filename)
        
        prompt = (
                f"Объедини задачи по номерам, и составь краткое описание, используй имена файлов есть указаны \n" 
                f"составь краткий отчет о проделанной работе \n" 
                f"укажи полезность работ \n" 
                f"Объедини строки по кодам задач, код (без номера) относится к конкретному проекту, раздели на задачи общие по логике \n" 
                f"\n{commit_messages_data}"
            )

        
        system_prompt = "Ты ассистент по подготовке отчетов, не используй Markdown и таблицы"
        response = new_chat(get_llm_token(),prompt,system_prompt)
        write_to_file(output_file_path, response)
    except Exception as e:
        print(f"Нет данных для анализа")
        # debug
        # print(f"{e}")
        