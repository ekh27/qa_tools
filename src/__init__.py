# Динамическая загрузка утилит
import os
import importlib
from pathlib import Path

__all__ = []

# Автоматически импортируем все модули утилит
_tools_dir = Path(__file__).parent
for file in _tools_dir.glob("*.py"):
    if file.stem != "__init__":
        try:
            importlib.import_module(f"{file.stem}")
        except Exception as e:
            print(f"Ошибка импорта {file.stem}: {e}")