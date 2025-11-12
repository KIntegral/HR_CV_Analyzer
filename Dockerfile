FROM python:3.11-slim

WORKDIR /app

# Zainstaluj wymagane pakiety systemowe
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Skopiuj requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Skopiuj pliki aplikacji
COPY streamlit_app.py .
COPY cv_analyzer_backend.py .
COPY arsenal/ ./arsenal/
COPY "IS_New 1.png"

# Expose port
EXPOSE 8501

# Uruchom Streamlit
CMD ["streamlit", "run", "streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501", "--client.showErrorDetails=false"]