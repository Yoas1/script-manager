FROM python:3.9

WORKDIR /app

ENV TZ=Asia/Jerusalem

COPY ./ ./

RUN pip install -r requirements.txt && \
    apt-get install -yq tzdata && \
    ln -fs /usr/share/zoneinfo/$TZ /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata

ENTRYPOINT ["./run.sh"]
