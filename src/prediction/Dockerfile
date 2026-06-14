FROM python:3.12-slim

WORKDIR /app

COPY src/prediction/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app 

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

CMD ["bash"]