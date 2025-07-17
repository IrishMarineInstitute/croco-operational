FROM python:3.11

RUN apt-get update && apt-get -y install cron vim

RUN mkdir /log

WORKDIR /root

COPY crontab /etc/cron.d/crontab
RUN chmod 0644 /etc/cron.d/crontab
RUN /usr/bin/crontab /etc/cron.d/crontab

COPY [ "*.py", "/root/" ]
COPY config .

RUN echo $PYTHONPATH

CMD ["cron", "-f"]
