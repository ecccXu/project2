import axios, { AxiosError } from 'axios';
import { 
  SystemStatus, 
  Sensor, 
  SensorConfig, 
  MqttConfig, 
  MqttTestResult, 
  TestCase, 
  TestExecutionRequest, 
  TestResult,
  PaginatedResponse,
  TestResultResponse,
  SensorData,
  ExportReportParams,
  ExportSensorDataParams,
  GenerateChartParams
} from '../utils/types';

// 创建axios实例
const apiClient = axios.create({
  baseURL: 'http://localhost:5000/api/v1',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 可以在这里添加认证token等
    console.log(`API请求: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    console.log(`API响应: ${response.config.url}`, response.data);
    return response.data;
  },
  (error: AxiosError) => {
    console.error('API Error:', error.response?.data || error.message);
    
    // 根据错误类型进行处理
    if (error.response) {
      // 服务器响应了错误状态码
      console.error(`API Error ${error.response.status}:`, error.response.data);
    } else if (error.request) {
      // 请求已发出但没有收到响应
      console.error('Network Error:', error.message);
    } else {
      // 其他错误
      console.error('Request Error:', error.message);
    }
    
    return Promise.reject(error);
  }
);

// 系统状态相关API
export const systemApi = {
  getStatus: (): Promise<{ code: number; message: string; data: SystemStatus }> => {
    return apiClient.get('/system/status');
  },
};

// 传感器相关API
export const sensorApi = {
  getSensors: (): Promise<{ code: number; message: string; data: Sensor[] }> => {
    return apiClient.get('/sensors');
  },
  
  addSensor: (sensorData: Omit<Sensor, 'lastActiveTime'>): Promise<{ code: number; message: string; data: { sensorId: string } }> => {
    return apiClient.post('/sensors', sensorData);
  },
  
  deleteSensor: (sensorId: string): Promise<{ code: number; message: string; data: { sensorId: string } }> => {
    return apiClient.delete(`/sensors/${sensorId}`);
  },
  
  updateSensorStatus: (sensorId: string, status: 'running' | 'stopped'): Promise<{ code: number; message: string; data: { sensorId: string; status: string } }> => {
    return apiClient.put(`/sensors/${sensorId}/status`, { status });
  },
  
  getSensorConfig: (): Promise<{ code: number; message: string; data: SensorConfig }> => {
    return apiClient.get('/sensors/config');
  },
  
  updateSensorConfig: (config: SensorConfig): Promise<{ code: number; message: string; data: {} }> => {
    return apiClient.put('/sensors/config', config);
  },
};

// MQTT相关API
export const mqttApi = {
  getMqttConfig: (): Promise<{ code: number; message: string; data: MqttConfig }> => {
    return apiClient.get('/mqtt/config');
  },
  
  updateMqttConfig: (config: MqttConfig): Promise<{ code: number; message: string; data: {} }> => {
    return apiClient.put('/mqtt/config', config);
  },
  
  testMqttConnection: (config?: MqttConfig): Promise<{ code: number; message: string; data: MqttTestResult }> => {
    return apiClient.post('/mqtt/test-connection', config || {});
  },
};

// 测试用例相关API
export const testCaseApi = {
  getTestCases: (): Promise<{ code: number; message: string; data: TestCase[] }> => {
    return apiClient.get('/test-cases');
  },
};

// 测试执行相关API
export const testExecutionApi = {
  startTest: (testData: TestExecutionRequest): Promise<{ code: number; message: string; data: { testId: string } }> => {
    return apiClient.post('/tests/start', testData);
  },
  
  getRealtimeResults: (sensorId?: string): Promise<{ code: number; message: string; data: TestResult[] }> => {
    const params: Record<string, string> = {};
    if (sensorId) {
      params.sensorId = sensorId;
    }
    return apiClient.get('/tests/realtime-results', { params });
  },
  
  exportReport: (params: ExportReportParams): Promise<{ code: number; message: string; data: { reportUrl: string; fileName: string } }> => {
    return apiClient.get('/tests/export-report', { params });
  },
};

// 数据查询相关API
export const dataQueryApi = {
  getTestResults: (params: {
    sensorId?: string;
    startTime?: string;
    endTime?: string;
    page?: number;
    pageSize?: number;
  }): Promise<{ code: number; message: string; data: PaginatedResponse<TestResultResponse> }> => {
    return apiClient.get('/data/test-results', { params });
  },
  
  getSensorData: (params: {
    sensorId?: string;
    source?: 'simulation' | 'real';
    startTime?: string;
    endTime?: string;
    page?: number;
    pageSize?: number;
  }): Promise<{ code: number; message: string; data: PaginatedResponse<SensorData> }> => {
    return apiClient.get('/data/sensor-data', { params });
  },
  
  exportSensorData: (params: ExportSensorDataParams): Promise<{ code: number; message: string; data: { fileUrl: string; fileName: string } }> => {
    return apiClient.get('/data/export-sensor-data', { params });
  },
  
  generateChart: (params: GenerateChartParams): Promise<{ code: number; message: string; data: { chartUrl: string; dataPoints: { time: string; value: number }[] } }> => {
    return apiClient.get('/data/generate-chart', { params });
  },
};