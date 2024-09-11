FROM ubuntu

# Install required packages including CA certificates
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get -y --no-install-recommends install cron curl git python3 ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && which cron \
    && rm -rf /etc/cron.*/*

# Clone the repository that contains the Python script
RUN git -c http.extraHeader="Authorization: Bearer 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" clone https://github.com/p100x/100xplatform_relaunch.git /backend

COPY crontab /hello-cron
COPY entrypoint.sh /entrypoint.sh

RUN crontab /hello-cron
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

CMD ["cron", "-f", "-L", "2"]

