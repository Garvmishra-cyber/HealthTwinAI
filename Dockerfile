FROM python:3.13-slim

# Install Tesseract OCR and required system libraries
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       tesseract-ocr \
       libgl1 \
       libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:$PORT app:app"]