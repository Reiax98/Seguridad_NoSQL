FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY migrate_users.py .

EXPOSE 8443

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8443", "--ssl-certfile", "/certs/api.crt", "--ssl-keyfile", "/certs/api.key"]
