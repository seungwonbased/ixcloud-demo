FROM ubuntu:20.04

WORKDIR /dummy

COPY . /dummy

RUN sed -i 's/archive.ubuntu.com/kr.archive.ubuntu.com/g' /etc/apt/sources.list
RUN apt-get update -y
RUN apt-get install -y libpq-dev
RUN apt-get install -y python3-dev
RUN apt-get install -y python3
RUN apt-get install -y python3-pip

RUN pip install wheel
RUN pip install -r ./requirements.txt

ENV FLASK_APP=app
ENV FLASK_DEBUG=true
ENV APP_CONFIG_FILE=/dummy/config/config.py
ENV DB_USER=postgres
ENV DB_PASSWORD=password
ENV DB_HOST=1.201.172.251
ENV DB_PORT=5432
ENV DB_NAME=dummy

RUN chmod +x ./app.sh

CMD ./app.sh