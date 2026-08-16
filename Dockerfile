FROM python:3.13-slim

# Install Tesseract OCR and required system libraries
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       tesseract-ocr \
       libgl1 \
       libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Application directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Environment settings
ENV PYTHONUNBUFFERED=1
ENV OMP_THREAD_LIMIT=1

# Start Flask with Gunicorn
# Increased timeout for OCR processing
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 1 --timeout 120 app:app"]
