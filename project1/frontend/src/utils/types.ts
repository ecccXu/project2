// 系统状态类型
export interface SystemStatus {
  systemStatus: 'online' | 'offline';
  connectedSensors: number;
  testPassRate: number;
  todayTestCount: number;
  mqttConnectionStatus: 'connected' | 'disconnected';
}

// 传感器类型
export interface Sensor {
  sensorId: string;
  type: string;
  status: 'running' | 'stopped';
  lastActiveTime: string | null;
  description: string;
  dataSource: 'simulation' | 'real';
}

// 传感器配置类型
export interface SensorConfig {
  dataSource: 'simulation' | 'real';
  sampleRate: number;
  temperatureRange: {
    min: number;
    max: number;
  };
  humidityRange: {
    min: number;
    max: number;
  };
  mqttQos: number;
}

// MQTT配置类型
export interface MqttConfig {
  brokerHost: string;
  brokerPort: number;
  clientId: string;
  cleanSession: boolean;
  username: string;
  password: string;
  subscribeTopic: string;
  publishTopicTemplate: string;
}

// MQTT连接测试结果类型
export interface MqttTestResult {
  connected: boolean;
  responseTime: number;
  error?: string;
}

// 测试用例类型
export interface TestCase {
  caseId: string;
  name: string;
  type: string;
  description: string;
  enabled: boolean;
}

// 测试执行请求类型
export interface TestExecutionRequest {
  sensorId: string;
  caseIds: string[];
}

// 测试结果类型
export interface TestResult {
  timestamp: string;
  sensorId: string;
  caseId: string;
  caseName: string;
  result: 'pass' | 'fail';
  details: string;
}

// 测试结果响应类型
export interface TestResultResponse {
  testId: string;
  sensorId: string;
  caseId: string;
  caseName: string;
  result: 'pass' | 'fail';
  testTime: string;
  details: string;
}

// 分页响应类型
export interface PaginatedResponse<T> {
  total: number;
  page: number;
  pageSize: number;
  items: T[];
}

// 传感器数据类型
export interface SensorData {
  dataId: string;
  sensorId: string;
  temperature: number | null;
  humidity: number | null;
  receiveTime: string;
  source: 'simulation' | 'real';
}

// 测试报告导出参数
export interface ExportReportParams {
  testId?: string;
  format: 'pdf' | 'excel';
}

// 传感器数据导出参数
export interface ExportSensorDataParams {
  sensorId?: string;
  source?: 'simulation' | 'real';
  startTime?: string;
  endTime?: string;
}

// 图表生成参数
export interface GenerateChartParams {
  sensorId: string;
  metric: 'temperature' | 'humidity';
  startTime: string;
  endTime: string;
}

// MQTT连接状态类型
export type MqttConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';