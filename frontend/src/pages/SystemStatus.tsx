import React, { useEffect } from 'react';
import { useAppStore } from '../stores';
import { FaServer, FaWifi, FaMicrochip, FaCheckCircle, FaExclamationTriangle } from 'react-icons/fa';

const SystemStatus: React.FC = () => {
  const {
    systemStatus,
    loadingSystemStatus,
    systemStatusError,
    fetchSystemStatus
  } = useAppStore();

  useEffect(() => {
    fetchSystemStatus();
    
    // 设置定时刷新（每10秒刷新一次）
    const interval = setInterval(() => {
      fetchSystemStatus();
    }, 10000);

    return () => clearInterval(interval);
  }, []);

  const getStatusIcon = (status: string | undefined) => {
    if (loadingSystemStatus) return <FaExclamationTriangle className="text-yellow-500 text-xl" />;
    if (!status) return <FaExclamationTriangle className="text-gray-500 text-xl" />;
    
    return status === 'online' 
      ? <FaServer className="text-green-500 text-xl" />
      : <FaServer className="text-red-500 text-xl" />;
  };

  const getMqttStatusIcon = (status: string | undefined) => {
    if (loadingSystemStatus) return <FaExclamationTriangle className="text-yellow-500 text-xl" />;
    if (!status) return <FaExclamationTriangle className="text-gray-500 text-xl" />;
    
    return status === 'connected' 
      ? <FaWifi className="text-green-500 text-xl" />
      : <FaWifi className="text-red-500 text-xl" />;
  };

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800">系统状态</h1>
        <p className="text-gray-600">实时监控系统各项指标</p>
      </div>

      {/* 错误信息显示 */}
      {systemStatusError && (
        <div className="mb-6 p-4 bg-red-100 border border-red-400 text-red-700 rounded-md">
          <p>获取系统状态时发生错误：{systemStatusError}</p>
        </div>
      )}

      {/* 状态卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
        <div className="bg-white p-6 rounded-md shadow-md">
          <div className="flex items-center">
            <div className="p-3 rounded-full bg-blue-100">
              {getStatusIcon(systemStatus?.systemStatus)}
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
              <p className="text-sm font-medium text-gray-600">已连接传感器</p>
              {loadingSystemStatus ? (
                <p className="text-2xl font-semibold text-gray-900">加载中...</p>
              ) : systemStatus ? (
                <p className="text-2xl font-semibold text-gray-900">{systemStatus.connectedSensors}</p>
              ) : (
                <p className="text-2xl font-semibold text-gray-900">0</p>
              )}
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
              {getMqttStatusIcon(systemStatus?.mqttConnectionStatus)}
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">MQTT连接</p>
              {loadingSystemStatus ? (
                <p className="text-2xl font-semibold text-gray-900">加载中...</p>
              ) : systemStatus ? (
                <p className={`text-2xl font-semibold ${systemStatus.mqttConnectionStatus === 'connected' ? 'text-green-600' : 'text-red-600'}`}>
                  {systemStatus.mqttConnectionStatus === 'connected' ? '已连接' : '未连接'}
                </p>
              ) : (
                <p className="text-2xl font-semibold text-gray-900">未知</p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 详细信息卡片 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-md shadow-md">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">系统详情</h2>
          <div className="space-y-4">
            <div>
              <p className="text-sm font-medium text-gray-600">系统状态</p>
              <p className="text-gray-900">
                {loadingSystemStatus 
                  ? '加载中...' 
                  : systemStatus 
                    ? systemStatus.systemStatus === 'online' 
                      ? '系统运行正常' 
                      : '系统处于离线状态'
                    : '无法获取状态'}
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600">连接的传感器数量</p>
              <p className="text-gray-900">
                {loadingSystemStatus 
                  ? '加载中...' 
                  : systemStatus 
                    ? `${systemStatus.connectedSensors} 个传感器已连接`
                    : '无法获取传感器数量'}
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600">今日测试总数</p>
              <p className="text-gray-900">
                {loadingSystemStatus 
                  ? '加载中...' 
                  : systemStatus 
                    ? `${systemStatus.todayTestCount} 次测试`
                    : '无法获取测试数量'}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-md shadow-md">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">MQTT详情</h2>
          <div className="space-y-4">
            <div>
              <p className="text-sm font-medium text-gray-600">MQTT连接状态</p>
              <p className={`text-gray-900 ${
                loadingSystemStatus 
                  ? '' 
                  : systemStatus 
                    ? systemStatus.mqttConnectionStatus === 'connected' 
                      ? 'text-green-600' 
                      : 'text-red-600'
                    : ''
              }`}>
                {loadingSystemStatus 
                  ? '加载中...' 
                  : systemStatus 
                    ? systemStatus.mqttConnectionStatus === 'connected' 
                      ? 'MQTT Broker连接正常' 
                      : 'MQTT Broker未连接'
                    : '无法获取MQTT状态'}
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600">数据接收</p>
              <p className="text-gray-900">
                {loadingSystemStatus 
                  ? '加载中...' 
                  : systemStatus 
                    ? systemStatus.mqttConnectionStatus === 'connected' 
                      ? '正在接收传感器数据' 
                      : '无法接收传感器数据'
                    : '无法获取数据接收状态'}
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600">连接说明</p>
              <p className="text-gray-900 text-sm text-gray-600">
                MQTT连接是传感器数据传输的关键，确保Broker配置正确且网络连接正常。
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* 状态说明 */}
      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-md p-4">
        <h3 className="text-md font-semibold text-blue-800 mb-2">系统状态说明</h3>
        <ul className="list-disc pl-5 space-y-1 text-sm text-blue-700">
          <li>系统状态每10秒自动刷新一次</li>
          <li>在线状态表示系统服务正常运行</li>
          <li>MQTT连接状态影响传感器数据的接收</li>
          <li>测试通过率反映了传感器测试的准确性</li>
          <li>如发现状态异常，请检查后端服务和网络连接</li>
        </ul>
      </div>
    </div>
  );
};

export default SystemStatus;