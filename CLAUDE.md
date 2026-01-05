# 必要文件
1. 原型设计：./CarTest_MQTT/UI/
2. 接口文档：./CarTest_MQTT/docs/API接口文档.md

# 核心规则
1. 前端按照原型开发，对接后端必须遵循接口文档。
2. 后端接口实现必须严格以接口文档为准。
3. 测试用例必须基于需求和接口文档编写。
4. 操作后，需要在各个板块的README.md中记录总结。

# 开发目录
1. 前端 ./CarTest_MQTT/frontend
2. 后端 ./CarTest_MQTT/backend
3. 测试 ./CarTest_MQTT/test

# 公共 MQTT 服务器信息

```json
Broker:broker.emqx.io

TCP 端口:1883

WebSocket 端口:8083

SSL/TLS 端口:8883

WebSocket Secure 端口:8084

QUIC 端口:14567

CA 证书文件:broker.emqx.io-ca.crt
```
