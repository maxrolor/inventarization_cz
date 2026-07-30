#!/usr/bin/env python3
"""
Скрипт для резервного копирования проекта и отправки изменений в Git.
Запуск: python backup_and_commit.py
"""

import os
import subprocess
import tarfile
import datetime
import shutil
from pathlib import Path

# Папка для резервных копий (будет создана в корне проекта)
BACKUP_DIR = "backups"
# Исключаемые каталоги и файлы (не включать в архив)
EXCLUDE = {".git", "venv", "__pycache__", "backups", ".env", ".idea", ".vscode"}


def create_backup(project_root: Path) -> str:
    """Создаёт архив проекта в папке backups с датой и временем."""
    backup_dir = project_root / BACKUP_DIR
    backup_dir.mkdir(exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_name = f"project_backup_{timestamp}.tar.gz"
    archive_path = backup_dir / archive_name

    print(f"📦 Создание архива {archive_path}...")

    with tarfile.open(archive_path, "w:gz") as tar:
        for item in project_root.iterdir():
            if item.name in EXCLUDE:
                print(f"  ⏭️ Пропускаем: {item.name}")
                continue
            tar.add(item, arcname=item.name, recursive=True)

    print(f"✅ Архив создан: {archive_path}")
    return str(archive_path)


def get_commit_message() -> str:
    """Запрашивает у пользователя сообщение для коммита."""
    msg = input("✏️ Введите сообщение для коммита (можно оставить пустым для автоматического): ").strip()
    if not msg:
        msg = f"Автоматический коммит от {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        print(f"Используется сообщение: {msg}")
    return msg


def run_git_command(args: list, cwd: str) -> bool:
    """Выполняет команду git, возвращает True при успехе."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0:
            print(f"❌ Ошибка: {result.stderr.strip()}")
            return False
        print(result.stdout.strip())
        return True
    except Exception as e:
        print(f"❌ Исключение: {e}")
        return False


def main():
    # Определяем корень проекта (место, где находится скрипт)
    script_dir = Path(__file__).parent.resolve()
    os.chdir(script_dir)

    # Проверяем, что это git-репозиторий
    if not (script_dir / ".git").exists():
        print("❌ Текущая папка не является Git-репозиторием!")
        return

    # 1. Резервное копирование
    print("\n🔐 Шаг 1: Создание резервной копии")
    create_backup(script_dir)

    # 2. Запрос сообщения коммита
    print("\n📝 Шаг 2: Ввод сообщения коммита")
    commit_msg = get_commit_message()

    # 3. Добавление всех изменений
    print("\n➕ Шаг 3: Добавление файлов (git add .)")
    if not run_git_command(["add", "."], cwd=script_dir):
        return

    # 4. Коммит
    print("\n💾 Шаг 4: Создание коммита")
    if not run_git_command(["commit", "-m", commit_msg], cwd=script_dir):
        return

    # 5. Push
    print("\n🚀 Шаг 5: Отправка изменений (git push)")
    if not run_git_command(["push"], cwd=script_dir):
        return

    print("\n✅ Готово! Проект заархивирован и изменения отправлены в GitHub.")


if __name__ == "__main__":
    main()