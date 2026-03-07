import React, { useEffect } from 'react';
import { useAppStore } from '../stores';
import { FaServer, FaMicrochip, FaCheckCircle, FaChartBar } from 'react-icons/fa';

const Dashboard: React.FC = () => {
  const {
    systemStatus,
    loadingSystemStatus,
    sensors,
    systemStatusError,
    sensorsError,
    fetchSystemStatus,
    fetchSensors
  } = useAppStore();

  useEffect(() => {
    // 初始加载数据
    fetchSystemStatus();
    fetchSensors();
    
    // 设置定时刷新（每30秒刷新一次）
    const interval = setInterval(() => {
      fetchSystemStatus();
      fetchSensors();
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  const getMqttStatusColor = () => {
    if (!systemStatus) return 'bg-gray-100 text-gray-800';
    return systemStatus.mqttConnectionStatus === 'connected'
      ? 'bg-green-100 text-green-800'
      : 'bg-red-100 text-red-800';
  };

  const runningSensors = sensors.filter(sensor => sensor.status === 'running').length;

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800">系统仪表板</h1>
        <p className="text-gray-600">车载环境传感器测试系统概览</p>
      </div>

      {/* 错误信息显示 */}
      {(systemStatusError || sensorsError) && (
        <div className="mb-6 p-4 bg-red-100 border border-red-400 text-red-700 rounded-md">
          <p>发生错误：</p>
          {systemStatusError && <p>系统状态错误：{systemStatusError}</p>}
          {sensorsError && <p>传感器错误：{sensorsError}</p>}
        </div>
      )}

      {/* 状态卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
        <div className="bg-white p-6 rounded-md shadow-md">
          <div className="flex items-center">
            <div className="p-3 rounded-full bg-blue-100">
              <FaServer className="text-blue-500 text-xl" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">系统状态</p>
              {loadingSystemStatus ? (
                <p className="text-2xl font-semibold text-gray-900">加载中...</p>
              ) : systemStatus ? (
                <p className={`text-2xl font-semibold ${systemStatus.systemStatus === 'online' ? 'text-green-600' : 'text-red-600'}`}>
                  {systemStatus.systemStatus === 'online' ? '在线' : '离线'}
                </p>
              ) : (
                <p className="text-2xl font-semibold text-gray-900">未知</p>
              )}
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-md shadow-md">
          <div className="flex items-center">
            <div className="p-3 rounded-full bg-green-100">
              <FaMicrochip className="text-green-500 text-xl" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">传感器</p>
              <p className="text-2xl font-semibold text-gray-900">
                {sensors.length} / {runningSensors} 运行中
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-md shadow-md">
          <div className="flex items-center">
            <div className="p-3 rounded-full bg-yellow-100">
              <FaCheckCircle className="text-yellow-500 text-xl" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">测试通过率</p>
              {loadingSystemStatus ? (
                <p className="text-2xl font-semibold text-gray-900">加载中...</p>
              ) : systemStatus ? (
                <p className="text-2xl font-semibold text-gray-900">{systemStatus.testPassRate}%</p>
              ) : (
                <p className="text-2xl font-semibold text-gray-900">0%</p>
              )}
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-md shadow-md">
          <div className="flex items-center">
            <div className="p-3 rounded-full bg-purple-100">
              <FaChartBar className="text-purple-500 text-xl" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">今日测试</p>
              {loadingSystemStatus ? (
                <p className="text-2xl font-semibold text-gray-900">加载中...</p>
              ) : systemStatus ? (
                <p className="text-2xl font-semibold text-gray-900">{systemStatus.todayTestCount}</p>
              ) : (
                <p className="text-2xl font-semibold text-gray-900">0</p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* MQTT连接状态 */}
      <div className="bg-white p-6 rounded-md shadow-md mb-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">MQTT连接状态</h2>
        <div className="flex items-center">
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${getMqttStatusColor()}`}>
            {loadingSystemStatus 
              ? '加载中...' 
              : systemStatus 
                ? systemStatus.mqttConnectionStatus === 'connected' 
                  ? '已连接' 
                  : '未连接'
                : '未知'}
          </span>
          <span className="ml-4 text-gray-600">
            {loadingSystemStatus 
              ? '正在获取状态...' 
              : systemStatus 
                ? systemStatus.mqttConnectionStatus === 'connected' 
                  ? 'MQTT Broker连接正常，可以接收传感器数据' 
                  : 'MQTT Broker未连接，请检查配置'
                : '无法获取MQTT连接状态'}
          </span>
        </div>
      </div>

      {/* 传感器状态概览 */}
      <div className="bg-white rounded-md shadow-md overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-800">传感器状态概览</h2>
        </div>
        <div className="p-6">
          {sensors.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {sensors.map((sensor) => (
                <div 
                  key={sensor.sensorId} 
                  className={`p-4 rounded-md border ${
                    sensor.status === 'running' 
                      ? 'border-green-200 bg-green-50' 
                      : 'border-red-200 bg-red-50'
                  }`}
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className="font-medium text-gray-900">{sensor.sensorId}</h3>
                      <p className="text-sm text-gray-500">{sensor.type}传感器</p>
                    </div>
                    <span
                      className={`px-2 py-1 text-xs rounded-full ${
                        sensor.status === 'running'
                          ? 'bg-green-100 text-green-800'
                          : 'bg-red-100 text-red-800'
                      }`}
                    >
                      {sensor.status === 'running' ? '运行中' : '已停止'}
                    </span>
                  </div>
                  <div className="mt-3">
                    <p className="text-xs text-gray-500">最后活跃: {sensor.lastActiveTime ? new Date(sensor.lastActiveTime).toLocaleString() : 'N/A'}</p>
                    <p className="text-xs text-gray-500">数据来源: {sensor.dataSource === 'simulation' ? '模拟' : '真实'}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-gray-500">暂无传感器数据</p>
            </div>
          )}
        </div>
      </div>

      {/* 系统说明 */}
      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-md p-4">
        <h3 className="text-md font-semibold text-blue-800 mb-2">系统说明</h3>
        <ul className="list-disc pl-5 space-y-1 text-sm text-blue-700">
          <li>系统状态显示整体服务运行情况</li>
          <li>传感器状态显示各个传感器的运行情况</li>
          <li>测试通过率和今日测试数反映系统测试效率</li>
          <li>MQTT连接状态影响传感器数据的接收</li>
          <li>页面数据每30秒自动刷新一次</li>
        </ul>
      </div>
    </div>
  );
};

export default Dashboard;