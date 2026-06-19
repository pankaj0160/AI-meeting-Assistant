FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    curl \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.docker.txt .

# Use CPU-optimized requirements for Docker
RUN pip install --no-cache-dir -r requirements.docker.txt

COPY . .

RUN mkdir -p uploads/audio uploads/video uploads/transcripts chroma_db

EXPOSE 8000

CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]