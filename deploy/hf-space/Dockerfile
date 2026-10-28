# Haathi backend for a Hugging Face Docker Space (free CPU: 2 vCPU, 16 GB RAM).
# Full models (BGE-M3 + bge-reranker-v2-m3) are baked into the image so a sleeping Space wakes up quickly.
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 HF_HOME=/home/user/.cache/huggingface \
    HAATHI_ENV=production HAATHI_VECTOR_STORE=qdrant-memory OMP_NUM_THREADS=2 TOKENIZERS_PARALLELISM=false
RUN useradd -m -u 1000 user
WORKDIR /app
COPY --chown=user requirements.txt /app/requirements.txt
# CPU-only PyTorch keeps the image small (no CUDA)
RUN pip install --index-url https://download.pytorch.org/whl/cpu "torch>=2.4,<3" && pip install -r /app/requirements.txt
USER user
RUN python -c "from huggingface_hub import snapshot_download as d; d('BAAI/bge-m3'); d('BAAI/bge-reranker-v2-m3')"
COPY --chown=user backend /app/backend
COPY --chown=user data /app/data
WORKDIR /app/backend
EXPOSE 7860
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860", "--ws-ping-interval", "20"]
