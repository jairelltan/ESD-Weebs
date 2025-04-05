FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y default-mysql-client netcat-traditional curl && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy SQL initialization scripts for initial setup
COPY databases/combined.txt /docker-entrypoint-initdb.d/init.sql

# Environment variables for database connection (will be set in docker-compose.yml)
ENV MYSQL_HOST=db
ENV MYSQL_USER=root
ENV MYSQL_PASSWORD=root_password
ENV MYSQL_PORT=3306

# Expose ports for all microservices (will be managed by Docker Compose)
EXPOSE 5000-5025

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:5000/ || exit 1

# Entry point script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["docker-entrypoint.sh"] 