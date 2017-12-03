FROM alpine:3.3

RUN \
    apk --no-cache add py-pip py-dateutil && \
    pip install --upgrade pip && \
    pip install telepot elasticsearch==2.2.0

ENV TOKEN
ENV ELASTIC
ENV ES_INDEX
ENV GROUPID
ENV ADMIN

COPY telegram.py /

CMD ["/telegram.py"]
