FROM python:3.7-alpine

RUN mkdir /data
#WORKDIR /data

ADD wenotify.py /
# ADD options.json /data

RUN apk update
RUN pip3 install requests

CMD ["python3","./wenotify.py"]