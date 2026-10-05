# QA_Tools — утилиты для тестирования Vanessa Automation

## Описание

Набор Python-скриптов, которые автоматизируют рутинные задачи тестировщика **Vanessa Automation** (1С): описание и ревью `.feature`-файлов через LLM, осмысленные сообщения коммитов, отчёты о работе за период, запуск GitLab-пайплайнов и контроль тегов запуска.

Инструменты используют **LLM (любой OpenAI-совместимый API)** — подходит и локальный сервер (Ollama, LM Studio, vLLM), и облачный провайдер — а также **Git** и **GitLab API**. Единый файл настроек `settings.env` собирает все параметры (LLM, GitLab, токены, сертификаты) в одном месте рядом с запускаемым файлом.

### Функциональность

- описание `.feature`-файла через LLM (для Merge Request);
- ревью теста по чек-листу стандартов;
- осмысленное сообщение коммита по staged-файлам;
- отчёт о проделанной работе за период из git-логов;
- запуск GitLab-пайплайна из JSON-конфига;
- контроль тегов запуска: проверка наличия тегов из JSON-параметров VA в `.feature`-файлах;
- ревью Merge Request по diff из GitLab;
- половина задач решается чистым Python без единого токена LLM.

### Установка и использование

#### Быстрый старт

Откройте PowerShell в корневом каталоге проекта, создайте и активируйте виртуальное окружение, затем установите зависимости:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Запустите сборщик и укажите нужные `.py`-файлы через запятую, например `get_diff_mr.py, LLM_file_description.py`:

```powershell
.\BUILD_bat\_build.bat
```

Готовые программы появятся в каталоге `dist`. Создайте каталог `exe` в корне проекта (или в текущем каталоге), переместите туда собранные программы и положите рядом рабочий файл настроек settings.env:

```powershell
New-Item -ItemType Directory -Force .\exe
Move-Item .\dist\*.exe .\exe\
Copy-Item .\src\settings.env .\exe\settings.env
```

После этого программы можно запускать непосредственно из `exe` или через соответствующие файлы `bat\RUN_<имя>.bat`. Файл `settings.env` должен находиться рядом с `.exe`, чтобы программы могли прочитать адреса сервисов и токены.

#### Требования

- **Python 3.10+**;
- Git-репозиторий тестов и доступ к **GitLab API** (для скриптов GitLab);
- LLM-эндпоинт (OpenAI-совместимый): локальная **Ollama** (по умолчанию `http://localhost:11434/v1`), LM Studio, vLLM или облачный API.

#### Виртуальное окружение (venv)

Зависимости собраны в `requirements.txt` (`openai`, `requests`, `urllib3`, `pyinstaller`). Рекомендуется ставить их в изолированное окружение:

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Запуск скриптов из каталога `src/` внутри активированного окружения:

```bash
cd src
python LLM_feature_description.py -f "path/to/file.feature"
```

> Замечания: виртуальное окружение `.venv/` не попадает в git (см. `.gitignore`). Скрипты работают из `src/`, поэтому активация venv не конфликтует с настройками — настройки читаются только из `settings.env`, переменные окружения ОС не используются.

#### Настройки проекта: файл `settings`

Все настройки задаются в **одном месте** — файле `settings` или `settings.env` (в стиле `.env`, `KEY=value`). **Единственный источник настроек — этот файл**; переменные окружения ОС не используются. Файл **не хранится в git** (см. `.gitignore`); коммитится только обезличенный шаблон `settings.env.example`.

Файл настроек ищется **рядом с запускаемым файлом**: `src/settings.env` для запуска из исходников и `settings`/`settings.env` рядом с `.exe` для собранных скриптов (дополнительно проверяются текущая рабочая директория и корень репозитория). Загружается автоматически при импорте (`src/functions.py` → `load_env_file`).

```bash
# settings.env
LLM_BASE_URL=http://localhost:11434/v1   # локальная Ollama, или https://... для облака
LLM_MODEL=qwen2.5:7b
LLM_API_KEY=                             # для локального LLM не нужен (можно пустым)
GITLAB_API_URL=https://gitlab.example.com
GITLAB_TOKEN=...                         # личный токен GitLab
# GITLAB_PROJECT_ID=12345                # дефолтный проект для get_diff_mr (иначе запрашивается)
# CA_BUNDLE=C:\path\to\ca-bundle.crt     # корневой CA для приватного GitLab (опционально)
# DOCS_DIR=C:\path\to\docs               # каталог шаблонов/чек-листов (по умолчанию: docs/ рядом с файлом)
# DOCS_TEMPLATE_DESCRIPTION=file_template_description.md   # имена шаблонов/чек-листов (переопределение)
# DOCS_TEMPLATE_REVIEW=file_template_review.md
# DOCS_CHECKLIST_REVIEW=checklist_test_review.md
# DOCS_USER_RULES=user_rules.md          # дополнительные (редактируемые) правила для нейронки при ревью
# DEFAULT_VARIABLES_FILE=C:\path\to\run_pipeline_default_variables.json   # путь к JSON с дефолтными переменными пайплайна
# DEPLOY_DIR=C:\path\to\VAtest           # каталог деплоя .exe (для BUILD_bat\_move.bat)
```

Если `settings.env` нет — для LLM используется дефолтный локальный эндпоинт, для GitLab — дефолтный URL (`https://gitlab.com`), а значения, которые код не может взять из дефолтов, запрашиваются интерактивно.

> Подробнее о параметрах `new_chat()` см. `src/functions.py` (`get_llm_config`, `get_llm_token`, `get_gitlab_token`, `get_ca_bundle`).

#### Токены

Токены задаются в `settings.env` и не попадают в git:

```env
LLM_API_KEY=...        # токен LLM (для локального LLM не обязателен)
GITLAB_TOKEN=...       # токен GitLab
```

Файл `settings.env` **не хранится в git** (см. `.gitignore`), токены защищены.

#### Структура репозитория

```
src/              — все CLI-утилиты + библиотека functions.py + настроечные JSON
  ├── functions.py                  — общая библиотека (LLM-чат, токены, настройки, пути)
  ├── LLM_feature_description.py    — описание .feature по шаблону
  ├── LLM_feature_AutoCheck.py      — ревью теста по чек-листу
  ├── LLM_file_description.py       — описание произвольного файла
  ├── GitMessageDoc.py              — сообщение коммита по staged-файлам
  ├── Report_from_commits.py        — отчёт о работе автора за период
  ├── get_diff_mr.py                — ревью Merge Request по diff из GitLab
  ├── run_pipeline_with_config.py   — запуск GitLab-пайплайна из JSON-конфига
  ├── collect_and_check_tags.py     — контроль тегов запуска в .feature
  ├── check_gitlab_api.py           — проверка доступа к GitLab API (служебный)
  ├── tst_llm.py                    — проверка LLM-эндпоинта (служебный)
  ├── __init__.py                   — динамический импорт инструментов
  ├── run_pipeline_default_variables.json  — дефолтные переменные пайплайна
  └── settings.env                  — настройки/токены (в .gitignore; шаблон — settings.env.example)
bat/_common_build.bat — общий поиск Python/PyInstaller и DEPLOY_DIR (для сборки/деплоя)
BUILD_bat/_build.bat  — сборка инструмента .py → .exe (PyInstaller) в dist\
BUILD_bat/_move.bat   — деплой .exe в ПРОД (%DEPLOY_DIR%\scripts\exe\)
configs/              — JSON-конфиги пайплайнов (project_id, ref, переменные БД/тест-план)
docs/                 — шаблоны описания/ревью, чек-лист и редактируемые правила (user_rules.md)
requirements.txt      — зависимости Python (openai, requests, urllib3, pyinstaller)
settings.env.example  — обезличенный шаблон настроек (коммитится)
readmi_temp.md        — внутренний шаблон структуры README
```

> `.exe` и сгенерированные `bat/RUN_*.bat` **не хранятся в репозитории** — они являются результатом сборки/деплоя (см. ниже) и живут вне проекта.

#### Общие аргументы CLI

| Флаг | Назначение |
|------|-----------|
| `-p`, `--path` | Путь к Git-репозиторию |
| `-f`, `--feature` | Путь к `.feature`-файлу / файлу |
| `-n`, `--name` | Логин автора |
| `-ds`, `--diff-start` | Дата начала периода (ГГГГ-ММ-ДД) |
| `-dn`, `--diff-end` | Дата конца периода (ГГГГ-ММ-ДД) |
| `-v`, `--verbose` | Подробный вывод |
| `--dry-run` | Проверка параметров без выполнения |

#### Запуск

Все инструменты запускаются как standalone-скрипты из `src/`:

```bash
cd src
python LLM_feature_description.py -f "path/to/file.feature"
python LLM_feature_AutoCheck.py -f "path/to/file.feature"
python LLM_file_description.py -f "path/to/file"
python GitMessageDoc.py -p "/repo/path"
python Report_from_commits.py -p "/repo/path" -n "username" -ds "2024-01-01" -dn "2024-12-31"
python get_diff_mr.py
python run_pipeline_with_config.py -cf "config.json"
python collect_and_check_tags.py -j <json_dir> -f <features_dir> -m <mask> [-o <out>]
python check_gitlab_api.py
python tst_llm.py
```

#### Сборка `.exe` и деплой (опционально)

Проект можно собрать в самодостаточные `.exe` и развернуть в прод-папку:

`BUILD_bat\_build.bat` необходимо запускать под виртуальным окружением проекта. Окружение должно находиться в `.venv` (допускается также `venv`) и содержать зависимости из `requirements.txt`, включая PyInstaller:

```bat
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
BUILD_bat\_build.bat
```

При запуске `BUILD_bat\_build.bat` сам активирует найденное окружение `.venv`/`venv`. Скрипт принимает один `.py`-файл или несколько файлов, перечисленных через запятую:

```bat
BUILD_bat\_build.bat src\get_diff_mr.py
BUILD_bat\_build.bat "src\get_diff_mr.py, src\LLM_file_description.py"
```

Без аргументов скрипт запрашивает тот же список интерактивно. Для каждого файла он последовательно собирает `dist\<name>.exe`, очищает остаточные файлы PyInstaller и создаёт `bat\RUN_<name>.bat`. Для файлов из `src` можно вводить только имя, например `get_diff_mr.py, LLM_file_description.py`.

`BUILD_bat\_move.bat` переносит собранный `.exe` в папку деплоя (`DEPLOY_DIR` в `settings.env`).

- Поиск Python/PyInstaller задаётся в `bat/_common_build.bat` (переопределяется переменной `PY`).
- Каталог деплоя задаётся ключом `DEPLOY_DIR` в корневом `settings.env` (бат-сборка читает его и раскладывает в `%DEPLOY_DIR%\scripts\exe\`).
- `.exe` читают настройки из своей директории, поэтому `BUILD_bat\_move.bat` при переносе кладёт рядом с exe рантайм-файлы: `settings.env` (из `src/settings.env` — единый живой конфиг; шаблон `settings.env.example` в деплое не участвует) и `run_pipeline_default_variables.json`. Если живого конфига нет — деплой прерывается, чтобы не оставить ПРОД без настроек.

### Пример работы

#### LLM_feature_description — описание теста для MR

Извлекает из `.feature`-файла имя теста и **номер задачи**, формирует описание по шаблону `docs/file_template_description.md` — готовое для вставки в Merge Request (без Markdown/таблиц).

```bash
python LLM_feature_description.py -f "path/to/file.feature"
```
Результат: `{file}_description.txt` рядом с исходным файлом.

#### LLM_feature_AutoCheck — проверка теста по стандартам

LLM сверяет `.feature`-файл с чек-листом `docs/checklist_test_review.md`: оценивает **когнитивную сложность** (шкала 1–10), **форматирование**, **именование сценариев**, использование **групп шагов**, наличие **запрещённых конструкций**. Замечания оформляются по шаблону `docs/file_template_review.md`. Дополнительные правила (например, порог размера теста) берутся из редактируемого файла `docs/user_rules.md` — их можно менять без пересборки. Фактическое число строк файла передаётся нейронке объективно, чтобы она не завышала оценку размера.

```bash
python LLM_feature_AutoCheck.py -f "path/to/file.feature"
```
Результат: `{file}_AutoCheck.txt`.

#### LLM_file_description — описание произвольного файла

Как и описание теста, но для любого файла.

```bash
python LLM_file_description.py -f "path/to/file"
```
Результат: `{file}_description.txt`.

#### GitMessageDoc — осмысленный коммит за 30 секунд

Собирает **staged-файлы**, получает их **diff** и через LLM формирует краткое информативное описание изменений вместо формального перечня файлов.

```bash
python GitMessageDoc.py -p "/repo/path"
```
Результат: `combined_message.txt` в репозитории.

#### Report_from_commits — отчёт о работе за спринт

Анализирует **git-логи по автору и датам** (`--diff-filter=A/M/R` для `.feature`): считает количество **новых** и **изменённых** `.feature`-файлов, собирает **заголовки и тела** сообщений коммитов, группирует изменения по **номерам задач**, LLM собирает связный отчёт.

```bash
python Report_from_commits.py -p "/repo/path" -n "username" -ds "2024-01-01" -dn "2024-12-31"
```
Результаты (в каталоге `GitMessageOut`): `new_feature_files_count.txt`, `commit_messages.txt`, `output_file_report.txt`.

#### get_diff_mr — ревью Merge Request

По URL MR извлекает diff и список затронутых `.feature`-файлов, генерирует отчёт о ревью через LLM. Настройки: базовый URL — `GITLAB_API_URL`, токен — `GITLAB_TOKEN`, ID проекта — `GITLAB_PROJECT_ID` (иначе запрашивается), корневой CA — `CA_BUNDLE`. Вывод сохраняется в текущую директорию.

```
Введите URL MR: https://gitlab.example.com/group/project/merge_requests/123
```
Результаты: `diffMergeRequest.txt`, `diffMergeRequest_name_files.txt`, `MergeRequest.txt`.

#### run_pipeline_with_config — запуск пайплайна из конфига

Читает JSON-конфиг (например, `configs/example_finance.json`: `project_id`, ветка `ref`, переменные БД/тест-план и т.д.), объединяет с дефолтами (`src/run_pipeline_default_variables.json`), запускает пайплайн через **GitLab API** и выводит URL.

Особенности переменных:
- `PATH_TS_FOLDER` хранится **относительным** путём (без префикса репозитория). Перед отправкой к нему подставляется `PREFIX_REPO` (дефолт `/repo_va/`, задаётся в `run_pipeline_default_variables.json`) — итог, например: `/repo_va/Features/GLOBAL/Example`.
- Введённый пользователем путь до тестов также трактуется как относительный — префикс добавляется автоматически.

```bash
python run_pipeline_with_config.py -cf "config.json"
```

#### collect_and_check_tags — контроль тегов запуска в `.feature`-файлах

Собирает теги из **JSON-параметров VA** (поля `СписокТеговОтбор` и `СписокТеговИсключение`) у файлов, имя которых содержит маску, и проверяет их наличие в `.feature`-файлах.

```bash
python collect_and_check_tags.py -j <json_dir> -f <features_dir> -m <mask> [-o <out>]
```

Параметры:
- `-j/--json` — путь к директории с JSON-параметрами (обязательно);
- `-f/--features` — путь к директории с `.feature`-файлами (обязательно);
- `-m/--mask` — маска для поиска JSON-файлов (обязательно);
- `-o/--output` — файл-отчёт (по умолчанию `tags_report.txt`);
- если параметры не заданы (или заданы не все) — запрашиваются интерактивно.

Особенности:
- проверка тегов **нечувствительна к регистру**, но по границам тега (тег `Metazon` не «ловит» `@Metazon_pack`);
- в консоль выводятся только итоги: всего файлов / с тегами / без тегов;
- подробный отчёт сгруппирован по тегам: разделы **«Тесты для запуска»** (теги отбора) и **«Исключены из запуска»** (теги исключения), для каждого тега указан JSON-источник;
- поддержка JSON с UTF-8 BOM.

Пример:
```bash
python collect_and_check_tags.py -j ./vaparams/global -f "Features/GLOBAL/BP_KAZ" -m "KAZTest"
```

#### Служебные скрипты

- `check_gitlab_api.py` — проверка доступа к GitLab API (URL из `GITLAB_API_URL`, токен из `GITLAB_TOKEN`; при невалидном токене запрашивает новый);
- `tst_llm.py` — проверка LLM-эндпоинта (отправляет тестовое сообщение и выводит ответ).
