FROM python:3.7-alpine

RUN apk update
RUN apk add jq
# RUN pip3 install requests paho-mqtt

RUN mkdir /data
ADD run.sh /
RUN chmod a+x /run.sh

CMD ["/run.sh"]