FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/__init__.py ./src/__init__.py
COPY src/db.py ./src/db.py
COPY src/mqtt_listener/ ./src/mqtt_listener/
COPY data/ ./data/

RUN useradd --create-home --shell /bin/bash mqttuser \
    && chown -R mqttuser:mqttuser /app
USER mqttuser

CMD ["python", "-m", "src.mqtt_listener.main"]
