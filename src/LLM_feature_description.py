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
            file_template_description = get_file_content(
                get_docs_file("DOCS_TEMPLATE_DESCRIPTION", "file_template_description.md")
            )[0]
            # Получаем директорию файла
            directory = os.path.dirname(file_path)
            filename = os.path.splitext(os.path.basename(file_path))[0]
            prompt = (
                f"Определи название теста"
                f"Не используй формат MD и таблицы \n"
                f"Не выводи тело теста, только описание \n"
                f"Составь краткий комментарий к тесту\n"
                f"Используй шаблон: {file_template_description} \n\n"
                f"{file_content}"
            )
            system_prompt =  (
                f"Ты технический писатель. Твоя задача составить краткое описание для теста.\n"
            )
            print("Подготовка описания")
            response = new_chat(get_llm_token(), prompt, system_prompt)
            print("Получен ответ от чата")
            # print(response)
            output_file_path = os.path.join(directory,filename+"_description.txt")
            write_to_file(output_file_path, response)
        else: 
            print("Файл не найден или пуст")
    except Exception as e:
        print(f"Произошла ошибка: {e}")
    # finally:
    #     input("Нажмите Enter для завершения...") 