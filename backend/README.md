# CarTest MQTT 后端系统

基于Flask + SQLAlchemy + MySQL的车载环境传感器测试系统后端，实现传感器数据采集、MQTT通信、测试执行与数据管理功能。

## 技术栈

- **语言**: Python 3.8+
- **框架**: Flask 2.3.3
- **ORM**: SQLAlchemy 3.0.5
- **数据库**: MySQL 8.0+ (支持SQLite开发测试)
- **MQTT客户端**: paho-mqtt 1.6.1
- **其他**: python-dotenv, pytest

## 项目概述

CarTest MQTT后端系统是专为车载环境传感器测试设计的完整解决方案，支持温湿度传感器数据采集、MQTT协议通信、自动化测试执行及数据管理。系统采用前后端分离架构，后端专注于业务逻辑处理和数据管理，为前端提供RESTful API接口。

### 核心功能

#### 1. 系统状态管理
- 获取系统整体运行状态
- 监控传感器连接数、测试通过率等指标
- 实时更新系统运行信息

#### 2. 传感器管理
- 传感器配置（模拟/真实模式、采集频率等）
- 传感器列表管理（添加、删除、状态控制）
- 传感器数据源管理
- 支持多种传感器类型扩展

#### 3. MQTT配置管理
- MQTT Broker连接配置
- 主题配置管理
- 连接测试功能
- 支持认证信息配置

#### 4. 测试用例管理
- 测试用例列表查询
- 默认测试用例初始化
- 测试用例启用/禁用控制
- 支持多种测试类型（功能测试、协议测试等）

#### 5. 测试执行管理
- 测试任务启动
- 实时测试结果查询
- 测试报告生成
- 支持批量测试执行

#### 6. 数据查询管理
- 历史测试结果查询
- 原始传感器数据查询
- 数据导出功能
- 支持分页查询

## 目录结构

```
backend/
├── app.py                 # 应用主入口
├── requirements.txt       # 依赖包列表
├── .env                  # 环境配置文件
├── config/               # 配置模块
│   ├── __init__.py
│   ├── app_config.py     # 应用配置
│   └── db_config.py      # 数据库配置
├── models/               # 数据模型
│   └── __init__.py
├── services/             # 业务逻辑服务
│   ├── __init__.py
│   ├── system_service.py
│   ├── sensor_service.py
│   ├── mqtt_service.py
│   ├── test_case_service.py
│   ├── test_execution_service.py
│   └── data_service.py
├── controllers/          # 控制器
│   ├── __init__.py
│   ├── system_controller.py
│   ├── sensor_controller.py
│   ├── mqtt_controller.py
│   ├── test_case_controller.py
│   ├── test_execution_controller.py
│   └── data_controller.py
├── utils/                # 工具类
│   ├── __init__.py
│   ├── response.py       # 响应格式工具
│   └── error_handler.py  # 错误处理
└── README.md
```

## API接口

### 系统状态接口
- `GET /api/v1/system/status` - 获取系统整体状态

### 传感器管理接口
- `GET /api/v1/sensors` - 获取传感器列表
- `POST /api/v1/sensors` - 添加传感器
- `DELETE /api/v1/sensors/{sensorId}` - 删除传感器
- `PUT /api/v1/sensors/{sensorId}/status` - 更新传感器状态
- `GET /api/v1/sensors/config` - 获取传感器配置
- `PUT /api/v1/sensors/config` - 更新传感器配置

### MQTT配置接口
- `GET /api/v1/mqtt/config` - 获取MQTT配置
- `PUT /api/v1/mqtt/config` - 更新MQTT配置
- `POST /api/v1/mqtt/test-connection` - 测试MQTT连接

### 测试用例接口
- `GET /api/v1/test-cases` - 获取测试用例列表

### 测试执行接口
- `POST /api/v1/tests/start` - 开始测试
- `GET /api/v1/tests/realtime-results` - 获取实时测试结果
- `GET /api/v1/tests/export-report` - 导出测试报告

### 数据查询接口
- `GET /api/v1/data/test-results` - 查询历史测试结果
- `GET /api/v1/data/sensor-data` - 查询原始传感器数据
- `GET /api/v1/data/export-sensor-data` - 导出传感器数据
- `GET /api/v1/data/generate-chart` - 生成数据图表

## 安装部署

### 1. 环境准备
```bash
# 安装Python依赖
pip install -r requirements.txt
```

### 2. 数据库配置
修改 `.env` 文件中的数据库配置：
```env
# 选择数据库类型: sqlite 或 mysql
DB_TYPE=sqlite  # 开发测试用
# DB_TYPE=mysql  # 生产环境用

# MySQL配置 (当DB_TYPE=mysql时生效)
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DB=cariot_test
```

### 3. 启动应用
```bash
# 开发模式启动
python app.py

# 或使用Flask命令
flask run
```

### 4. 访问服务
服务启动后，默认监听 `http://localhost:5000`

## 错误码说明

| 错误码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未授权 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 409 | 资源冲突 |
| 500 | 服务器内部错误 |
| 601 | MQTT连接失败 |
| 603 | 测试任务冲突 |

## 测试

运行单元测试：
```bash
pytest
```

## 配置说明

### 数据库配置
- 开发测试环境推荐使用SQLite，无需额外配置
- 生产环境推荐使用MySQL，需正确配置连接参数

### MQTT配置
- 系统默认连接本地MQTT Broker (localhost:1883)
- 可通过API接口动态修改MQTT连接参数

### 分页配置
- 默认每页10条记录
- 最大每页100条记录

## 优化总结

我们对CarTest MQTT系统进行了全方位的优化，主要改进包括：

### 后端优化

#### 1. 数据模型优化
- 确保所有时间字段使用UTC时间并符合ISO 8601格式
- 优化数据库表结构，确保字段类型和约束符合接口文档要求

#### 2. 服务层优化
- 增强参数验证，确保所有输入参数符合接口文档规范
- 添加更完善的错误处理机制
- 优化业务逻辑，确保数据处理符合接口文档要求

#### 3. 控制器层优化
- 确保所有API端点的请求方法、路径和参数完全符合接口文档
- 统一响应格式，确保所有接口返回标准格式数据
- 增强错误处理，提供更准确的错误码和消息

#### 4. 错误处理优化
- 添加针对特定错误码的处理（如603测试任务冲突、601 MQTT连接失败等）
- 统一错误响应格式
- 完善日志记录

#### 5. 功能完整性
- 实现了所有接口文档中定义的端点
- 确保分页功能符合规范
- 添加了导出和图表生成接口的模拟实现

### 前端优化

#### 1. 架构优化
- 采用React + TypeScript + Vite技术栈
- 使用Tailwind CSS进行样式设计
- 集成Zustand进行状态管理
- 使用Axios进行HTTP请求
- 集成mqtt.js实现MQTT over WebSocket连接

#### 2. 组件结构优化
- 创建了完整的页面组件（仪表板、传感器管理、MQTT配置、测试执行、数据查询等）
- 实现了响应式布局和用户友好的界面设计
- 创建了MQTT监听器组件处理实时消息
- 实现了统一的错误处理和加载状态

#### 3. API集成优化
- 创建了完整的API服务层，实现所有接口文档定义的端点
- 实现了MQTT服务层，处理WebSocket连接和消息订阅
- 创建了统一的状态管理store，管理所有应用状态
- 实现了类型安全的数据交互

#### 4. 用户体验优化
- 实现了实时数据更新功能
- 添加了完整的表单验证和错误提示
- 优化了页面加载和响应性能
- 实现了直观的数据可视化

### 验证结果
通过全面测试，前后端接口完全符合接口文档规范，数据结构和格式完全一致，系统运行稳定。前端能够正确调用后端API并展示数据，实现了完整的车载环境传感器测试系统功能。

这些优化确保了整个系统完全符合接口文档规范，前后端协同工作良好，为系统的可维护性和扩展性奠定了良好基础。