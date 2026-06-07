# Vention libraries require Python >=3.10,<3.11, so we pin 3.10.
FROM python:3.10-slim

# graphviz provides the `dot` binary that the state-machine router uses to
# render GET /sm/diagram.svg.
RUN apt-get update \
    && apt-get install -y --no-install-recommends graphviz \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install dependencies first so the layer caches across code changes.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code (uvicorn runs with cwd=/app, so `main:app` and
# `from app...` imports resolve here).
COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
