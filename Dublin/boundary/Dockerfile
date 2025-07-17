FROM python:3.12

RUN apt-get update && apt-get -y install cron vim

RUN mkdir /log

WORKDIR /root

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY crontab /etc/cron.d/crontab
RUN chmod 0644 /etc/cron.d/crontab
RUN /usr/bin/crontab /etc/cron.d/crontab

COPY [ "*.py", "/root/" ]
COPY [ "*.nc", "/root/" ]
COPY config .

RUN echo $PYTHONPATH

CMD ["cron", "-f"]
