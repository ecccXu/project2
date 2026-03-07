import React, { useEffect, useState } from 'react';
import { useAppStore } from '../stores';
import { Sensor } from '../utils/types';

const Sensors: React.FC = () => {
  const {
    sensors,
    loadingSensors,
    sensorConfig,
    loadingSensorConfig,
    sensorsError,
    sensorConfigError,
    fetchSensors,
    fetchSensorConfig,
    addSensor,
    deleteSensor,
    updateSensorStatus,
    updateSensorConfig
  } = useAppStore();

  const [showAddForm, setShowAddForm] = useState(false);
  const [newSensor, setNewSensor] = useState<Omit<Sensor, 'lastActiveTime'>>({
    sensorId: '',
    type: '温湿度',
    status: 'stopped',
    description: '',
    dataSource: 'simulation'
  });

  const [editingConfig, setEditingConfig] = useState<any>(null);

  useEffect(() => {
    fetchSensors();
    fetchSensorConfig();
  }, []);

  const handleAddSensor = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await addSensor(newSensor);
      setNewSensor({
        sensorId: '',
        type: '温湿度',
        status: 'stopped',
        description: '',
        dataSource: 'simulation'
      });
      setShowAddForm(false);
    } catch (error) {
      console.error('添加传感器失败:', error);
    }
  };

  const handleDeleteSensor = async (sensorId: string) => {
    if (window.confirm(`确定要删除传感器 ${sensorId} 吗？`)) {
      try {
        await deleteSensor(sensorId);
      } catch (error) {
        console.error('删除传感器失败:', error);
      }
    }
  };

  const toggleSensorStatus = async (sensor: Sensor) => {
    const newStatus = sensor.status === 'running' ? 'stopped' : 'running';
    try {
      await updateSensorStatus(sensor.sensorId, newStatus);
    } catch (error) {
      console.error('更新传感器状态失败:', error);
    }
  };

  const handleConfigChange = (field: string, value: any) => {
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
        await updateSensorConfig(editingConfig);
        setEditingConfig(null);
      } catch (error) {
        console.error('保存传感器配置失败:', error);
      }
    }
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-800">传感器管理</h1>
        <button
          onClick={() => setShowAddForm(true)}
          className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-md transition-colors"
        >
          添加传感器
        </button>
      </div>

      {/* 错误信息显示 */}
      {(sensorsError || sensorConfigError) && (
        <div className="mb-6 p-4 bg-red-100 border border-red-400 text-red-700 rounded-md">
          <p>发生错误：</p>
          {sensorsError && <p>{sensorsError}</p>}
          {sensorConfigError && <p>{sensorConfigError}</p>}
        </div>
      )}

      {/* 添加传感器表单 */}
      {showAddForm && (
        <div className="bg-white p-4 rounded-md shadow-md mb-6">
          <h2 className="text-lg font-semibold mb-3">添加新传感器</h2>
          <form onSubmit={handleAddSensor}>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  传感器ID
                </label>
                <input
                  type="text"
                  value={newSensor.sensorId}
                  onChange={(e) => setNewSensor({...newSensor, sensorId: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="如: DHT11-001"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  传感器类型
                </label>
                <select
                  value={newSensor.type}
                  onChange={(e) => setNewSensor({...newSensor, type: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="温湿度">温湿度</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  数据来源
                </label>
                <select
                  value={newSensor.dataSource}
                  onChange={(e) => setNewSensor({...newSensor, dataSource: e.target.value as 'simulation' | 'real'})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="simulation">模拟</option>
                  <option value="real">真实</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  描述
                </label>
                <input
                  type="text"
                  value={newSensor.description}
                  onChange={(e) => setNewSensor({...newSensor, description: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="传感器描述"
                />
              </div>
            </div>
            <div className="mt-4 flex space-x-2">
              <button
                type="submit"
                className="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-md"
              >
                添加
              </button>
              <button
                type="button"
                onClick={() => setShowAddForm(false)}
                className="bg-gray-500 hover:bg-gray-600 text-white px-4 py-2 rounded-md"
              >
                取消
              </button>
            </div>
          </form>
        </div>
      )}

      {/* 传感器配置编辑 */}
      {sensorConfig && !editingConfig && (
        <div className="bg-white p-4 rounded-md shadow-md mb-6">
          <div className="flex justify-between items-center mb-3">
            <h2 className="text-lg font-semibold">传感器配置</h2>
            <button
              onClick={() => setEditingConfig({...sensorConfig})}
              className="text-blue-500 hover:text-blue-700"
            >
              编辑配置
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-3 bg-gray-50 rounded">
              <p className="text-sm text-gray-600">数据来源模式</p>
              <p className="font-medium">{sensorConfig.dataSource}</p>
            </div>
            <div className="p-3 bg-gray-50 rounded">
              <p className="text-sm text-gray-600">采集频率</p>
              <p className="font-medium">{sensorConfig.sampleRate} 秒</p>
            </div>
            <div className="p-3 bg-gray-50 rounded">
              <p className="text-sm text-gray-600">温度范围</p>
              <p className="font-medium">{sensorConfig.temperatureRange.min} ~ {sensorConfig.temperatureRange.max} ℃</p>
            </div>
            <div className="p-3 bg-gray-50 rounded">
              <p className="text-sm text-gray-600">湿度范围</p>
              <p className="font-medium">{sensorConfig.humidityRange.min} ~ {sensorConfig.humidityRange.max} %</p>
            </div>
          </div>
        </div>
      )}

      {/* 编辑传感器配置表单 */}
      {editingConfig && (
        <div className="bg-white p-4 rounded-md shadow-md mb-6">
          <h2 className="text-lg font-semibold mb-3">编辑传感器配置</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                数据来源模式
              </label>
              <select
                value={editingConfig.dataSource}
                onChange={(e) => handleConfigChange('dataSource', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="simulation">模拟</option>
                <option value="real">真实</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                采集频率（秒）
              </label>
              <input
                type="number"
                min="1"
                max="10"
                value={editingConfig.sampleRate}
                onChange={(e) => handleConfigChange('sampleRate', parseInt(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                温度最小值（℃）
              </label>
              <input
                type="number"
                value={editingConfig.temperatureRange.min}
                onChange={(e) => handleConfigChange('temperatureRange', {
                  ...editingConfig.temperatureRange,
                  min: parseInt(e.target.value)
                })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                温度最大值（℃）
              </label>
              <input
                type="number"
                value={editingConfig.temperatureRange.max}
                onChange={(e) => handleConfigChange('temperatureRange', {
                  ...editingConfig.temperatureRange,
                  max: parseInt(e.target.value)
                })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                湿度最小值（%）
              </label>
              <input
                type="number"
                value={editingConfig.humidityRange.min}
                onChange={(e) => handleConfigChange('humidityRange', {
                  ...editingConfig.humidityRange,
                  min: parseInt(e.target.value)
                })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                湿度最大值（%）
              </label>
              <input
                type="number"
                value={editingConfig.humidityRange.max}
                onChange={(e) => handleConfigChange('humidityRange', {
                  ...editingConfig.humidityRange,
                  max: parseInt(e.target.value)
                })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
          <div className="mt-4 flex space-x-2">
            <button
              onClick={handleSaveConfig}
              className="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-md"
            >
              保存
            </button>
            <button
              onClick={() => setEditingConfig(null)}
              className="bg-gray-500 hover:bg-gray-600 text-white px-4 py-2 rounded-md"
            >
              取消
            </button>
          </div>
        </div>
      )}

      {/* 传感器列表 */}
      <div className="bg-white rounded-md shadow-md overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-800">传感器列表</h2>
        </div>
        {loadingSensors ? (
          <div className="p-6 text-center">加载中...</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    传感器ID
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    类型
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    状态
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    最后活跃时间
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    数据来源
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    描述
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    操作
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {sensors.map((sensor) => (
                  <tr key={sensor.sensorId} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">{sensor.sensorId}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-500">{sensor.type}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                          sensor.status === 'running'
                            ? 'bg-green-100 text-green-800'
                            : 'bg-red-100 text-red-800'
                        }`}
                      >
                        {sensor.status === 'running' ? '运行中' : '已停止'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {sensor.lastActiveTime ? new Date(sensor.lastActiveTime).toLocaleString() : 'N/A'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {sensor.dataSource === 'simulation' ? '模拟' : '真实'}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {sensor.description}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <button
                        onClick={() => toggleSensorStatus(sensor)}
                        className={`mr-2 ${
                          sensor.status === 'running'
                            ? 'text-red-600 hover:text-red-900'
                            : 'text-green-600 hover:text-green-900'
                        }`}
                      >
                        {sensor.status === 'running' ? '停止' : '启动'}
                      </button>
                      <button
                        onClick={() => handleDeleteSensor(sensor.sensorId)}
                        className="text-red-600 hover:text-red-900"
                      >
                        删除
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {sensors.length === 0 && !loadingSensors && (
          <div className="p-6 text-center text-gray-500">暂无传感器数据</div>
        )}
      </div>
    </div>
  );
};

export default Sensors;