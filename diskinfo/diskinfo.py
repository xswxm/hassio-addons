import os
import json
import logging
import time
from paho.mqtt import client as mqtt_client

logging.basicConfig(level=logging.INFO)

CONFIG = {}

def get_config():
    config = {}
    CONFIG_PATH = "/data/options.json"
    with open(CONFIG_PATH) as fp:
        config = json.load(fp)
    f = os.popen("ls /dev/|grep sd")
    config['disks'] = f.readlines()
    logging.info (" {0}: Config loaded: {1}".format(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())), config))
    return config

def connect_mqtt() -> mqtt_client:
    global CONFIG
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            logging.info(" {0}: Connected to MQTT Broker!".format(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))))
        else:
            logging.info(" {0}: Failed to connect, return code {1}\n".format(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))), rc)
    client_id = time.strftime('%Y%m%d%H%M%S',time.localtime(time.time()))
    client = mqtt_client.Client(client_id)
    client.username_pw_set(username=CONFIG['username'], password=CONFIG['password'])
    client.on_connect = on_connect
    client.connect(CONFIG['broker'], int(CONFIG['port']))
    return client

# subscribe mqtt topic and receive msg
def subscribe(client: mqtt_client):
    def on_message(client, userdata, msg):
        logging.info(" {0}: Received `{0}` from `{1}` topic".format(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))), msg.payload.decode(), msg.topic)

    client.on_message = on_message

def publish(client, topic, msg):
    result = client.publish(topic, msg)
    status = result[0]
    if status == 0:
        logging.info(" {0}: Publish `{1} to `{2}` topic".format(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())), msg, topic))
    else:
        logging.info(" {0}: Failed to send message to topic {1}".format(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())), topic))

def sync_disks(client):
    global CONFIG
    for disk in CONFIG['disks']:
        disk = disk.replace('\n','')
        f = os.popen("smartctl -a /dev/" + disk)
        diskinfo = {}
        for line in f.readlines():
            if line[:49] == "SMART overall-health self-assessment test result:":
                diskinfo['health'] = line[50:].split()[0]
            if line[:27] == "190 Airflow_Temperature_Cel":
                diskinfo['temperature'] = int(line[87:].split()[0])
                break
        publish(client, "homeassistant/diskinfo/{0}".format(disk), json.dumps(diskinfo))

if __name__ == '__main__':
    print("注意：请根据自己的硬盘情况将sda替换为自己硬盘符，按实将以下示例添加到configuration.yaml文件中，有几个硬盘添加几遍。")
    print('\
  - platform: mqtt \n\
    name: "sda health"\n\
    state_topic: "homeassistant/diskinfo/sda"\n\
    value_template: "{{ value_json.health }}"\n\
  - platform: mqtt\n\
    name: "sda temperature"\n\
    state_topic: "homeassistant/diskinfo/sda"\n\
    unit_of_measurement: "℃"\n\
    value_template: "{{ value_json.temperature }}"')
    CONFIG = get_config()
    client = connect_mqtt()
    subscribe(client)
    client.loop_start()
    while True:
        sync_disks(client)
        time.sleep(CONFIG['interval'])
