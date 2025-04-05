FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y default-mysql-client netcat-traditional

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"] 