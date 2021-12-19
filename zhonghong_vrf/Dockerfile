FROM ubuntu:20.04

RUN mkdir /data
#WORKDIR /data

ADD vrf.py /
#ADD options.json /data
ADD sources.list /etc/apt/

RUN apt-get update
RUN apt-get install -y python3 python3-pip
RUN pip3 install requests paho-mqtt

RUN apt-get autoremove -y python3-pip
RUN apt-get clean

CMD ["python3","./vrf.py"]