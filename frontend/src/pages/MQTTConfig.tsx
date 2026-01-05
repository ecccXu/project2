import React, { useEffect, useState } from 'react';
import { useAppStore } from '../stores';
import { MqttConfig } from '../utils/types';

const MQTTConfig: React.FC = () => {
  const {
    mqttConfig,
    loadingMqttConfig,
    mqttConnectionStatus,
    mqttTestResult,
    mqttConfigError,
    fetchMqttConfig,
    updateMqttConfig,
    testMqttConnection,
    connectToMqtt,
    disconnectMqtt
  } = useAppStore();

  const [editingConfig, setEditingConfig] = useState<MqttConfig | null>(null);
  const [isTesting, setIsTesting] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);

  useEffect(() => {
    fetchMqttConfig();
  }, []);

  const handleConfigChange = (field: keyof MqttConfig, value: any) => {
    if (editingConfig) {
      setEditingConfig({
        ...editingConfig,
        [field]: value
      });
    }
  };

  const handleSaveConfig = async () => {
    if (editingConfig) {
      try {
        await updateMqttConfig(editingConfig);
        setEditingConfig(null);
      } catch (error) {
        console.error('保存MQTT配置失败:', error);
      }
    }
  };

  const handleTestConnection = async () => {
    if (editingConfig) {
      setIsTesting(true);
      try {
        await testMqttConnection(editingConfig);
      } catch (error) {
        console.error('测试MQTT连接失败:', error);
      } finally {
        setIsTesting(false);
      }
    } else if (mqttConfig) {
      setIsTesting(true);
      try {
        await testMqttConnection(mqttConfig);
      } catch (error) {
        console.error('测试MQTT连接失败:', error);
      } finally {
        setIsTesting(false);
      }
    }
  };

  const handleConnect = async () => {
    if (editingConfig) {
      setIsConnecting(true);
      try {
        await connectToMqtt(editingConfig);
      } catch (error) {
        console.error('连接MQTT失败:', error);
      } finally {
        setIsConnecting(false);
      }
    } else if (mqttConfig) {
      setIsConnecting(true);
      try {
        await connectToMqtt(mqttConfig);
      } catch (error) {
        console.error('连接MQTT失败:', error);
      } finally {
        setIsConnecting(false);
      }
    }
  };

  const handleDisconnect = () => {
    disconnectMqtt();
  };

  const getStatusColor = () => {
    switch (mqttConnectionStatus) {
      case 'connected':
        return 'bg-green-100 text-green-800';
      case 'connecting':
        return 'bg-yellow-100 text-yellow-800';
      case 'error':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusText = () => {
    switch (mqttConnectionStatus) {
      case 'connected':
        return '已连接';
      case 'connecting':
        return '连接中...';
      case 'disconnected':
        return '未连接';
      case 'error':
        return '连接错误';
      default:
        return '未知';
    }
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-800">MQTT配置</h1>
        <div className="flex items-center space-x-2">
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor()}`}>
            状态: {getStatusText()}
          </span>
          {mqttConnectionStatus === 'connected' || mqttConnectionStatus === 'connecting' ? (
            <button
              onClick={handleDisconnect}
              disabled={mqttConnectionStatus === 'connecting'}
              className="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-md disabled:opacity-50"
            >
              断开连接
            </button>
          ) : (
            <button
              onClick={handleConnect}
              disabled={isConnecting || !editingConfig && !mqttConfig}
              className="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-md disabled:opacity-50"
            >
              {isConnecting ? '连接中...' : '连接MQTT'}
            </button>
          )}
        </div>
      </div>

      {/* 错误信息显示 */}
      {mqttConfigError && (
        <div className="mb-6 p-4 bg-red-100 border border-red-400 text-red-700 rounded-md">
          <p>发生错误：{mqttConfigError}</p>
        </div>
      )}

      {/* MQTT配置编辑 */}
      {mqttConfig && !editingConfig && (
        <div className="bg-white p-4 rounded-md shadow-md mb-6">
          <div className="flex justify-between items-center mb-3">
            <h2 className="text-lg font-semibold">MQTT配置</h2>
            <button
              onClick={() => setEditingConfig({ ...mqttConfig })}
              className="text-blue-500 hover:text-blue-700"
            >
              编辑配置
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-3 bg-gray-50 rounded">
              <p className="text-sm text-gray-600">Broker地址</p>
              <p className="font-medium">{mqttConfig.brokerHost}</p>
            </div>
            <div className="p-3 bg-gray-50 rounded">
              <p className="text-sm text-gray-600">Broker端口</p>
              <p className="font-medium">{mqttConfig.brokerPort}</p>
            </div>
            <div className="p-3 bg-gray-50 rounded">
              <p className="text-sm text-gray-600">客户端ID</p>
              <p className="font-medium">{mqttConfig.clientId}</p>
            </div>
            <div className="p-3 bg-gray-50 rounded">
              <p className="text-sm text-gray-600">Clean Session</p>
              <p className="font-medium">{mqttConfig.cleanSession ? '是' : '否'}</p>
            </div>
            <div className="p-3 bg-gray-50 rounded">
              <p className="text-sm text-gray-600">用户名</p>
              <p className="font-medium">{mqttConfig.username || '未设置'}</p>
            </div>
            <div className="p-3 bg-gray-50 rounded">
              <p className="text-sm text-gray-600">订阅主题</p>
              <p className="font-medium">{mqttConfig.subscribeTopic}</p>
            </div>
          </div>
        </div>
      )}

      {/* 编辑MQTT配置表单 */}
      {editingConfig && (
        <div className="bg-white p-4 rounded-md shadow-md mb-6">
          <h2 className="text-lg font-semibold mb-3">编辑MQTT配置</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Broker地址
              </label>
              <input
                type="text"
                value={editingConfig.brokerHost}
                onChange={(e) => handleConfigChange('brokerHost', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="localhost"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Broker端口
              </label>
              <input
                type="number"
                value={editingConfig.brokerPort}
                onChange={(e) => handleConfigChange('brokerPort', parseInt(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="1883"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                客户端ID
              </label>
              <input
                type="text"
                value={editingConfig.clientId}
                onChange={(e) => handleConfigChange('clientId', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="CarTest-Web-Client-12345"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Clean Session
              </label>
              <select
                value={editingConfig.cleanSession.toString()}
                onChange={(e) => handleConfigChange('cleanSession', e.target.value === 'true')}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="true">是</option>
                <option value="false">否</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                用户名（可选）
              </label>
              <input
                type="text"
                value={editingConfig.username}
                onChange={(e) => handleConfigChange('username', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="admin"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                密码（可选）
              </label>
              <input
                type="password"
                value={editingConfig.password}
                onChange={(e) => handleConfigChange('password', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="password"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                订阅主题
              </label>
              <input
                type="text"
                value={editingConfig.subscribeTopic}
                onChange={(e) => handleConfigChange('subscribeTopic', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="vehicle/sensor/data/+"
              />
            </div>
          </div>
          <div className="mt-4 flex space-x-2">
            <button
              onClick={handleSaveConfig}
              className="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-md"
            >
              保存配置
            </button>
            <button
              onClick={() => setEditingConfig(null)}
              className="bg-gray-500 hover:bg-gray-600 text-white px-4 py-2 rounded-md"
            >
              取消
            </button>
            <button
              onClick={handleTestConnection}
              disabled={isTesting}
              className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-md disabled:opacity-50"
            >
              {isTesting ? '测试中...' : '测试连接'}
            </button>
          </div>
        </div>
      )}

      {/* 连接测试结果 */}
      {mqttTestResult && (
        <div className="bg-white p-4 rounded-md shadow-md mb-6">
          <h2 className="text-lg font-semibold mb-3">连接测试结果</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-3 bg-gray-50 rounded">
              <p className="text-sm text-gray-600">连接状态</p>
              <p className={`font-medium ${mqttTestResult.connected ? 'text-green-600' : 'text-red-600'}`}>
                {mqttTestResult.connected ? '连接成功' : '连接失败'}
              </p>
            </div>
            <div className="p-3 bg-gray-50 rounded">
              <p className="text-sm text-gray-600">响应时间</p>
              <p className="font-medium">{mqttTestResult.responseTime} 毫秒</p>
            </div>
          </div>
        </div>
      )}

      {/* MQTT连接状态说明 */}
      <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
        <h3 className="text-md font-semibold text-blue-800 mb-2">MQTT连接说明</h3>
        <ul className="list-disc pl-5 space-y-1 text-sm text-blue-700">
          <li>配置正确的Broker地址和端口以建立连接</li>
          <li>如需认证，请填写用户名和密码</li>
          <li>订阅主题用于接收传感器数据</li>
          <li>连接成功后，系统将开始接收传感器数据</li>
        </ul>
      </div>
    </div>
  );
};

export default MQTTConfig;