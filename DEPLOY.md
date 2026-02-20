# Инструкция по деплою на PythonAnywhere

## 1. Подготовка к деплою

### 1.1. Загрузка изменений на GitHub

На локальной машине выполните:

```bash
git add .
git commit -m "Обновление: конфигуратор товаров с мультиязычностью"
git push origin main
```

### 1.2. Проверка окружения PythonAnywhere

Откройте консоль Bash на PythonAnywhere и проверьте настройки:

```bash
# Проверка переменных окружения
echo $MYSQL_DATABASE
echo $MYSQL_USER
echo $MYSQL_PASSWORD
echo $MYSQL_HOST
```

Если переменные не установлены, добавьте их в `.env` файл или в настройки веб-приложения (Web > Environment variables).

## 2. Деплой на PythonAnywhere

### Вариант 1: Ручной деплой (пошагово)

#### Шаг 1: Переход в директорию проекта
```bash
cd ~/candle_shop_test
```

#### Шаг 2: Получение изменений из git
```bash
git pull origin main
```

#### Шаг 3: Активация виртуального окружения
```bash
source ../venv/bin/activate
```

#### Шаг 4: Установка зависимостей
```bash
pip install -r requirements.txt
```

#### Шаг 5: Применение миграций
```bash
python manage.py migrate
```

#### Шаг 6: Сбор статических файлов
```bash
python manage.py collectstatic --noinput
```

#### Шаг 7: Проверка Django
```bash
python manage.py check
```

#### Шаг 8: Перезагрузка веб-приложения
В панели PythonAnywhere: **Web > Reload** (или нажмите зеленую кнопку Reload)

### Вариант 2: Автоматический деплой (скриптом)

Загрузите скрипт deploy.sh на сервер и выполните:

```bash
cd ~/candle_shop_test
bash scripts/deploy_pythonanywhere.sh
```

Затем перезагрузите веб-приложение в панели.

## 3. Решение проблем

### Проблема: ImportError или ModuleNotFoundError

```bash
# Переустановка зависимостей
pip install --force-reinstall -r requirements.txt
```

### Проблема: Миграции не применяются

```bash
# Проверка статуса миграций
python manage.py showmigrations

# Если нужно сбросить миграции (ОПАСНО - только для dev!)
# python manage.py migrate shop zero
# python manage.py makemigrations shop
# python manage.py migrate
```

### Проблема: Статические файлы не загружаются

```bash
# Полная очистка и пересборка
python manage.py collectstatic --noinput --clear
```

## 4. Проверка после деплоя

1. Откройте сайт: https://candleshoptest.pythonanywhere.com
2. Проверьте страницу товара с опциями
3. Проверьте добавление в корзину
4. Проверьте оформление заказа
5. Проверьте админку: https://candleshoptest.pythonanywhere.com/admin

## 5. Откат изменений (если что-то пошло не так)

```bash
# Откат к предыдущей версии
git log --oneline -5  # посмотреть историю
git reset --hard HEAD~1  # откат на 1 коммит назад
git push origin main --force  # принудительный push

# Переустановка на PythonAnywhere
cd ~/candle_shop_test
git pull origin main
python manage.py migrate
python manage.py collectstatic --noinput
```

---

**Важно**: Всегда делайте бэкап базы данных перед деплоем (см. BACKUP.md)!
