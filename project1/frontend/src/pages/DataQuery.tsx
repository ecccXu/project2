import React, { useEffect, useState } from 'react';
import { useAppStore } from '../stores';
import { TestResultResponse, SensorData } from '../utils/types';

const DataQuery: React.FC = () => {
  const {
    testResults,
    sensorData,
    loadingTestResults,
    loadingSensorData,
    testResultsError,
    sensorDataError,
    fetchTestResults,
    fetchSensorData,
    exportSensorData,
    generateChart
  } = useAppStore();

  const [activeTab, setActiveTab] = useState<'test' | 'sensor'>('test');
  const [testQuery, setTestQuery] = useState({
    sensorId: '',
    startTime: '',
    endTime: '',
    page: 1,
    pageSize: 10
  });
  const [sensorQuery, setSensorQuery] = useState({
    sensorId: '',
    source: '' as 'simulation' | 'real' | '',
    startTime: '',
    endTime: '',
    page: 1,
    pageSize: 10
  });
  const [chartParams, setChartParams] = useState({
    sensorId: '',
    metric: 'temperature' as 'temperature' | 'humidity',
    startTime: '',
    endTime: ''
  });
  const [showChartModal, setShowChartModal] = useState(false);
  const [chartUrl, setChartUrl] = useState('');

  useEffect(() => {
    if (activeTab === 'test') {
      fetchTestResults(testQuery);
    } else {
      fetchSensorData(sensorQuery);
    }
  }, [activeTab]);

  const handleTestQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await fetchTestResults(testQuery);
    } catch (error) {
      console.error('查询测试结果失败:', error);
    }
  };

  const handleSensorQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await fetchSensorData(sensorQuery);
    } catch (error) {
      console.error('查询传感器数据失败:', error);
    }
  };

  const handleExportSensorData = async () => {
    const { sensorId, source, startTime, endTime } = sensorQuery;
    try {
      await exportSensorData({
        sensorId: sensorId || undefined,
        source: source || undefined,
        startTime: startTime || undefined,
        endTime: endTime || undefined
      });
    } catch (error) {
      console.error('导出传感器数据失败:', error);
    }
  };

  const handleGenerateChart = async () => {
    if (!chartParams.sensorId || !chartParams.startTime || !chartParams.endTime) {
      alert('请填写完整的图表生成参数');
      return;
    }

    try {
      const result = await generateChart(chartParams);
      if (result) {
        setChartUrl(result.chartUrl);
        setShowChartModal(true);
      }
    } catch (error) {
      console.error('生成图表失败:', error);
    }
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-800">数据查询</h1>
      </div>

      {/* 错误信息显示 */}
      {(testResultsError || sensorDataError) && (
        <div className="mb-6 p-4 bg-red-100 border border-red-400 text-red-700 rounded-md">
          <p>发生错误：</p>
          {testResultsError && <p>测试结果查询错误：{testResultsError}</p>}
          {sensorDataError && <p>传感器数据查询错误：{sensorDataError}</p>}
        </div>
      )}

      {/* 选项卡 */}
      <div className="mb-6 border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('test')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'test'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            测试结果
          </button>
          <button
            onClick={() => setActiveTab('sensor')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'sensor'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            传感器数据
          </button>
        </nav>
      </div>

      {/* 测试结果查询 */}
      {activeTab === 'test' && (
        <div>
          <div className="bg-white p-4 rounded-md shadow-md mb-6">
            <h2 className="text-lg font-semibold mb-3">查询测试结果</h2>
            <form onSubmit={handleTestQuery} className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  传感器ID
                </label>
                <input
                  type="text"
                  value={testQuery.sensorId}
                  onChange={(e) => setTestQuery({...testQuery, sensorId: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="如: DHT11-001"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  开始时间
                </label>
                <input
                  type="datetime-local"
                  value={testQuery.startTime}
                  onChange={(e) => setTestQuery({...testQuery, startTime: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  结束时间
                </label>
                <input
                  type="datetime-local"
                  value={testQuery.endTime}
                  onChange={(e) => setTestQuery({...testQuery, endTime: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div className="flex items-end">
                <button
                  type="submit"
                  className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-md w-full"
                >
                  查询
                </button>
              </div>
            </form>
          </div>

          <div className="bg-white rounded-md shadow-md overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-800">测试结果列表</h2>
            </div>
            {loadingTestResults ? (
              <div className="p-6 text-center">加载中...</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        测试ID
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        传感器ID
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        测试用例
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        结果
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        测试时间
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        详情
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {testResults.length > 0 ? (
                      testResults.map((result, index) => (
                        <tr key={index} className="hover:bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                            {result.testId}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {result.sensorId}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {result.caseName || result.caseId}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span
                              className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                                result.result === 'pass'
                                  ? 'bg-green-100 text-green-800'
                                  : 'bg-red-100 text-red-800'
                              }`}
                            >
                              {result.result === 'pass' ? '通过' : '失败'}
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {result.testTime ? new Date(result.testTime).toLocaleString() : 'N/A'}
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-500 max-w-xs">
                            {result.details}
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={6} className="px-6 py-4 text-center text-sm text-gray-500">
                          暂无测试结果
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 传感器数据查询 */}
      {activeTab === 'sensor' && (
        <div>
          <div className="bg-white p-4 rounded-md shadow-md mb-6">
            <h2 className="text-lg font-semibold mb-3">查询传感器数据</h2>
            <form onSubmit={handleSensorQuery} className="grid grid-cols-1 md:grid-cols-5 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  传感器ID
                </label>
                <input
                  type="text"
                  value={sensorQuery.sensorId}
                  onChange={(e) => setSensorQuery({...sensorQuery, sensorId: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="如: DHT11-001"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  数据来源
                </label>
                <select
                  value={sensorQuery.source}
                  onChange={(e) => setSensorQuery({...sensorQuery, source: e.target.value as 'simulation' | 'real' | ''})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">全部</option>
                  <option value="simulation">模拟</option>
                  <option value="real">真实</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  开始时间
                </label>
                <input
                  type="datetime-local"
                  value={sensorQuery.startTime}
                  onChange={(e) => setSensorQuery({...sensorQuery, startTime: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  结束时间
                </label>
                <input
                  type="datetime-local"
                  value={sensorQuery.endTime}
                  onChange={(e) => setSensorQuery({...sensorQuery, endTime: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div className="flex items-end">
                <div className="flex space-x-2 w-full">
                  <button
                    type="submit"
                    className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-md flex-1"
                  >
                    查询
                  </button>
                  <button
                    type="button"
                    onClick={handleExportSensorData}
                    className="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-md"
                  >
                    导出
                  </button>
                </div>
              </div>
            </form>
          </div>

          {/* 图表生成 */}
          <div className="bg-white p-4 rounded-md shadow-md mb-6">
            <h2 className="text-lg font-semibold mb-3">生成数据图表</h2>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  传感器ID
                </label>
                <input
                  type="text"
                  value={chartParams.sensorId}
                  onChange={(e) => setChartParams({...chartParams, sensorId: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="如: DHT11-001"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  指标类型
                </label>
                <select
                  value={chartParams.metric}
                  onChange={(e) => setChartParams({...chartParams, metric: e.target.value as 'temperature' | 'humidity'})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="temperature">温度</option>
                  <option value="humidity">湿度</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  开始时间
                </label>
                <input
                  type="datetime-local"
                  value={chartParams.startTime}
                  onChange={(e) => setChartParams({...chartParams, startTime: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div className="flex items-end">
                <button
                  onClick={handleGenerateChart}
                  className="bg-purple-500 hover:bg-purple-600 text-white px-4 py-2 rounded-md w-full"
                >
                  生成图表
                </button>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-md shadow-md overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-800">传感器数据列表</h2>
            </div>
            {loadingSensorData ? (
              <div className="p-6 text-center">加载中...</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        数据ID
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        传感器ID
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        温度 (℃)
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        湿度 (%)
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        接收时间
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        数据来源
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {sensorData.length > 0 ? (
                      sensorData.map((data, index) => (
                        <tr key={index} className="hover:bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                            {data.dataId}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {data.sensorId}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {data.temperature !== undefined ? `${data.temperature}℃` : 'N/A'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {data.humidity !== undefined ? `${data.humidity}%` : 'N/A'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {data.receiveTime ? new Date(data.receiveTime).toLocaleString() : 'N/A'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span
                              className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                                data.source === 'simulation'
                                  ? 'bg-blue-100 text-blue-800'
                                  : 'bg-yellow-100 text-yellow-800'
                              }`}
                            >
                              {data.source === 'simulation' ? '模拟' : '真实'}
                            </span>
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={6} className="px-6 py-4 text-center text-sm text-gray-500">
                          暂无传感器数据
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 图表模态框 */}
      {showChartModal && chartUrl && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50" onClick={() => setShowChartModal(false)}>
          <div className="relative top-20 mx-auto p-5 border w-11/12 max-w-4xl shadow-lg rounded-md bg-white" onClick={(e) => e.stopPropagation()}>
            <div className="mt-3">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold text-gray-800">数据图表</h3>
                <button
                  onClick={() => setShowChartModal(false)}
                  className="text-gray-500 hover:text-gray-700"
                >
                  <span className="text-2xl">&times;</span>
                </button>
              </div>
              <div className="p-4">
                <img src={chartUrl} alt="数据图表" className="w-full h-auto" />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DataQuery;