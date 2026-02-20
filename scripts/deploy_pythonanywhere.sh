#!/bin/bash
# deploy.sh - Скрипт для деплоя на PythonAnywhere
# Использование: bash deploy.sh

echo "=== Деплой на PythonAnywhere ==="
echo ""

# 1. Переход в директорию проекта
cd ~/candle_shop_test || exit 1

# 2. Получение последних изменений из git
echo "1. Получение изменений из git..."
git pull origin main

# 3. Активация виртуального окружения
echo "2. Активация виртуального окружения..."
source ../venv/bin/activate

# 4. Установка зависимостей
echo "3. Установка зависимостей..."
pip install -r requirements.txt --quiet

# 5. Применение миграций
echo "4. Применение миграций..."
python manage.py migrate --noinput

# 6. Сбор статических файлов
echo "5. Сбор статических файлов..."
python manage.py collectstatic --noinput --clear

# 7. Проверка системы
echo "6. Проверка Django..."
python manage.py check --deploy

echo ""
echo "=== Деплой завершен! ==="
echo "Не забудьте перезагрузить веб-приложение в панели PythonAnywhere (Web > Reload)"
