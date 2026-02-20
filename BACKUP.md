# Инструкция по бэкапу и восстановлению базы данных

## Быстрый старт (PythonAnywhere)

### Создание бэкапа (одной командой)

```bash
cd ~/candle_shop_test
bash scripts/backup_pythonanywhere.sh
```

### Создание бэкапа вручную

```bash
# Дамп базы данных MySQL
mysqldump -u candleshoptest -p candleshoptest\$default > ~/backup_$(date +%Y%m%d_%H%M%S).sql

# Архивация медиафайлов
tar -czf ~/media_backup_$(date +%Y%m%d_%H%M%S).tar.gz ~/candle_shop_test/media/
```

## Подробная инструкция

### 1. Бэкап базы данных MySQL на PythonAnywhere

#### Вариант 1: Полный дамп (рекомендуется)

```bash
# Формат: mysqldump -u [user] -p[password] [database] > [backup_file.sql]
mysqldump -u candleshoptest -pYourPassword candleshoptest\$default > ~/db_backup_$(date +%Y%m%d).sql
```

#### Вариант 2: Дамп с gzip-сжатием (меньше размер)

```bash
mysqldump -u candleshoptest -p candleshoptest\$default | gzip > ~/db_backup_$(date +%Y%m%d).sql.gz
```

#### Вариант 3: Дамп без пароля (через .my.cnf)

Создайте файл `~/.my.cnf`:
```ini
[mysqldump]
user = candleshoptest
password = YourPassword
host = candleshoptest.mysql.pythonanywhere-services.com
```

Затем:
```bash
chmod 600 ~/.my.cnf
mysqldump candleshoptest\$default > ~/db_backup_$(date +%Y%m%d).sql
```

### 2. Бэкап медиафайлов

```bash
# Архивация папки media
tar -czf ~/media_backup_$(date +%Y%m%d_%H%M%S).tar.gz ~/candle_shop_test/media/

# Проверка размера
ls -lh ~/*.tar.gz
```

### 3. Скачивание бэкапов на локальный компьютер

#### Windows (PowerShell):
```powershell
# Скачивание дампа базы
scp candleshoptest@candleshoptest.pythonanywhere.com:~/db_backup_2025*.sql C:\backups\

# Скачивание медиафайлов
scp candleshoptest@candleshoptest.pythonanywhere.com:~/media_backup_2025*.tar.gz C:\backups\
```

#### Linux/Mac:
```bash
# Скачивание всех бэкапов
scp candleshoptest@candleshoptest.pythonanywhere.com:~/db_backup_*.sql ./backups/

# Или через rsync (если доступно)
rsync -avz candleshoptest@candleshoptest.pythonanywhere.com:~/backups/ ./local_backups/
```

### 4. Автоматический бэкап (Cron-задание)

Настройте автоматический бэкап через Cron на PythonAnywhere:

```bash
# Открыть редактор cron
 crontab -e

# Добавить строку для ежедневного бэкапа в 3:00 утра
0 3 * * * cd ~/candle_shop_test && bash scripts/backup_pythonanywhere.sh >> ~/backup_cron.log 2>&1

# Или упрощенная версия (только база)
0 3 * * * mysqldump -u candleshoptest -pYourPassword candleshoptest\$default > ~/backups/auto_db_$(date +\%Y\%m\%d).sql 2>> ~/backup_errors.log
```

## Восстановление из бэкапа

### 1. Восстановление базы данных из дампа

#### Полное восстановление (предварительно очистив базу):
```bash
# ОПАСНО! Удаляет все текущие данные
mysql -u candleshoptest -p -e "DROP DATABASE candleshoptest\$default; CREATE DATABASE candleshoptest\$default;"

# Восстановление из дампа
mysql -u candleshoptest -p candleshoptest\$default < ~/db_backup_20250120.sql
```

#### Восстановление без удаления (может вызвать конфликты):
```bash
mysql -u candleshoptest -p candleshoptest\$default < ~/db_backup_20250120.sql
```

#### Восстановление из gzip-архива:
```bash
gunzip < ~/db_backup_20250120.sql.gz | mysql -u candleshoptest -p candleshoptest\$default
```

### 2. Восстановление медиафайлов

```bash
# Распаковка архива
cd ~/candle_shop_test
tar -xzf ~/media_backup_20250120_143022.tar.gz

# Проверка
ls -la media/
```

### 3. Восстановление на чистую установку

```bash
# 1. Клонирование репозитория (если нужно)
cd ~
git clone https://github.com/StanislavPashchenko/candle_shop_test.git

# 2. Установка зависимостей
cd candle_shop_test
source ../venv/bin/activate
pip install -r requirements.txt

# 3. Восстановление базы
mysql -u candleshoptest -p candleshoptest\$default < ~/db_backup_20250120.sql

# 4. Восстановление медиафайлов (если есть)
tar -xzf ~/media_backup_20250120.tar.gz

# 5. Сбор статики
python manage.py collectstatic --noinput

# 6. Проверка
python manage.py check
```

## SQLite (для локальной разработки)

### Бэкап SQLite:
```bash
# Просто копируем файл базы
cp db.sqlite3 db_backup_$(date +%Y%m%d).sqlite3
```

### Восстановление SQLite:
```bash
cp db_backup_20250120.sqlite3 db.sqlite3
```

### Дамп SQLite в SQL (для миграции на MySQL):
```bash
sqlite3 db.sqlite3 .dump > dump.sql
```

## Автоматизация через Makefile

Создайте файл `Makefile` в корне проекта:

```makefile
.PHONY: backup restore deploy

backup:
	@echo "Creating backup..."
	mysqldump -u $(MYSQL_USER) -p$(MYSQL_PASSWORD) $(MYSQL_DATABASE) > backups/db_$(shell date +%Y%m%d_%H%M%S).sql
	tar -czf backups/media_$(shell date +%Y%m%d_%H%M%S).tar.gz media/

restore:
	@echo "Restoring from backup..."
	mysql -u $(MYSQL_USER) -p$(MYSQL_PASSWORD) $(MYSQL_DATABASE) < $(BACKUP_FILE)

deploy:
	git pull origin main
	pip install -r requirements.txt
	python manage.py migrate
	python manage.py collectstatic --noinput
```

Использование:
```bash
make backup
make restore BACKUP_FILE=backups/db_20250120_120000.sql
```

## Рекомендации по безопасности

1. **Регулярность**: Делайте бэкапы минимум раз в неделю, перед важными изменениями — обязательно
2. **Хранение**: Храните бэкапы в разных местах (локально, в облаке, на PythonAnywhere)
3. **Тестирование**: Периодически проверяйте восстановление из бэкапов
4. **Пароли**: Никогда не храните пароли в открытом виде в скриптах
5. **Доступ**: Ограничьте права доступа к файлам бэкапов (`chmod 600`)

## Проверка целостности бэкапа

```bash
# Проверка SQL-дампа (ищем ошибки)
head -20 ~/db_backup_20250120.sql

# Проверка размера (должен быть > 0)
ls -lh ~/db_backup_*.sql

# Проверка архива
tar -tzf ~/media_backup_20250120.tar.gz | head -10
```

## Полезные команды

```bash
# Размер базы данных MySQL
mysql -u candleshoptest -p -e "SELECT table_name, ROUND(((data_length + index_length) / 1024 / 1024), 2) AS 'Size (MB)' FROM information_schema.TABLES WHERE table_schema = 'candleshoptest\$default';"

# Очистка старых бэкапов (оставляем только последние 5)
cd ~/backups && ls -t db_backup_*.sql | tail -n +6 | xargs rm -f
```

---

**Важно**: Всегда проверяйте бэкап перед важными изменениями!
