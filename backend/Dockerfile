# Build context is backend/ (Railway service root directory = backend).
FROM python:3.11-slim

# faiss-cpu wheels link against GNU OpenMP, which python:slim doesn't ship.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# FAISS index + sqlite metadata live on the Railway volume mounted at /data.
ENV DATA_DIR=/data

# Railway injects PORT; shell form so it expands (default for local runs).
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
