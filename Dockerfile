FROM python:3.11-slim

WORKDIR /app

# Zainstaluj wymagane pakiety systemowe + DejaVu fonts
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    tesseract-ocr \
    fonts-dejavu \
    fontconfig \
    && fc-cache -f -v \
    && rm -rf /var/lib/apt/lists/*

# Skopiuj requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Skopiuj pliki aplikacji
COPY streamlit_app.py .
COPY cv_analyzer_backend.py .
COPY arsenal/ ./arsenal/
COPY IS_New.png /app/IS_New.png

# Expose port
EXPOSE 8501

# Uruchom Streamlit
CMD ["streamlit", "run", "streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8080", "--client.showErrorDetails=false"]
