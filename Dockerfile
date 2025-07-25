FROM python:3.12-slim

WORKDIR /app

# Install Promtail
RUN apt-get update && \
    apt-get install -y curl unzip gettext-base && \
    curl -L -o /tmp/promtail.zip https://github.com/grafana/loki/releases/download/v2.9.5/promtail-linux-amd64.zip && \
    unzip /tmp/promtail.zip -d /usr/local/bin && \
    mv /usr/local/bin/promtail-linux-amd64 /usr/local/bin/promtail && \
    chmod +x /usr/local/bin/promtail && \
    rm -rf /var/lib/apt/lists/* /tmp/promtail.zip

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend /app/backend
COPY pyproject.toml /app/pyproject.toml

# Copy entrypoint
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh


#RUN pip install --no-cache-dir fastapi uvicorn

COPY promtail-config.yml /etc/promtail.yml

CMD ["./docker-entrypoint.sh"]
