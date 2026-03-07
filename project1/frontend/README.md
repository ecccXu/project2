# CarTest MQTT 前端系统

基于React + TypeScript + Vite的车载环境传感器测试系统前端，实现传感器配置、MQTT连接管理、测试执行与数据展示功能。

## 技术栈

- **框架**: React 18
- **语言**: TypeScript
- **构建工具**: Vite 4
- **样式**: Tailwind CSS
- **状态管理**: Zustand
- **HTTP请求**: Axios
- **MQTT客户端**: mqtt.js
- **图标**: React Icons

## 项目概述

CarTest MQTT前端系统是专为车载环境传感器测试设计的完整前端解决方案，支持温湿度传感器配置、MQTT连接管理、自动化测试执行及数据可视化。系统采用前后端分离架构，前端专注于用户界面和交互体验，通过RESTful API与后端服务通信。

### 核心功能

#### 1. 仪表板
- 系统状态概览
- 传感器连接统计
- 测试通过率展示
- 今日测试数统计

#### 2. 传感器管理
- 传感器列表展示
- 添加/删除传感器
- 启动/停止传感器
- 传感器配置管理
- 数据来源模式切换

#### 3. MQTT配置管理
- MQTT Broker连接配置
- 认证信息管理
- 连接测试功能
- 订阅主题配置

#### 4. 测试执行管理
- 测试用例选择
- 测试任务启动
- 实时测试结果展示
- 测试报告导出

#### 5. 数据查询管理
- 历史测试结果查询
- 原始传感器数据查询
- 数据导出功能
- 支持分页查询
- 数据图表生成

## 目录结构

```
frontend/
├── public/                 # 静态资源
├── src/                    # 源代码目录
│   ├── components/         # 可复用组件
│   │   ├── Layout.tsx      # 主布局组件
│   │   └── MQTTListener.tsx # MQTT消息监听器
│   ├── pages/              # 页面组件
│   │   ├── Dashboard.tsx   # 仪表板页面
│   │   ├── Sensors.tsx     # 传感器管理页面
│   │   ├── MQTTConfig.tsx  # MQTT配置页面
│   │   ├── TestExecution.tsx # 测试执行页面
│   │   ├── DataQuery.tsx   # 数据查询页面
│   │   └── SystemStatus.tsx # 系统状态页面
│   ├── services/           # API服务
│   │   ├── api.ts          # API接口定义
│   │   └── mqttService.ts  # MQTT服务
│   ├── stores/             # 状态管理
│   │   └── index.ts        # Zustand store
│   ├── utils/              # 工具类
│   │   └── types.ts        # 类型定义
│   ├── App.tsx             # 应用主组件
│   ├── main.tsx            # 应用入口
│   └── index.css           # 全局样式
├── package.json            # 项目依赖配置
├── vite.config.ts          # Vite配置
├── tsconfig.json           # TypeScript配置
└── tailwind.config.js      # Tailwind配置
```

## 安装部署

### 1. 环境准备
```bash
# 安装Node.js依赖
npm install
```

### 2. 启动开发服务器
```bash
# 启动开发服务器
npm run dev

# 默认监听端口为3000（如果被占用会自动选择其他端口）
```

### 3. 构建生产版本
```bash
# 构建生产版本
npm run build

# 预览生产构建
npm run preview
```

## API接口

前端与后端通过以下API接口通信：

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

## 配置说明

### 环境配置
- 前端默认连接本地后端服务 (http://localhost:5000)
- 如需连接其他后端服务，修改 [src/services/api.ts](file:///X:/Code%20Projects/CarIoT_Test_Project/CarTest_MQTT/frontend/src/services/api.ts) 中的baseURL

### MQTT配置
- 通过WebSocket连接MQTT Broker
- 支持认证信息配置
- 可动态修改连接参数

## 优化总结

我们对CarTest MQTT前端系统进行了全方位的优化，主要改进包括：

### 1. 架构优化
- 采用React + TypeScript + Vite现代化技术栈
- 使用Tailwind CSS实现响应式设计
- 集成Zustand进行高效状态管理
- 使用Axios进行HTTP请求管理
- 集成mqtt.js实现MQTT over WebSocket连接

### 2. 组件结构优化
- 创建了完整的页面组件（仪表板、传感器管理、MQTT配置、测试执行、数据查询等）
- 实现了响应式布局和用户友好的界面设计
- 创建了MQTT监听器组件处理实时消息
- 实现了统一的错误处理和加载状态

### 3. API集成优化
- 创建了完整的API服务层，实现所有接口文档定义的端点
- 实现了MQTT服务层，处理WebSocket连接和消息订阅
- 创建了统一的状态管理store，管理所有应用状态
- 实现了类型安全的数据交互

### 4. 用户体验优化
- 实现了实时数据更新功能
- 添加了完整的表单验证和错误提示
- 优化了页面加载和响应性能
- 实现了直观的数据可视化

这些优化确保了前端系统完全符合接口文档规范，与后端服务协同工作良好，为用户提供流畅的操作体验，并为系统的可维护性和扩展性奠定了良好基础。