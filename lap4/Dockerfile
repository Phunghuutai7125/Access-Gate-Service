FROM python:3.12-slim

WORKDIR /app

# Cài curl để HEALTHCHECK dùng được
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Cài dependency trước để tận dụng layer cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Tạo user non-root và chuyển quyền sở hữu
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

ENV PORT=8000
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "src.access_gate.main:app", "--host", "0.0.0.0", "--port", "8000"]
