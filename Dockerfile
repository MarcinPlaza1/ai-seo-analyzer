FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instalacja zależności systemowych
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    python3-dev \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libcairo2 \
    libffi-dev \
    libssl-dev \
    wget \
    curl \
    # Dodatkowe zależności dla WeasyPrint
    libpango1.0-dev \
    libharfbuzz-dev \
    libgdk-pixbuf2.0-dev \
    shared-mime-info \
    mime-support \
    libglib2.0-dev \
    libcairo2-dev \
    libxml2-dev \
    libgirepository1.0-dev \
    # Dodatkowe biblioteki dla gobject
    libglib2.0-0 \
    gobject-introspection \
    gir1.2-gtk-3.0 \
    pkg-config \
    # Czyszczenie cache apt
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Kopiowanie plików konfiguracyjnych
COPY requirements.txt setup.py ./

# Instalacja zależności Pythona
RUN pip install --no-cache-dir pip --upgrade && \
    pip install --no-cache-dir wheel setuptools && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install -e .

# Instalacja modelu spaCy
RUN python -m spacy download pl_core_news_sm

# Kopiowanie kodu aplikacji
COPY . .

# Ustawienie zmiennych środowiskowych
ENV PYTHONPATH=/usr/lib/python3/dist-packages:/app
ENV GI_TYPELIB_PATH=/usr/lib/girepository-1.0
ENV LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
