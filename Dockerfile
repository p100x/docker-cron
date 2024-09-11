FROM ubuntu

# Installiere Python und notwendige Pakete
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get -y --no-install-recommends install cron curl python3 python3-venv python3-pip ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && which cron \
    && rm -rf /etc/cron.*/*

# Erstelle eine virtuelle Umgebung
RUN python3 -m venv /opt/venv

# Aktiviere die virtuelle Umgebung und installiere Abhängigkeiten
COPY requirements.txt .
RUN /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install -r requirements.txt

# Kopiere das Python-Skript in den Container
COPY DataCollection /DataCollection

# Kopiere crontab und entrypoint
COPY crontab /hello-cron
COPY entrypoint.sh /entrypoint.sh

# Mache entrypoint ausführbar
RUN crontab /hello-cron
RUN chmod +x /entrypoint.sh

# Setze den Standard-Python für den Cronjob auf die virtuelle Umgebung
ENV PATH="/opt/venv/bin:$PATH"

ENTRYPOINT ["/entrypoint.sh"]

CMD ["cron", "-f", "-L", "2"]

