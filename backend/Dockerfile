FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv
WORKDIR /app/backend
COPY pyproject.toml ./
RUN uv sync --no-dev
COPY . .
ENV HAATHI_DATA_DIR=/app/data
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
