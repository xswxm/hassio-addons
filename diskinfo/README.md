# Home Assistant Add-on: diskinfo

## 关于

[diskinfo](https://github.com/xswxm/hassio-addons/blob/main/diskinfo/README.md)是一个基于smartctl命令的，用于监控硬盘温度和健康状态的插件。

注意：镜像测试阶段，建议手动编译镜像后，添加 --privileged 运行

docker-compose.yaml 示例
```yaml
version: "3.9"
services:
  diskinfo:
    container_name: addon_diskinfo
    privileged: true
    restart: unless-stopped
    image: [你的镜像]
    volumes:
      - ${PWD}/options.json:/data/options.json:ro
```

## configuration.yaml 配置
注意：请根据自己的硬盘情况将sda替换为自己硬盘符，按实将以下示例添加到configuration.yaml文件中，有几个硬盘添加几遍。
```yaml
  - platform: mqtt
    name: "sda health"
    state_topic: "homeassistant/diskinfo/sda"
    value_template: "{{ value_json.health }}"
  - platform: mqtt
    name: "sda temperature"
    state_topic: "homeassistant/diskinfo/sda"
    unit_of_measurement: "℃"
    value_template: "{{ value_json.temperature }}"
```

## 配置

#### Option `broker`

mqtt服务器

#### Option `port`

mqtt服务器端口

#### Option `username`

mqtt服务器用户名

#### Option `password`

mqtt服务器密码

#### Option `interval`

硬盘刷新时间间隔，int类型，默认3600秒