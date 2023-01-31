# -*- coding: utf-8 -*-

import requests
import json
import logging
import time
from paho.mqtt import client as mqtt_client

logging.basicConfig(level=logging.INFO)

STATES = {'on':{0:'OFF', 1:'ON','OFF':0,'ON':1},
    'mode':{0:'off',1:'cool',2:'dry',4:'fan_only',8:'heat','off':0,'cool':1,'dry':2,'fan_only':4,'heat':8},
    'fan':{0:'auto',1:'high',2:'medium',4:'low',6:'silent','auto':0,'high':1,'medium':2,'low':4,'silent':8}}
CONFIG = {}
acs = []

def setConfig():
    global CONFIG
    CONFIG = {}
    CONFIG['broker'] = "192.168.123.10"
    CONFIG['port'] = 1883
    CONFIG['gateway'] = "192.168.123.251"
    CONFIG['username'] = "mqtt"
    CONFIG['password'] = "mqtt"

def loadConfig(CONFIG_PATH = '/data/options.json'):
    global CONFIG
    CONFIG = {}
    with open(CONFIG_PATH) as fp:
        CONFIG = json.load(fp)
    logging.info (" {0}: Config loaded: {1}".format(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())), CONFIG))

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
        logging.info(" {0}: Received `{1}` from `{2}` topic".format(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())), msg.payload.decode(), msg.topic))

        try:
            if "homeassistant/climate/zhonghong/" in msg.topic:
                object_id = msg.topic.split('/')[3]

                idx = int(object_id.split('_')[1])
                global acs
                for i in range(len(acs)):
                    if acs[i]['idx'] == idx:
                        break
                ac = {}
                ac['idx'] = idx
                ac['on'] = acs[i]['on']
                ac['mode'] = acs[i]['mode']
                ac['tempSet'] = acs[i]['tempSet']
                ac['fan'] = acs[i]['fan']
                if msg.topic.split('/')[-2] == 'temp':
                    ac['tempSet'] = int(float(msg.payload.decode()))
                else:
                    global STATES
                    ac[msg.topic.split('/')[-2]] = STATES[msg.topic.split('/')[-2]][msg.payload.decode()]
                if msg.topic.split('/')[-2] == 'mode' and msg.payload.decode() == 'off':
                    ac['on'] = 0
                else:
                    ac['on'] = 1
                setAC(ac)

            elif msg.topic == "homeassistant/zhonghong/initialize":
                initializeClimates(client)
        except Exception as e:
            logging.info(" {0}: Exception `{1}`".format(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())), e))
    client.on_message = on_message

# publish state for an air conditioner
def publish(client, topic, msg):
    result = client.publish(topic, msg)
    status = result[0]
    if status == 0:
        logging.info(" {0}: Publish `{1} to `{2}` topic".format(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())), msg, topic))
    else:
        logging.info(" {0}: Failed to send message to topic {1}".format(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())), topic))

# get states for all air conditioners
def getACList():
    # global acs_sample
    # return acs_sample['unit']

    global CONFIG
    api = 'http://{0}/cgi-bin/api.html?f=17&p={1}'
    i = 0
    acs_temp = []
    while True:
        try:
            r = requests.get(api.format(CONFIG['gateway'],i), auth=('admin',''), proxies = {'http': None, 'https': None})
            msg = json.loads(r.text)
            if msg['err'] == 0 and len(msg['unit']) > 0:
                for m in msg['unit']:
                    acs_temp.append(m)
            else:
                break
        except Exception as e: 
            r = str(e)
            if "('Connection aborted.', BadStatusLine('" in r:
                msg = json.loads(r[39:-3])
                if msg['err'] == 0 and len(msg['unit']) > 0:
                    for m in msg['unit']:
                        acs_temp.append(m)
                else:
                    break
        i = i + 1
    return acs_temp

# set values for a air conditioner
def setAC(ac):
    global CONFIG
    api = "http://{0}/cgi-bin/api.html?f=18&idx={1}&on={2}&mode={3}&tempSet={4}&fan={5}".format(CONFIG['gateway'], ac['idx'], ac['on'], ac['mode'], ac['tempSet'], ac['fan'])
    logging.info(" {0}: Set: {1}".format(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())), api))
    try:
        r = requests.get(api, auth=('admin',''), proxies = {'http': None, 'https': None})
    except Exception as e:
        msg = str(e)
        if "('Connection aborted.', BadStatusLine('" in msg:
            msg = ''
        else:
            msg = ''

def initializeClimates(client, node_id = "zhonghong", component = "climate", discovery_prefix = "homeassistant"):
    global acs
    acs = getACList()
    for ac in acs:
        object_id = "ac_{0}".format(ac['idx'])
        # Create Climate
        # removeClimate(object_id)
        createClimate(object_id)

        # Update Values
        topic = "{0}/{1}/{2}/{3}/{4}/state".format(discovery_prefix, component, node_id, object_id, 'mode')
        msg = STATES['mode'][0]  if ac['on'] == 0 else STATES['mode'][ac['mode']]
        publish(client, topic, msg)
        topic = "{0}/{1}/{2}/{3}/{4}/state".format(discovery_prefix, component, node_id, object_id, 'temp')
        msg = int(ac['tempSet'])  
        publish(client, topic, msg)
        topic = "{0}/{1}/{2}/{3}/{4}/state".format(discovery_prefix, component, node_id, object_id, 'cur_temp')
        msg = int(ac['tempIn'])
        publish(client, topic, msg)
        topic = "{0}/{1}/{2}/{3}/{4}/state".format(discovery_prefix, component, node_id, object_id, 'fan')
        msg = STATES['fan'][ac['fan']]
        publish(client, topic, msg)

def createClimate(object_id, name = None, device_class = None, icon = None, temperature_unit = "C", node_id = "zhonghong", component = "climate", discovery_prefix = "homeassistant"):
    device = {}
    device["identifiers"] = ["ZhongHong VRF"]
    device["name"] = "ZhongHong VRF"
    device["manufacturer"] = "xswxm"
    device["model"] = "V100"
    device["sw_version"] = "0.3.0"
    
    topic = "{0}/{1}/{2}/{3}/config".format(discovery_prefix, component, node_id, object_id)

    payload = {}
    payload["device"] = device
    payload["temp_unit"] = temperature_unit
    payload["force_update"] = True

    payload["unique_id"] = "{0}_{1}".format(node_id, object_id)
    payload["object_id"] = "{0}_{1}".format(node_id, object_id)
    if icon != None:
        payload["icon"] = icon
    if device_class != None:
        payload["device_class"] = device_class
    payload["name"] = "zhonghong_{0}".format(object_id)
    payload["modes"] = [
		"heat",
		"cool",
		"dry",
		"fan_only",
		"off"
	]
    payload["fan_modes"] = [
		"low",
		"medium",
		"high"
	]
    # payload["min_temp"] = 16.0
    payload["max_temp"] = 29.0
    payload["power_command_topic"] = "{0}/{1}/{2}/{3}/{4}/set".format(discovery_prefix, component, node_id, object_id, 'on')
    payload["mode_command_topic"] = "{0}/{1}/{2}/{3}/{4}/set".format(discovery_prefix, component, node_id, object_id, 'mode')
    payload["temperature_command_topic"] = "{0}/{1}/{2}/{3}/{4}/set".format(discovery_prefix, component, node_id, object_id, 'temp')
    payload["fan_mode_command_topic"] = "{0}/{1}/{2}/{3}/{4}/set".format(discovery_prefix, component, node_id, object_id, 'fan')

    payload["mode_state_topic"] = "{0}/{1}/{2}/{3}/{4}/state".format(discovery_prefix, component, node_id, object_id, 'mode')
    payload["temperature_state_topic"] = "{0}/{1}/{2}/{3}/{4}/state".format(discovery_prefix, component, node_id, object_id, 'temp')
    payload["current_temperature_topic"] = "{0}/{1}/{2}/{3}/{4}/state".format(discovery_prefix, component, node_id, object_id, 'cur_temp')
    payload["fan_mode_state_topic"] = "{0}/{1}/{2}/{3}/{4}/state".format(discovery_prefix, component, node_id, object_id, 'fan')
    payload["temp_step"] = 1.0
    publish(client, topic, json.dumps(payload))
    client.subscribe("{0}/{1}/{2}/{3}/{4}/set".format(discovery_prefix, component, node_id, object_id, 'on'))
    client.subscribe("{0}/{1}/{2}/{3}/{4}/set".format(discovery_prefix, component, node_id, object_id, 'mode'))
    client.subscribe("{0}/{1}/{2}/{3}/{4}/set".format(discovery_prefix, component, node_id, object_id, 'temp'))
    client.subscribe("{0}/{1}/{2}/{3}/{4}/set".format(discovery_prefix, component, node_id, object_id, 'fan'))

def removeClimate(object_id, node_id = "zhonghong", component = "climate", discovery_prefix = "homeassistant"):
    topic = "{0}/{1}/{2}/{3}/config".format(discovery_prefix, component, node_id, object_id)
    publish(client, topic, json.dumps(''))

def syncACList(client, node_id = "zhonghong", component = "climate", discovery_prefix = "homeassistant"):
    global STATES, acs
    acs_temp = getACList()
    
    for i in range(len(acs)):
        object_id = "ac_{0}".format(acs[i]['idx'])
        if acs[i]['on'] != acs_temp[i]['on'] or acs[i]['mode'] != acs_temp[i]['mode']:
            acs[i]['on'] = acs_temp[i]['on']
            acs[i]['mode'] = acs_temp[i]['mode']
            topic = "{0}/{1}/{2}/{3}/{4}/state".format(discovery_prefix, component, node_id, object_id, 'mode')
            msg = STATES['mode'][0]  if acs[i]['on'] == 0 else STATES['mode'][acs[i]['mode']]
            publish(client, topic, msg)
        if acs[i]['tempSet'] != acs_temp[i]['tempSet']:
            acs[i]['tempSet'] = acs_temp[i]['tempSet']
            topic = "{0}/{1}/{2}/{3}/{4}/state".format(discovery_prefix, component, node_id, object_id, 'temp')
            msg = int(acs[i]['tempSet'])  
            publish(client, topic, msg)
        if acs[i]['tempIn'] != acs_temp[i]['tempIn']:
            acs[i]['tempIn'] = acs_temp[i]['tempIn']
            topic = "{0}/{1}/{2}/{3}/{4}/state".format(discovery_prefix, component, node_id, object_id, 'cur_temp')
            msg = int(acs[i]['tempIn'])
            publish(client, topic, msg)
        if acs[i]['fan'] != acs_temp[i]['fan']:
            acs[i]['fan'] = acs_temp[i]['fan']
            topic = "{0}/{1}/{2}/{3}/{4}/state".format(discovery_prefix, component, node_id, object_id, 'fan')
            msg = STATES['fan'][acs[i]['fan']]
            publish(client, topic, msg)

if __name__ == '__main__':
    # setConfig()
    loadConfig()
    client = connect_mqtt()
    subscribe(client)
    client.subscribe("homeassistant/zhonghong/initialize")
    client.loop_start()

    count = 2
    while count > 0:
        initializeClimates(client)
        time.sleep(1)
        count = count - 1
    
    while True:
        syncACList(client)
        time.sleep(1)