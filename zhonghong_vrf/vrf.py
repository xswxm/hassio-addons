import requests
import json
import logging
import time
from paho.mqtt import client as mqtt_client
import copy
#import argparse

#logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
logging.basicConfig(level=logging.INFO)

#'{"err":0,"unit":[
# {"oa":1,"ia":1,"nm":"","on":0,"mode":2,"alarm":0,
# "tempSet":"24","tempIn":"23","fan":1,"idx":0,"grp":0,"OnoffLock":0,
# "tempLock":0,"highestVal":26,"lowestVal":26,"modeLock":0,
# "FlowDirection1":0,"FlowDirection2":0,"MainRmc":0},
# {"oa":1,"ia":2,"nm":"","on":0,"mode":1,"alarm":0,"tempSet":"20","tempIn":"23","fan":1,"idx":1,"grp":0,"OnoffLock":0,"tempLock":0,"highestVal":26,"lowestVal":26,"modeLock":0,"FlowDirection1":0,"FlowDirection2":0,"MainRmc":0},{"oa":1,"ia":3,"nm":"","on":0,"mode":1,"alarm":0,"tempSet":"25","tempIn":"23","fan":1,"idx":2,"grp":0,"OnoffLock":0,"tempLock":0,"highestVal":26,"lowestVal":26,"modeLock":0,"FlowDirection1":0,"FlowDirection2":0,"MainRmc":0},{"oa":1,"ia":4,"nm":"","on":0,"mode":8,"alarm":0,"tempSet":"26","tempIn":"23","fan":1,"idx":3,"grp":0,"OnoffLock":0,"tempLock":0,"highestVal":26,"lowestVal":26,"modeLock":0,"FlowDirection1":0,"FlowDirection2":0,"MainRmc":0},{"oa":1,"ia":5,"nm":"","on":1,"mode":8,"alarm":0,"tempSet":"27","tempIn":"37","fan":4,"idx":4,"grp":0,"OnoffLock":0,"tempLock":0,"highestVal":27,"lowestVal":27,"modeLock":0,"FlowDirection1":0,"FlowDirection2":0,"MainRmc":0}]}'

acs = None
CONFIG = {}
STATES = {'on':{0:'OFF', 1:'ON','OFF':0,'ON':1},
    'mode':{0:'off',1:'cool',2:'dry',4:'fan_only',8:'heat','off':0,'cool':1,'dry':2,'fan_only':4,'heat':8},
    'fan':{0:'auto',1:'high',2:'medium',4:'low',6:'silent','auto':0,'high':1,'medium':2,'low':4,'silent':8}}

def get_config():
    config = {}
    CONFIG_PATH = "/data/options.json"
    with open(CONFIG_PATH) as fp:
        config = json.load(fp)
    logging.info(" {0}: Config loaded: {1}".format(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())), config))
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
        logging.info(" {0}: Received `{1}` from `{2}` topic".format(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())), msg.payload.decode(), msg.topic))
        oi = msg.topic.split('/')[3].split('_')

        ac_temp = {}
        oa = int(oi[1])
        ia = int(oi[2])
        global acs
        for ac in acs:
            if ac['oa'] == oa and ac['ia'] == ia:
                ac_temp = copy.deepcopy(ac)
                break
        
        if msg.topic.split('/')[-2] == 'temp':
            ac_temp['tempSet'] = int(float(msg.payload.decode()))
        else:
            global STATES
            ac_temp[msg.topic.split('/')[-2]] = STATES[msg.topic.split('/')[-2]][msg.payload.decode()]
        if msg.topic.split('/')[-2] == 'mode' and msg.payload.decode() == 'off':
            ac_temp['on'] = 0
        else:
            ac_temp['on'] = 1
        set_ac(ac_temp)

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
def get_acs():
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
def set_ac(ac):
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

def print_instructions(acs):
    str_acs = "\n注意: 如果首次使用home assistant发现不了设备，请将以下配置手动添加到configuration.yaml中，并重启home assistant。\n"
    str_acs += "---------------------------------------------START---------------------------------------------\n"
    str_acs += "climate:\n"
    for ac in acs:
        str_acs += get_configuration(ac)
    str_acs += "---------------------------------------------E N D---------------------------------------------"
    logging.info(str_acs)

def get_configuration(ac):
    str_ac = "  - platform: mqtt\n"
    str_ac += "    name: zhonghong_hvac_{0}_{1}\n".format(ac['oa'], ac['ia'])
    str_ac += '\
    modes:\n\
      - "heat"\n\
      - "cool"\n\
      - "dry"\n\
      - "fan_only"\n\
      - "off"\n\
    fan_modes:\n\
      - "auto"\n\
      - "low"\n\
      - "medium"\n\
      - "high"\n\
      - "silent"\n'
    str_ac += '    power_command_topic: "homeassistant/climate/zhonghong/ac_{0}_{1}/on/set"\n'.format(ac['oa'], ac['ia'])
    str_ac += '    mode_command_topic: "homeassistant/climate/zhonghong/ac_{0}_{1}/mode/set"\n'.format(ac['oa'], ac['ia'])
    str_ac += '    temperature_command_topic: "homeassistant/climate/zhonghong/ac_{0}_{1}/temp/set"\n'.format(ac['oa'], ac['ia'])
    str_ac += '    fan_mode_command_topic: "homeassistant/climate/zhonghong/ac_{0}_{1}/fan/set"\n'.format(ac['oa'], ac['ia'])
    str_ac += '    mode_state_topic: "homeassistant/climate/zhonghong/ac_{0}_{1}/mode/state"\n'.format(ac['oa'], ac['ia'])
    str_ac += '    temperature_state_topic: "homeassistant/climate/zhonghong/ac_{0}_{1}/temp/state"\n'.format(ac['oa'], ac['ia'])
    str_ac += '    current_temperature_topic: "homeassistant/climate/zhonghong/ac_{0}_{1}/cur_temp/state"\n'.format(ac['oa'], ac['ia'])
    str_ac += '    fan_mode_state_topic: "homeassistant/climate/zhonghong/ac_{0}_{1}/fan/state"\n'.format(ac['oa'], ac['ia'])
    str_ac += '    precision: 1.0\n'
    return str_ac

def sync_acs(client):
    global acs, STATES
    acs_temp = get_acs()

    if acs == None:   # setup ac_list if it is empty
        acs = copy.deepcopy(acs_temp)
        print_instructions(acs)
        for ac in acs:
            # Subscribe
            client.subscribe("homeassistant/climate/zhonghong/ac_{0}_{1}/{2}/set".format(ac['oa'], ac['ia'], 'on'))
            client.subscribe("homeassistant/climate/zhonghong/ac_{0}_{1}/{2}/set".format(ac['oa'], ac['ia'], 'mode'))
            client.subscribe("homeassistant/climate/zhonghong/ac_{0}_{1}/{2}/set".format(ac['oa'], ac['ia'], 'temp'))
            client.subscribe("homeassistant/climate/zhonghong/ac_{0}_{1}/{2}/set".format(ac['oa'], ac['ia'], 'fan'))
            # Publish
            # client.publish("homeassistant/climate/zhonghong/ac_{0}_{1}/{2}/set".format(ac['oa'], ac['ia'], 'on'), STATES['on'][ac['on']])
            if ac['on'] == 1:
                client.publish("homeassistant/climate/zhonghong/ac_{0}_{1}/{2}/state".format(ac['oa'], ac['ia'], 'mode'), STATES['mode'][ac['mode']])
            else:
                client.publish("homeassistant/climate/zhonghong/ac_{0}_{1}/{2}/state".format(ac['oa'], ac['ia'], 'mode'), STATES['mode'][0])
            client.publish("homeassistant/climate/zhonghong/ac_{0}_{1}/{2}/state".format(ac['oa'], ac['ia'], 'temp'), ac['tempSet'])
            client.publish("homeassistant/climate/zhonghong/ac_{0}_{1}/{2}/state".format(ac['oa'], ac['ia'], 'cur_temp'), ac['tempIn'])
    else:
        for ac_temp in acs_temp:
            for ac in acs:
                if ac['oa'] == ac_temp['oa'] and ac['ia'] == ac_temp['ia']:
                    if ac['on'] != ac_temp['on'] or ac['mode'] != ac_temp['mode']:
                        logging.info(" {0}: Publish on: {1}".format(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())), STATES['on'][ac_temp['on']]))
                        topic = "homeassistant/climate/zhonghong/ac_{0}_{1}/{2}/state".format(ac['oa'], ac['ia'], 'mode')
                        msg = STATES['mode'][ac_temp['mode']]
                        if ac_temp['on'] == 0:
                            msg = STATES['mode'][0]
                        publish(client, topic, msg)
                    if ac['tempSet'] != ac_temp['tempSet']:
                        topic = "homeassistant/climate/zhonghong/ac_{0}_{1}/{2}/state".format(ac['oa'], ac['ia'], 'temp')
                        msg = ac_temp['tempSet']
                        publish(client, topic, msg)
                    if ac['tempIn'] != ac_temp['tempIn']:
                        topic = "homeassistant/climate/zhonghong/ac_{0}_{1}/{2}/state".format(ac['oa'], ac['ia'], 'cur_temp')
                        msg = ac_temp['tempIn']
                        publish(client, topic, msg)
                    if ac['fan'] != ac_temp['fan']:
                        topic = "homeassistant/climate/zhonghong/ac_{0}_{1}/{2}/state".format(ac['oa'], ac['ia'], 'fan')
                        msg = STATES['fan'][ac_temp['fan']]
                        publish(client, topic, msg)
                    break
        # update acs
        acs = copy.deepcopy(acs_temp)

if __name__ == '__main__':
    CONFIG = get_config()
    client = connect_mqtt()
    subscribe(client)
    client.loop_start()
    while True:
        sync_acs(client)
        time.sleep(1)