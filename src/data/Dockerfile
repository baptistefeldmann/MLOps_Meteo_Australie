FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY src/data/requirements.txt /tmp/requirements.txt
RUN uv pip install --system -r /tmp/requirements.txt

COPY . /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

CMD ["python", "src/data/collect_main.py"]