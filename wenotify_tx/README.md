# Home Assistant Add-on: wenotify_tx

## 关于

[wenotify_tx](https://github.com/xswxm/hassio-addons/blob/main/wenotify_tx/README.md)是一个基于[天行数据](https://www.tianapi.com/) API的企业微信消息推送工具，可以实现每日情话、心灵鸡汤等等推送。

## 版本更新
0.0.5:
- 首版发布

## 配置

#### Option `api`

接口名称，如果接口地址为 "https://apis.tianapi.com/pcterm/index " ，则此处为"pcterm"

#### Option `key`

你的key

#### Option `push_time`

每日推送时间，如"12:00:00"，则每日中午12点推送消息

#### Option `corpid`

企业微信corpid

#### Option `corpsecret`

企业微信corpsecret

#### Option `agentid`

企业微信agentid

#### Option `touser`

发送对象，"@all" 则为所有对象

#### Option `http_proxy`

HTTP代理服务器地址，防止路由器ip变更重复添加企业微信应用的ip白名单

#### Option `https_proxy`

HTTPS代理服务器地址，防止路由器ip变更重复添加企业微信应用的ip白名单
