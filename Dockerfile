FROM ubuntu

# Install required packages
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get -y --no-install-recommends install cron curl python3 ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && which cron \
    && rm -rf /etc/cron.*/*

# Kopiere das lokale Python-Skript in den Container
COPY DataCollection /DataCollection

COPY crontab /hello-cron
COPY entrypoint.sh /entrypoint.sh

RUN crontab /hello-cron
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

CMD ["cron", "-f", "-L", "2"]

