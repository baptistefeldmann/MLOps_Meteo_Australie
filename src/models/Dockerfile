FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY src/models/requirements.txt /tmp/requirements.txt
RUN uv pip install --system -r /tmp/requirements.txt

COPY . /app

ENV PYTHONUNBUFFERED=1

CMD ["bash"]