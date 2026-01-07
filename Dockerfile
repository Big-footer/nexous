# Dockerfile
FROM python:3.11-slim

# ---- system deps (필요 최소) ----
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# ---- workdir ----
WORKDIR /app

# ---- python deps ----
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- app ----
COPY . .

# ---- non-root ----
RUN useradd -m nexous
USER nexous

# ---- default entry ----
ENTRYPOINT ["python", "-m", "nexous.cli.main"]
