FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /worker
RUN apt-get update && apt-get install -y --no-install-recommends bash curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /worker/requirements.txt
RUN pip install --no-cache-dir -r /worker/requirements.txt
COPY tasks_dft.py /worker/tasks_dft.py
CMD ["celery", "-A", "tasks_dft.celery_app", "worker", "--loglevel=info", "-Q", "heavy_dft"]
