from functions import get_file_content, new_chat, write_to_file, get_argument, get_llm_token, get_docs_file
import os
'''
этот скрипт автоматизирует процесс обработки текстового файла (указывается при запуске) с помощью модели OpenAI,
формирования краткого описания и сохранения результата в новый файл.
'''

args = get_argument()

if __name__ == "__main__":
    print(f'Получен путь к файлу: {args.feature}')
    file_content, file_path = get_file_content(args.feature)
    try:
        if file_content:
            checklist_test_review = get_file_content(
                get_docs_file("DOCS_CHECKLIST_REVIEW", "checklist_test_review.md")
            )[0]
            file_template_review = get_file_content(
                get_docs_file("DOCS_TEMPLATE_REVIEW", "file_template_review.md")
            )[0]
            # Дополнительные (пользовательские) правила для нейронки — редактируемый
            # файл в docs/, по аналогии с чек-листом и шаблоном, без пересборки .exe.
            user_rules = get_file_content(
                get_docs_file("DOCS_USER_RULES", "user_rules.md")
            )[0]
            # Получаем директорию файла
            directory = os.path.dirname(file_path)
            filename = os.path.splitext(os.path.basename(file_path))[0]
            # Фактическое число строк теста — объективная метрика, чтобы нейронка
            # не оценивала размер "на глаз" (иначе завышает и ругается даже на
            # ~250 строк при лимите 1000).
            line_fact = f"В проверяемом файле {len(file_content.splitlines())} строк."
            prompt = (
                f"Составь краткий комментарий к тесту\n"
                f"Оцени сложность для понимания теста по шкале 10\n"
                f"Проверь опечатки \n\n"
                f"Строго. Проверь тест на соответствие правилам по пунктам:\n {checklist_test_review} \n\n"
                f"{line_fact}\n\n"
                f"{user_rules}\n\n"
                f"Замечания только по пунктам которые не соответствуют правилам \n\n"
                f"Для ответа используй шаблон: '{file_template_review}' \n\n"
                f"В комментарии указывай где нужно внести изменения \n"
                f"{args.feature}\n"
                f"{file_content}"
            )
            system_prompt =  (
                f"Ты эксперт по тестированию в 1С\n"
                f"Не используй формат MD и таблицы для ответа\n"
                f"Не выводи тело теста, только полную строку с замечанием и комментарии по теме\n"
                
            )
            print("Проверка теста...")
            response = new_chat(get_llm_token(), prompt, system_prompt)
            print("Получен ответ от ассистента")
            # print(response)
            output_file_path = os.path.join(directory,filename+"_AutoCheck.txt")
            write_to_file(output_file_path, response)
        else: 
            print("Файл не найден или пуст")
    except Exception as e:
        print(f"Произошла ошибка: {e}")
    # finally:
    #     input("Нажмите Enter для завершения...") 