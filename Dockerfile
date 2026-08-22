FROM python:3.11-slim

WORKDIR /app

# Install build dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential git curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency manifests first for better caching
COPY pyproject.toml requirements.txt /app/

RUN python -m pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy application code
COPY . /app

ENV PORT=8000

EXPOSE 8000

CMD ["uvicorn", "web_app:app", "--host", "0.0.0.0", "--port", "8000"]
