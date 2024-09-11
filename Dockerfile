FROM ubuntu

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get -y --no-install-recommends install cron curl python3 \
    && rm -rf /var/lib/apt/lists/* \
    && which cron \
    && rm -rf /etc/cron.*/*

COPY crontab /hello-cron
COPY entrypoint.sh /entrypoint.sh

# Copy the backend folder into the Docker image
COPY backend /backend

RUN crontab /hello-cron
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

CMD ["cron", "-f", "-L", "2"]
