# Используйте базовый образ Python
FROM python:3.9

# Установите рабочую директорию в контейнере
WORKDIR /app

# Скопируйте зависимости проекта
COPY requirements.txt .

# Установите зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Скопируйте остальные файлы проекта в контейнер
COPY . .

# Определите команду для запуска вашего приложения
CMD ["python", "tg_nyr.py"]
