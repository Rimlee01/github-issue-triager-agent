FROM python:3.12-slim AS base

WORKDIR /app

# Security: run as non-root user
RUN groupadd -r triager && useradd -r -g triager triager

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (Docker layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Data directories for ChromaDB and HuggingFace model cache
RUN mkdir -p /app/data/chroma_db /app/data/hf_cache && chown -R triager:triager /app

USER triager

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
