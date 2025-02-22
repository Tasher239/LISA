# Используем официальный образ Python
FROM python:3.10

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы проекта
COPY requirements.txt .
COPY src /app/src

# Устанавливаем зависимости
RUN pip install -r requirements.txt

# Создаем директорию для базы данных (если используете SQLite)
RUN mkdir -p /app/database

# Переменные окружения (если нужно)
ENV PYTHONPATH=/app

# Запускаем бота
CMD ["python", "src/main.py"]

# docker build -t lisa .
# docker save lisa -o lisa.tar

