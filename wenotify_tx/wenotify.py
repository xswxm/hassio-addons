#!/usr/bin/env python
# -*- coding: utf-8 -*-

import http.client, urllib
import time
import requests
import json
import logging

logging.basicConfig(level=logging.INFO)

CONFIG = {}

def get_config():
    config = {}
    CONFIG_PATH = "/data/options.json"
    with open(CONFIG_PATH) as fp:
        config = json.load(fp)
    logging.info(" {0}: Config loaded: {1}".format(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())), config))
    return config

def getQinghua():
    conn = http.client.HTTPSConnection('api.tianapi.com')  #接口域名
    params = urllib.parse.urlencode({'key':CONFIG['key']})
    headers = {'Content-type':'application/x-www-form-urlencoded'}
    conn.request('POST','/'+ CONFIG['api']  +'/index',params,headers)
    res = conn.getresponse()
    return json.loads(res.read().decode('utf-8'))

def updateQinghua():
    data = getQinghua()
    if data['code'] == 200:
        return data['newslist'][0]['content']
    elif is_between_time(): # 如还在12:00 内吗，等待10s再获取一次
        time.sleep(10)
        updateQinghua()

# 定时12:00~12:01之间发一次消息
def is_between_time():
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    t = now[0:11] + CONFIG['push_time']
    t1 = time.strptime(t, "%Y-%m-%d %H:%M:%S")
    t2 = time.mktime(t1)
    if t2 <= time.time() <= t2 + 60:
        return True
    else:
        return False

# 微信消息提醒模块
class WeWorkNotify():
    def __init__(self, corpid, corpsecret, agentId, touser, http_proxy, https_proxy):
        self._corpid = corpid
        self._corpsecret = corpsecret
        self._agentid = agentId
        self._touser = touser
        self._proxies = { "http": http_proxy, 'https': https_proxy } 
        self._token = ""
        self._token_expire_time = 0
        self._header = {}

    def _get_access_token(self):
        url = 'https://qyapi.weixin.qq.com/cgi-bin/gettoken'
        values = {
            "corpid": self._corpid,
            "corpsecret": self._corpsecret,
        }
        req = requests.post(url, params=values, headers=self._header, proxies=self._proxies)
        data = json.loads(req.text)
        if data["errcode"] != 0:
            logging.info(" {0}: 获取企业微信 Access token 失败 `{1}`".format(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())), data))
        self._token_expire_time = time.time() + data["expires_in"]
        return data["access_token"]

    def get_access_token(self):
        if time.time() < self._token_expire_time:
            return self._token
        else:
            self._token = self._get_access_token()
            return self._token

    def send_msg(self, message):
        send_url = 'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token=' + self.get_access_token()
        send_values = {
            "touser": self._touser,
            "msgtype": "text",
            "agentid": self._agentid,
            "text": {
                "content": message
                },
            "safe": "0"
            }
        send_msges=(bytes(json.dumps(send_values), 'utf-8'))
        response = requests.post(send_url, send_msges, proxies=self._proxies).json()
        if response["errcode"] != 0:
            logging.info(" {0}: 发送消息失败 `{1}`".format(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())), response))
        else:
            logging.info(" {0}: 发送消息成功 `{1}`".format(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())), send_msges))


if __name__ == '__main__':    
    CONFIG = get_config()
    wx = WeWorkNotify(CONFIG['corpid'], CONFIG['corpsecret'], CONFIG['agentid'], CONFIG['touser'], CONFIG['http_proxy'], CONFIG['https_proxy'])

    while True:
        if is_between_time():
            try:
                qinghua = updateQinghua()
                wx.send_msg(qinghua)
            except Exception as e:
                logging.info(" {0}: Exception `{1}`".format(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())), e))
        # 每一分钟检测一次，防止cpu过载
        time.sleep(60)
