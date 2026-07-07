FROM python:3.12-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libavformat-dev libavcodec-dev libavdevice-dev libavutil-dev \
    libswscale-dev libswresample-dev libavfilter-dev \
    pkg-config gcc g++ python3-dev \
    libportaudio2 portaudio19-dev libasound2 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY launcher.py .
COPY server ./server
COPY web ./web

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SOUNDSHARE_CLOUD=1 \
    SOUNDSHARE_DATA_DIR=/data

RUN mkdir -p /data

EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:' + (__import__('os').environ.get('PORT', '8765')) + '/health')"

CMD ["sh", "-c", "python -m server.app --host 0.0.0.0 --port ${PORT:-8765}"]
