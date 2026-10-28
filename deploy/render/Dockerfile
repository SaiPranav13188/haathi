# Haathi backend for Render's free plan (512 MB RAM): light engine (hashing embedder + lexical reranker +
# NumPy vector store), ~175 MB in memory. Gemini (key set in the Render dashboard) handles answers and live voice.
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    HAATHI_ENV=production HAATHI_EMBEDDER=hash HAATHI_RERANKER=lexical HAATHI_VECTOR_STORE=numpy
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt
COPY backend /app/backend
COPY data /app/data
WORKDIR /app/backend
# Render provides $PORT
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000} --ws-ping-interval 20"]
