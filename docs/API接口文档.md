# CarTest MQTT 后端接口文档

文档版本：v1.0
适用范围：CarTest MQTT 车载环境传感器测试系统前后端开发协作
最后更新时间：2026-01-04

# 一、系统概述

CarTest MQTT系统是一款专注于车载环境传感器（以DHT11温湿度传感器为核心）的测试平台，通过MQTT协议实现传感器数据的采集与传输，提供传感器配置、MQTT连接管理、测试用例执行、测试结果与原始数据查询等核心功能。本接口文档定义了前端与后端之间的所有HTTP/RESTful接口规范，明确了接口路径、请求方法、参数格式、响应数据及错误码，为前后端开发提供统一协作依据。

核心业务流程：
1. 系统初始化与状态监控
2. 传感器配置（模拟/真实模式切换、参数设置）
3. MQTT Broker连接配置与测试
4. 测试用例管理与执行
5. 实时/历史测试结果查询与导出
6. 原始传感器数据查询与导出

# 二、接口规范

## 2.1 基础信息

- 基础URL：`/api/v1`（所有接口均基于此前缀）

- 数据交互格式：JSON（请求头需指定`Content-Type: application/json`）

- 时间格式：ISO 8601 标准（示例：2026-01-04T10:35:22+08:00）

- 字符编码：UTF-8

## 2.2 响应格式规范

所有接口的响应数据均遵循统一格式，包含状态码、描述信息和业务数据（无业务数据时为空对象）：

```json

{
  "code": 200,          // 状态码：200表示成功，非200表示异常
  "message": "success", // 状态描述：成功时为"success"，异常时为具体错误信息
  "data": {}            // 业务数据：根据接口功能返回对应数据，无数据时返回空对象
}
```

## 2.3 请求方法定义

|请求方法|适用场景|
|---|---|
|GET|查询资源（如获取系统状态、传感器列表、配置信息等）|
|POST|创建资源或执行操作（如添加传感器、开始测试、测试MQTT连接等）|
|PUT|更新资源（如修改传感器配置、MQTT配置、传感器状态等）|
|DELETE|删除资源（如删除传感器）|
## 2.4 分页参数规范

所有分页查询接口（如历史测试结果、原始传感器数据查询）均统一使用以下分页参数：

|参数名|类型|必填|默认值|描述|
|---|---|---|---|---|
|page|int|否|1|页码|
|pageSize|int|否|10|每页条数（最大值不超过100）|
分页查询接口的响应数据中，`data` 字段包含以下统一结构：

```json

{
  "total": 156,         // 总记录数
  "page": 1,            // 当前页码
  "pageSize": 10,       // 每页条数
  "items": []           // 当前页数据列表
}
```

# 三、核心接口详情

## 3.1 系统状态接口

### 3.1.1 获取系统整体状态

- 接口路径：`/system/status`

- 请求方法：GET

- 描述：获取系统运行状态、已连接传感器数量、测试通过率、今日测试总数及MQTT连接状态

- 请求参数：无

- 响应数据示例：

```json

{
  "code": 200,
  "message": "success",
  "data": {
    "systemStatus": "online",          // 系统状态：online-在线，offline-离线
    "connectedSensors": 3,             // 已连接传感器数量
    "testPassRate": 87,                // 测试通过率（百分比）
    "todayTestCount": 156,             // 今日测试总数
    "mqttConnectionStatus": "connected"// MQTT连接状态：connected-已连接，disconnected-未连接
  }
}
```

## 3.2 传感器管理接口

### 3.2.1 获取传感器列表

- 接口路径：`/sensors`

- 请求方法：GET

- 描述：获取所有已配置的传感器信息，包含传感器ID、类型、状态、最后活跃时间等

- 请求参数：无

- 响应数据示例：

```json

{
  "code": 200,
  "message": "success",
  "data": [
    {
      "sensorId": "DHT11-001",
      "type": "温湿度",
      "status": "running",              // 状态：running-运行中，stopped-已停止
      "lastActiveTime": "2026-01-04T10:35:22+08:00",
      "description": "车内温湿度传感器",
      "dataSource": "simulation"        // 数据来源：simulation-模拟，real-真实
    },
    {
      "sensorId": "DHT11-002",
      "type": "温湿度",
      "status": "stopped",
      "lastActiveTime": "2026-01-04T09:15:33+08:00",
      "description": "发动机舱温湿度传感器",
      "dataSource": "simulation"
    }
  ]
}
```

### 3.2.2 添加传感器

- 接口路径：`/sensors`

- 请求方法：POST

- 描述：添加新的传感器配置（支持温湿度传感器，后续可扩展其他类型）

- 请求体参数：

```json

{
  "sensorId": "DHT11-003",    // 传感器ID（唯一标识，格式建议：传感器类型-序号）
  "type": "温湿度",           // 传感器类型：目前仅支持"温湿度"
  "description": "车外温湿度传感器" // 传感器描述（可选）
}
```

- 响应数据示例：

```json

{
  "code": 200,
  "message": "传感器添加成功",
  "data": {
    "sensorId": "DHT11-003"
  }
}
```

### 3.2.3 删除传感器

- 接口路径：`/sensors/{sensorId}`

- 请求方法：DELETE

- 描述：删除指定ID的传感器配置（仅支持删除已停止状态的传感器）

- 路径参数：`sensorId` - 传感器ID（如DHT11-003）

- 响应数据示例：

```json

{
  "code": 200,
  "message": "传感器删除成功",
  "data": {
    "sensorId": "DHT11-003"
  }
}
```

### 3.2.4 更新传感器状态

- 接口路径：`/sensors/{sensorId}/status`

- 请求方法：PUT

- 描述：启动或停止指定ID的传感器（模拟模式/真实模式均适用）

- 路径参数：`sensorId` - 传感器ID

- 请求体参数：

```json

{
  "status": "running" // 目标状态：running-启动，stopped-停止
}
```

- 响应数据示例：

```json

{
  "code": 200,
  "message": "传感器状态更新成功",
  "data": {
    "sensorId": "DHT11-002",
    "status": "running"
  }
}
```

### 3.2.5 获取传感器配置

- 接口路径：`/sensors/config`

- 请求方法：GET

- 描述：获取当前传感器的全局配置，包含数据来源模式、模拟参数、MQTT QoS级别等

- 请求参数：无

- 响应数据示例：

```json

{
  "code": 200,
  "message": "success",
  "data": {
    "dataSource": "simulation",        // 数据来源模式：simulation-模拟，real-真实
    "sampleRate": 2,                   // 采集频率（秒）
    "temperatureRange": {              // 温度模拟范围（仅模拟模式生效）
      "min": -40,
      "max": 85
    },
    "humidityRange": {                 // 湿度模拟范围（仅模拟模式生效）
      "min": 0,
      "max": 100
    },
    "mqttQos": 1                       // MQTT QoS级别：0-最多一次，1-至少一次，2-恰好一次
  }
}
```

### 3.2.6 更新传感器配置

- 接口路径：`/sensors/config`

- 请求方法：PUT

- 描述：更新传感器的全局配置（支持模式切换、参数调整，真实模式需核心模块完成后启用）

- 请求体参数：

```json

{
  "dataSource": "simulation",        // 数据来源模式：simulation-模拟，real-真实（真实模式默认不可用）
  "sampleRate": 3,                   // 采集频率（秒），范围：1-10
  "temperatureRange": {              // 温度模拟范围（仅模拟模式生效）
    "min": -40,
    "max": 85
  },
  "humidityRange": {                 // 湿度模拟范围（仅模拟模式生效）
    "min": 0,
    "max": 100
  },
  "mqttQos": 1                       // MQTT QoS级别：0/1/2
}
```

- 响应数据示例：

```json

{
  "code": 200,
  "message": "传感器配置更新成功",
  "data": {}
}
```

## 3.3 MQTT配置接口

### 3.3.1 获取MQTT配置

- 接口路径：`/mqtt/config`

- 请求方法：GET

- 描述：获取当前MQTT Broker的连接配置、认证信息及主题配置

- 请求参数：无

- 响应数据示例：

```json

{
  "code": 200,
  "message": "success",
  "data": {
    "brokerHost": "localhost",                // Broker地址
    "brokerPort": 1883,                       // Broker端口
    "clientId": "CarTest-Web-Client-12345",   // 客户端ID
    "cleanSession": true,                     // Clean Session标识
    "username": "",                           // 用户名（可选）
    "password": "",                           // 密码（可选）
    "subscribeTopic": "vehicle/sensor/data/+",// 数据订阅主题（支持通配符）
    "publishTopicTemplate": "vehicle/test/command/{sensor_id}" // 指令发布主题模板
  }
}
```

### 3.3.2 更新MQTT配置

- 接口路径：`/mqtt/config`

- 请求方法：PUT

- 描述：更新MQTT Broker的连接配置、认证信息及订阅主题

- 请求体参数：

```json

{
  "brokerHost": "localhost",                // Broker地址
  "brokerPort": 1883,                       // Broker端口
  "clientId": "CarTest-Web-Client-12345",   // 客户端ID
  "cleanSession": true,                     // Clean Session标识
  "username": "admin",                      // 用户名（可选）
  "password": "password123",                // 密码（可选）
  "subscribeTopic": "vehicle/sensor/data/+" // 数据订阅主题
}
```

- 响应数据示例：

```json

{
  "code": 200,
  "message": "MQTT配置更新成功",
  "data": {}
}
```

### 3.3.3 测试MQTT连接

- 接口路径：`/mqtt/test-connection`

- 请求方法：POST

- 描述：测试当前（或传入）的MQTT配置是否能成功连接Broker

- 请求体参数（可选，为空时使用当前配置）：

```json

{
  "brokerHost": "localhost",
  "brokerPort": 1883,
  "clientId": "CarTest-Web-Client-12345",
  "cleanSession": true,
  "username": "admin",
  "password": "password123"
}
```

- 响应数据示例：

```json

{
  "code": 200,
  "message": "MQTT连接测试成功",
  "data": {
    "connected": true,
    "responseTime": 350 // 连接响应时间（毫秒）
  }
}
```

## 3.4 测试用例接口

### 3.4.1 获取测试用例列表

- 接口路径：`/test-cases`

- 请求方法：GET

- 描述：获取所有测试用例信息，包含用例ID、名称、类型、描述及启用状态

- 请求参数：无

- 响应数据示例：

```json

{
  "code": 200,
  "message": "success",
  "data": [
    {
      "caseId": "TC-001",
      "name": "温度范围校验",
      "type": "功能测试",
      "description": "校验温度值是否在车载工作范围 [-40℃, 85℃] 内",
      "enabled": true
    },
    {
      "caseId": "TC-002",
      "name": "湿度范围校验",
      "type": "功能测试",
      "description": "校验湿度值是否在有效范围 [0%, 100%] 内",
      "enabled": true
    },
    {
      "caseId": "TC-003",
      "name": "数据格式校验",
      "type": "功能测试",
      "description": "校验接收的数据是否为合法JSON格式，并包含sensorId、temperature等必要字段",
      "enabled": true
    },
    {
      "caseId": "TC-004",
      "name": "MQTT QoS 1 可靠性测试",
      "type": "协议测试",
      "description": "模拟网络中断，验证QoS 1级别下消息的送达性",
      "enabled": false
    }
  ]
}
```

## 3.5 测试执行接口

### 3.5.1 开始测试

- 接口路径：`/tests/start`

- 请求方法：POST

- 描述：执行选中的测试用例，支持指定单个传感器或所有已连接传感器

- 请求体参数：

```json

{
  "sensorId": "all",                // 传感器ID：all-所有已连接传感器，或具体ID（如DHT11-001）
  "caseIds": ["TC-001", "TC-002"]  // 待执行的测试用例ID列表
}
```

- 响应数据示例：

```json

{
  "code": 200,
  "message": "测试已开始",
  "data": {
    "testId": "T-20260104-001" // 测试任务ID（用于后续查询结果、导出报告）
  }
}
```

### 3.5.2 获取实时测试结果

- 接口路径：`/tests/realtime-results`

- 请求方法：GET

- 描述：获取当前正在执行的测试任务的实时结果

- 请求参数（可选）：`sensorId` - 传感器ID，为空时获取所有传感器结果

- 响应数据示例：

```json

{
  "code": 200,
  "message": "success",
  "data": [
    {
      "timestamp": "2026-01-04T10:35:22+08:00",
      "sensorId": "DHT11-001",
      "caseId": "TC-001",
      "caseName": "温度范围校验",
      "result": "pass",          // 测试结果：pass-通过，fail-失败
      "details": "温度 25.3℃ 在 [-40, 85] 范围内"
    },
    {
      "timestamp": "2026-01-04T10:35:22+08:00",
      "sensorId": "DHT11-001",
      "caseId": "TC-002",
      "caseName": "湿度范围校验",
      "result": "pass",
      "details": "湿度 48.1% 在 [0, 100] 范围内"
    }
  ]
}
```

### 3.5.3 导出测试报告

- 接口路径：`/tests/export-report`

- 请求方法：GET

- 描述：导出指定测试任务或所有测试任务的报告，支持PDF/Excel格式

- 请求参数：

|参数名|类型|必填|描述|
|---|---|---|---|
|testId|string|否|测试任务ID，为空时导出所有测试报告|
|format|string|是|导出格式：pdf/excel|
- 响应数据示例：

```json

{
  "code": 200,
  "message": "success",
  "data": {
    "reportUrl": "/downloads/reports/T-20260104-001.pdf", // 报告下载链接
    "fileName": "测试报告_20260104_001.pdf"                // 报告文件名
  }
}
```

## 3.6 数据查询接口

### 3.6.1 查询历史测试结果

- 接口路径：`/data/test-results`

- 请求方法：GET

- 描述：分页查询历史测试结果，支持按传感器ID、时间范围筛选

- 请求参数：

|参数名|类型|必填|描述|
|---|---|---|---|
|sensorId|string|否|传感器ID，为空时查询所有|
|startTime|string|否|开始时间（ISO 8601格式）|
|endTime|string|否|结束时间（ISO 8601格式）|
|page|int|否|页码，默认1|
|pageSize|int|否|每页条数，默认10|
- 响应数据示例：

```json

{
  "code": 200,
  "message": "success",
  "data": {
    "total": 156,
    "page": 1,
    "pageSize": 10,
    "items": [
      {
        "testId": "T-20260104-001",
        "sensorId": "DHT11-001",
        "caseId": "TC-001",
        "caseName": "温度范围校验",
        "result": "pass",
        "testTime": "2026-01-04T10:35:22+08:00",
        "details": "温度 25.3℃ 在 [-40, 85] 范围内"
      },
      {
        "testId": "T-20260104-001",
        "sensorId": "DHT11-001",
        "caseId": "TC-002",
        "caseName": "湿度范围校验",
        "result": "pass",
        "testTime": "2026-01-04T10:35:22+08:00",
        "details": "湿度 48.1% 在 [0, 100] 范围内"
      }
    ]
  }
}
```

### 3.6.2 查询原始传感器数据

- 接口路径：`/data/sensor-data`

- 请求方法：GET

- 描述：分页查询原始传感器数据，支持按传感器ID、时间范围、数据来源筛选

- 请求参数：

|参数名|类型|必填|描述|
|---|---|---|---|
|sensorId|string|否|传感器ID，为空时查询所有|
|source|string|否|数据来源：simulation-模拟，real-真实，为空时查询所有|
|startTime|string|否|开始时间（ISO 8601格式）|
|endTime|string|否|结束时间（ISO 8601格式）|
|page|int|否|页码，默认1|
|pageSize|int|否|每页条数，默认10|
- 响应数据示例：

```json

{
  "code": 200,
  "message": "success",
  "data": {
    "total": 456,
    "page": 1,
    "pageSize": 10,
    "items": [
      {
        "dataId": "D-20260104-001",
        "sensorId": "DHT11-001",
        "temperature": 25.3,
        "humidity": 48.1,
        "receiveTime": "2026-01-04T10:35:22+08:00",
        "source": "simulation"
      },
      {
        "dataId": "D-20260104-002",
        "sensorId": "DHT11-001",
        "temperature": -41.0,
        "humidity": 50.0,
        "receiveTime": "2026-01-04T10:35:20+08:00",
        "source": "simulation"
      }
    ]
  }
}
```

### 3.6.3 导出原始传感器数据

- 接口路径：`/data/export-sensor-data`

- 请求方法：GET

- 描述：导出指定条件的原始传感器数据，仅支持Excel格式

- 请求参数：与“查询原始传感器数据”接口一致（无page、pageSize参数）

- 响应数据示例：

```json

{
  "code": 200,
  "message": "success",
  "data": {
    "fileUrl": "/downloads/data/sensor_data_20260104.xlsx", // 数据文件下载链接
    "fileName": "传感器原始数据_20260104.xlsx"                // 数据文件名
  }
}
```

### 3.6.4 生成数据图表

- 接口路径：`/data/generate-chart`

- 请求方法：GET

- 描述：生成指定传感器、指定指标的时序数据图表，返回图表图片链接及原始数据点

- 请求参数：

|参数名|类型|必填|描述|
|---|---|---|---|
|sensorId|string|是|传感器ID|
|metric|string|是|指标类型：temperature-温度，humidity-湿度|
|startTime|string|是|开始时间（ISO 8601格式）|
|endTime|string|是|结束时间（ISO 8601格式）|
- 响应数据示例：

```json

{
  "code": 200,
  "message": "success",
  "data": {
    "chartUrl": "/charts/DHT11-001_temperature_20260104.png", // 图表图片链接
    "dataPoints": [
      {
        "time": "2026-01-04T10:35:18+08:00",
        "value": 24.9
      },
      {
        "time": "2026-01-04T10:35:20+08:00",
        "value": -41.0
      },
      {
        "time": "2026-01-04T10:35:22+08:00",
        "value": 25.3
      }
    ]
  }
}
```

# 四、错误码说明

系统采用统一的错误码体系，用于标识不同类型的异常场景，便于前后端问题定位和处理：

|错误码|错误类型|说明|处理建议|
|---|---|---|---|
|200|成功|接口请求执行成功|无需处理|
|400|请求参数错误|请求参数缺失、格式错误或取值超出范围|检查请求参数是否符合接口文档要求|
|401|未授权|当前用户未登录或登录状态已过期|重新登录系统|
|403|权限不足|当前用户无权限执行该操作|联系管理员分配对应权限|
|404|资源不存在|请求的资源（如传感器、测试任务）不存在|检查资源ID是否正确，或确认资源已创建|
|409|资源冲突|操作与资源当前状态冲突（如删除运行中的传感器）|调整资源状态后重新操作（如先停止传感器再删除）|
|500|服务器内部错误|后端服务执行过程中发生未知异常|联系管理员查看服务日志定位问题|
|501|功能未实现|请求的功能尚未开发完成（如真实传感器模式）|等待功能开发完成后再使用|
|601|MQTT连接失败|MQTT Broker连接测试或实际连接失败|检查MQTT配置（地址、端口、认证信息）是否正确|
|602|传感器未连接|操作的传感器未处于连接状态|启动传感器并确认连接成功后再操作|
|603|测试任务冲突|当前存在正在执行的测试任务，无法重复启动|等待当前测试任务完成或终止后再启动新任务|
# 五、接口调用注意事项

1. 所有接口均需在请求头中携带认证信息（如Token），具体认证方式由项目统一认证方案确定。

2. 模拟模式与真实模式切换时，需确保核心模块已完成开发（真实模式启用条件），否则会返回501错误。

3. MQTT配置更新后需重新测试连接，确认连接成功后，新配置才会生效于传感器数据传输。

4. 分页查询接口的`pageSize`参数最大值为100，超过时会自动截断为100。

5. 导出接口（测试报告、传感器数据）返回的下载链接有效期为24小时，过期后需重新调用接口生成。

6. 实时测试结果接口建议通过WebSocket长连接实现推送，本文档中HTTP GET接口为简化方案，实际开发可优化。
> （注：文档部分内容可能由 AI 生成）