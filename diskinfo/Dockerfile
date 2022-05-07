FROM python:3.7-alpine

RUN mkdir /data
#WORKDIR /data

ADD diskinfo.py /
#ADD options.json /data

RUN apk update
RUN apk add smartmontools
RUN pip3 install requests paho-mqtt

CMD ["python3","./diskinfo.py"]