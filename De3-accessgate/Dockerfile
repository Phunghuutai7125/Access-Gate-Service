FROM python:3.12-slim

WORKDIR /app

# Cài curl để HEALTHCHECK kiểm tra trạng thái
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Cài dependency
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code và static files
COPY main.py .
COPY static/ ./static/
COPY data/ ./data/

# Tạo user non-root để chạy an toàn
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

ENV PORT=8000
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
