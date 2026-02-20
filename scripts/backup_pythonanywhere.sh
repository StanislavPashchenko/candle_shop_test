#!/bin/bash
# backup.sh - Скрипт для создания бэкапа базы данных и медиафайлов
# Использование: bash backup.sh

# Настройки
PROJECT_NAME="candle_shop_test"
BACKUP_DIR="~/backups"
DATE=$(date +%Y-%m-%d_%H-%M-%S)
BACKUP_NAME="${PROJECT_NAME}_${DATE}"

# Создание директории для бэкапов
mkdir -p ${BACKUP_DIR}

echo "=== Создание бэкапа ${BACKUP_NAME} ==="
echo ""

# 1. Бэкап MySQL базы данных
echo "1. Создание дампа MySQL базы данных..."
mysqldump -u ${MYSQL_USER} -p${MYSQL_PASSWORD} ${MYSQL_DATABASE} > ${BACKUP_DIR}/${BACKUP_NAME}_db.sql

if [ $? -eq 0 ]; then
    echo "   ✓ Дамп базы создан: ${BACKUP_DIR}/${BACKUP_NAME}_db.sql"
else
    echo "   ✗ Ошибка при создании дампа базы данных"
    exit 1
fi

# 2. Архивация медиафайлов
echo "2. Архивация медиафайлов..."
cd ~/candle_shop_test
if [ -d "media" ]; then
    tar -czf ${BACKUP_DIR}/${BACKUP_NAME}_media.tar.gz media/
    echo "   ✓ Медиафайлы заархивированы: ${BACKUP_DIR}/${BACKUP_NAME}_media.tar.gz"
else
    echo "   ℹ Папка media не найдена, пропускаем"
fi

# 3. Архивация статических файлов (если нужно)
echo "3. Архивация статических файлов..."
if [ -d "staticfiles" ]; then
    tar -czf ${BACKUP_DIR}/${BACKUP_NAME}_static.tar.gz staticfiles/
    echo "   ✓ Статические файлы заархивированы: ${BACKUP_DIR}/${BACKUP_NAME}_static.tar.gz"
else
    echo "   ℹ Папка staticfiles не найдена, пропускаем"
fi

echo ""
echo "=== Бэкап завершен! ==="
echo "Файлы бэкапа:"
ls -lh ${BACKUP_DIR}/${BACKUP_NAME}*

echo ""
echo "Для скачивания бэкапов используйте:"
echo "scp candleshoptest@candleshoptest.pythonanywhere.com:${BACKUP_DIR}/${BACKUP_NAME}_db.sql ./"
