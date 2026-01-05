import { create } from 'zustand';
import { 
  SystemStatus, 
  Sensor, 
  SensorConfig, 
  MqttConfig, 
  TestCase, 
  TestResult,
  SensorData,
  MqttTestResult,
  MqttConnectionStatus
} from '../utils/types';
import { mqttService } from '../services/mqttService';
import { systemApi, sensorApi, mqttApi, testCaseApi, testExecutionApi, dataQueryApi } from '../services/api';

interface AppState {
  // 系统状态
  systemStatus: SystemStatus | null;
  loadingSystemStatus: boolean;
  systemStatusError: string | null;
  
  // 传感器相关
  sensors: Sensor[];
  sensorConfig: SensorConfig | null;
  loadingSensors: boolean;
  loadingSensorConfig: boolean;
  sensorsError: string | null;
  sensorConfigError: string | null;
  
  // MQTT相关
  mqttConfig: MqttConfig | null;
  mqttConnectionStatus: MqttConnectionStatus;
  loadingMqttConfig: boolean;
  mqttTestResult: MqttTestResult | null;
  mqttConfigError: string | null;
  
  // 测试用例相关
  testCases: TestCase[];
  loadingTestCases: boolean;
  testCasesError: string | null;
  
  // 测试执行相关
  realtimeResults: TestResult[];
  loadingRealtimeResults: boolean;
  realtimeResultsError: string | null;
  
  // 数据查询相关
  testResults: TestResult[];
  sensorData: SensorData[];
  loadingTestResults: boolean;
  loadingSensorData: boolean;
  testResultsError: string | null;
  sensorDataError: string | null;
  
  // 操作方法
  fetchSystemStatus: () => Promise<void>;
  fetchSensors: () => Promise<void>;
  addSensor: (sensorData: Omit<Sensor, 'lastActiveTime'>) => Promise<void>;
  deleteSensor: (sensorId: string) => Promise<void>;
  updateSensorStatus: (sensorId: string, status: 'running' | 'stopped') => Promise<void>;
  fetchSensorConfig: () => Promise<void>;
  updateSensorConfig: (config: SensorConfig) => Promise<void>;
  fetchMqttConfig: () => Promise<void>;
  updateMqttConfig: (config: MqttConfig) => Promise<void>;
  testMqttConnection: (config?: MqttConfig) => Promise<void>;
  connectToMqtt: (config: MqttConfig) => Promise<void>;
  disconnectMqtt: () => void;
  fetchTestCases: () => Promise<void>;
  startTest: (testData: { sensorId: string; caseIds: string[] }) => Promise<void>;
  fetchRealtimeResults: (sensorId?: string) => Promise<void>;
  exportReport: (params: { testId?: string; format: 'pdf' | 'excel' }) => Promise<void>;
  fetchTestResults: (params: {
    sensorId?: string;
    startTime?: string;
    endTime?: string;
    page?: number;
    pageSize?: number;
  }) => Promise<void>;
  fetchSensorData: (params: {
    sensorId?: string;
    source?: 'simulation' | 'real';
    startTime?: string;
    endTime?: string;
    page?: number;
    pageSize?: number;
  }) => Promise<void>;
  exportSensorData: (params: {
    sensorId?: string;
    source?: 'simulation' | 'real';
    startTime?: string;
    endTime?: string;
  }) => Promise<void>;
  generateChart: (params: {
    sensorId: string;
    metric: 'temperature' | 'humidity';
    startTime: string;
    endTime: string;
  }) => Promise<void>;
  clearErrors: () => void;
}

export const useAppStore = create<AppState>((set, get) => ({
  // 初始化状态
  systemStatus: null,
  loadingSystemStatus: false,
  systemStatusError: null,
  sensors: [],
  sensorConfig: null,
  loadingSensors: false,
  loadingSensorConfig: false,
  sensorsError: null,
  sensorConfigError: null,
  mqttConfig: null,
  mqttConnectionStatus: 'disconnected',
  loadingMqttConfig: false,
  mqttTestResult: null,
  mqttConfigError: null,
  testCases: [],
  loadingTestCases: false,
  testCasesError: null,
  realtimeResults: [],
  loadingRealtimeResults: false,
  realtimeResultsError: null,
  testResults: [],
  sensorData: [],
  loadingTestResults: false,
  loadingSensorData: false,
  testResultsError: null,
  sensorDataError: null,
  
  // 获取系统状态
  fetchSystemStatus: async () => {
    set({ loadingSystemStatus: true, systemStatusError: null });
    try {
      const response = await systemApi.getStatus();
      if (response.code === 200) {
        set({ systemStatus: response.data, systemStatusError: null });
      } else {
        set({ systemStatusError: response.message || '获取系统状态失败' });
      }
    } catch (error: any) {
      console.error('获取系统状态失败:', error);
      set({ systemStatusError: error.message || '获取系统状态失败' });
    } finally {
      set({ loadingSystemStatus: false });
    }
  },
  
  // 获取传感器列表
  fetchSensors: async () => {
    set({ loadingSensors: true, sensorsError: null });
    try {
      const response = await sensorApi.getSensors();
      if (response.code === 200) {
        set({ sensors: response.data, sensorsError: null });
      } else {
        set({ sensorsError: response.message || '获取传感器列表失败' });
      }
    } catch (error: any) {
      console.error('获取传感器列表失败:', error);
      set({ sensorsError: error.message || '获取传感器列表失败' });
    } finally {
      set({ loadingSensors: false });
    }
  },
  
  // 添加传感器
  addSensor: async (sensorData) => {
    try {
      const response = await sensorApi.addSensor(sensorData);
      if (response.code === 200) {
        // 重新获取传感器列表
        get().fetchSensors();
        return response.data;
      } else {
        throw new Error(response.message || '添加传感器失败');
      }
    } catch (error: any) {
      console.error('添加传感器失败:', error);
      set({ sensorsError: error.message || '添加传感器失败' });
      throw error;
    }
  },
  
  // 删除传感器
  deleteSensor: async (sensorId) => {
    try {
      const response = await sensorApi.deleteSensor(sensorId);
      if (response.code === 200) {
        // 从本地状态中移除传感器
        set((state) => ({
          sensors: state.sensors.filter(sensor => sensor.sensorId !== sensorId)
        }));
        return response.data;
      } else {
        throw new Error(response.message || '删除传感器失败');
      }
    } catch (error: any) {
      console.error('删除传感器失败:', error);
      set({ sensorsError: error.message || '删除传感器失败' });
      throw error;
    }
  },
  
  // 更新传感器状态
  updateSensorStatus: async (sensorId, status) => {
    try {
      const response = await sensorApi.updateSensorStatus(sensorId, status);
      if (response.code === 200) {
        // 更新本地状态
        set((state) => ({
          sensors: state.sensors.map(sensor => 
            sensor.sensorId === sensorId 
              ? { ...sensor, status: response.data.status as 'running' | 'stopped' } 
              : sensor
          )
        }));
        return response.data;
      } else {
        throw new Error(response.message || '更新传感器状态失败');
      }
    } catch (error: any) {
      console.error('更新传感器状态失败:', error);
      set({ sensorsError: error.message || '更新传感器状态失败' });
      throw error;
    }
  },
  
  // 获取传感器配置
  fetchSensorConfig: async () => {
    set({ loadingSensorConfig: true, sensorConfigError: null });
    try {
      const response = await sensorApi.getSensorConfig();
      if (response.code === 200) {
        set({ sensorConfig: response.data, sensorConfigError: null });
      } else {
        set({ sensorConfigError: response.message || '获取传感器配置失败' });
      }
    } catch (error: any) {
      console.error('获取传感器配置失败:', error);
      set({ sensorConfigError: error.message || '获取传感器配置失败' });
    } finally {
      set({ loadingSensorConfig: false });
    }
  },
  
  // 更新传感器配置
  updateSensorConfig: async (config) => {
    try {
      const response = await sensorApi.updateSensorConfig(config);
      if (response.code === 200) {
        set({ sensorConfig: config });
        return response.data;
      } else {
        throw new Error(response.message || '更新传感器配置失败');
      }
    } catch (error: any) {
      console.error('更新传感器配置失败:', error);
      set({ sensorConfigError: error.message || '更新传感器配置失败' });
      throw error;
    }
  },
  
  // 获取MQTT配置
  fetchMqttConfig: async () => {
    set({ loadingMqttConfig: true, mqttConfigError: null });
    try {
      const response = await mqttApi.getMqttConfig();
      if (response.code === 200) {
        set({ mqttConfig: response.data, mqttConfigError: null });
      } else {
        set({ mqttConfigError: response.message || '获取MQTT配置失败' });
      }
    } catch (error: any) {
      console.error('获取MQTT配置失败:', error);
      set({ mqttConfigError: error.message || '获取MQTT配置失败' });
    } finally {
      set({ loadingMqttConfig: false });
    }
  },
  
  // 更新MQTT配置
  updateMqttConfig: async (config) => {
    try {
      const response = await mqttApi.updateMqttConfig(config);
      if (response.code === 200) {
        set({ mqttConfig: config });
        return response.data;
      } else {
        throw new Error(response.message || '更新MQTT配置失败');
      }
    } catch (error: any) {
      console.error('更新MQTT配置失败:', error);
      set({ mqttConfigError: error.message || '更新MQTT配置失败' });
      throw error;
    }
  },
  
  // 测试MQTT连接
  testMqttConnection: async (config) => {
    try {
      const response = await mqttApi.testMqttConnection(config);
      if (response.code === 200) {
        set({ mqttTestResult: response.data });
        return response.data;
      } else {
        throw new Error(response.message || '测试MQTT连接失败');
      }
    } catch (error: any) {
      console.error('测试MQTT连接失败:', error);
      set({ mqttConfigError: error.message || '测试MQTT连接失败' });
      throw error;
    }
  },
  
  // 连接MQTT
  connectToMqtt: async (config) => {
    set({ mqttConnectionStatus: 'connecting' });
    try {
      await mqttService.connect(config);
      set({ mqttConnectionStatus: 'connected' });
    } catch (error: any) {
      console.error('MQTT连接失败:', error);
      set({ mqttConnectionStatus: 'error' });
      throw error;
    }
  },
  
  // 断开MQTT连接
  disconnectMqtt: () => {
    mqttService.disconnect();
    set({ mqttConnectionStatus: 'disconnected' });
  },
  
  // 获取测试用例
  fetchTestCases: async () => {
    set({ loadingTestCases: true, testCasesError: null });
    try {
      const response = await testCaseApi.getTestCases();
      if (response.code === 200) {
        set({ testCases: response.data, testCasesError: null });
      } else {
        set({ testCasesError: response.message || '获取测试用例失败' });
      }
    } catch (error: any) {
      console.error('获取测试用例失败:', error);
      set({ testCasesError: error.message || '获取测试用例失败' });
    } finally {
      set({ loadingTestCases: false });
    }
  },
  
  // 开始测试
  startTest: async (testData) => {
    try {
      const response = await testExecutionApi.startTest(testData);
      if (response.code === 200) {
        console.log('测试已开始，测试ID:', response.data.testId);
        return response.data;
      } else {
        throw new Error(response.message || '开始测试失败');
      }
    } catch (error: any) {
      console.error('开始测试失败:', error);
      throw error;
    }
  },
  
  // 获取实时测试结果
  fetchRealtimeResults: async (sensorId) => {
    set({ loadingRealtimeResults: true, realtimeResultsError: null });
    try {
      const response = await testExecutionApi.getRealtimeResults(sensorId);
      if (response.code === 200) {
        set({ realtimeResults: response.data, realtimeResultsError: null });
      } else {
        set({ realtimeResultsError: response.message || '获取实时测试结果失败' });
      }
    } catch (error: any) {
      console.error('获取实时测试结果失败:', error);
      set({ realtimeResultsError: error.message || '获取实时测试结果失败' });
    } finally {
      set({ loadingRealtimeResults: false });
    }
  },
  
  // 导出报告
  exportReport: async (params) => {
    try {
      const response = await testExecutionApi.exportReport(params);
      if (response.code === 200) {
        console.log('报告导出成功:', response.data.reportUrl);
        window.open(response.data.reportUrl, '_blank');
        return response.data;
      } else {
        throw new Error(response.message || '导出报告失败');
      }
    } catch (error: any) {
      console.error('导出报告失败:', error);
      throw error;
    }
  },
  
  // 获取测试结果
  fetchTestResults: async (params) => {
    set({ loadingTestResults: true, testResultsError: null });
    try {
      const response = await dataQueryApi.getTestResults(params);
      if (response.code === 200) {
        set({ testResults: response.data.items, testResultsError: null });
      } else {
        set({ testResultsError: response.message || '获取测试结果失败' });
      }
    } catch (error: any) {
      console.error('获取测试结果失败:', error);
      set({ testResultsError: error.message || '获取测试结果失败' });
    } finally {
      set({ loadingTestResults: false });
    }
  },
  
  // 获取传感器数据
  fetchSensorData: async (params) => {
    set({ loadingSensorData: true, sensorDataError: null });
    try {
      const response = await dataQueryApi.getSensorData(params);
      if (response.code === 200) {
        set({ sensorData: response.data.items, sensorDataError: null });
      } else {
        set({ sensorDataError: response.message || '获取传感器数据失败' });
      }
    } catch (error: any) {
      console.error('获取传感器数据失败:', error);
      set({ sensorDataError: error.message || '获取传感器数据失败' });
    } finally {
      set({ loadingSensorData: false });
    }
  },
  
  // 导出传感器数据
  exportSensorData: async (params) => {
    try {
      const response = await dataQueryApi.exportSensorData(params);
      if (response.code === 200) {
        console.log('传感器数据导出成功:', response.data.fileUrl);
        window.open(response.data.fileUrl, '_blank');
        return response.data;
      } else {
        throw new Error(response.message || '导出传感器数据失败');
      }
    } catch (error: any) {
      console.error('导出传感器数据失败:', error);
      throw error;
    }
  },
  
  // 生成图表
  generateChart: async (params) => {
    try {
      const response = await dataQueryApi.generateChart(params);
      if (response.code === 200) {
        console.log('图表生成成功:', response.data.chartUrl);
        // 这里可以将图表URL保存到状态中供组件使用
        return response.data;
      } else {
        throw new Error(response.message || '生成图表失败');
      }
    } catch (error: any) {
      console.error('生成图表失败:', error);
      throw error;
    }
  },
  
  // 清除错误
  clearErrors: () => {
    set({
      systemStatusError: null,
      sensorsError: null,
      sensorConfigError: null,
      mqttConfigError: null,
      testCasesError: null,
      realtimeResultsError: null,
      testResultsError: null,
      sensorDataError: null
    });
  }
}));