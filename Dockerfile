# Python 3.12 asosida image
FROM python:3.12-slim

# ishchi katalog
WORKDIR /app

# kerakli fayllarni ko‘chirib olish
COPY requirements.txt .

# kutubxonalarni o‘rnatish
RUN pip install --no-cache-dir -r requirements.txt

# butun kodni konteynerga yuklash
COPY . .

# default ishga tushirish komandasi
CMD ["python", "main.py"]