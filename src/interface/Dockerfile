FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY src/interface/requirements.txt /tmp/requirements.txt
RUN uv pip install --system -r /tmp/requirements.txt

COPY . /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

CMD ["streamlit", "run", "src/interface/app.py", "--server.address=0.0.0.0", "--server.port=8501"]