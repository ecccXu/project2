import React, { useEffect, useState } from 'react';
import { useAppStore } from '../stores';
import { TestCase, TestResult } from '../utils/types';

const TestExecution: React.FC = () => {
  const {
    testCases,
    loadingTestCases,
    realtimeResults,
    loadingRealtimeResults,
    realtimeResultsError,
    fetchTestCases,
    startTest,
    fetchRealtimeResults,
    exportReport
  } = useAppStore();

  const [selectedSensor, setSelectedSensor] = useState<string>('all');
  const [selectedCases, setSelectedCases] = useState<string[]>([]);
  const [isStartingTest, setIsStartingTest] = useState(false);
  const [exportFormat, setExportFormat] = useState<'pdf' | 'excel'>('pdf');

  useEffect(() => {
    fetchTestCases();
    // 每5秒自动获取一次实时结果
    const interval = setInterval(() => {
      fetchRealtimeResults();
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  const toggleTestCase = (caseId: string) => {
    if (selectedCases.includes(caseId)) {
      setSelectedCases(selectedCases.filter(id => id !== caseId));
    } else {
      setSelectedCases([...selectedCases, caseId]);
    }
  };

  const handleStartTest = async () => {
    if (selectedCases.length === 0) {
      alert('请至少选择一个测试用例');
      return;
    }

    setIsStartingTest(true);
    try {
      await startTest({
        sensorId: selectedSensor,
        caseIds: selectedCases
      });
    } catch (error) {
      console.error('开始测试失败:', error);
    } finally {
      setIsStartingTest(false);
    }
  };

  const handleExportReport = async () => {
    try {
      await exportReport({ format: exportFormat });
    } catch (error) {
      console.error('导出报告失败:', error);
    }
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-800">测试执行</h1>
        <div className="flex space-x-2">
          <select
            value={exportFormat}
            onChange={(e) => setExportFormat(e.target.value as 'pdf' | 'excel')}
            className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="pdf">PDF格式</option>
            <option value="excel">Excel格式</option>
          </select>
          <button
            onClick={handleExportReport}
            className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-md"
          >
            导出报告
          </button>
        </div>
      </div>

      {/* 错误信息显示 */}
      {realtimeResultsError && (
        <div className="mb-6 p-4 bg-red-100 border border-red-400 text-red-700 rounded-md">
          <p>获取实时结果时发生错误：{realtimeResultsError}</p>
        </div>
      )}

      {/* 测试控制面板 */}
      <div className="bg-white p-4 rounded-md shadow-md mb-6">
        <h2 className="text-lg font-semibold mb-3">测试控制</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              选择传感器
            </label>
            <select
              value={selectedSensor}
              onChange={(e) => setSelectedSensor(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">所有传感器</option>
              {/* 从store获取传感器列表 */}
              {/* 暂时使用静态选项，实际应用中应从store获取 */}
              <option value="DHT11-001">DHT11-001</option>
              <option value="DHT11-002">DHT11-002</option>
              <option value="DHT11-003">DHT11-003</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              选择测试用例
            </label>
            <div className="h-32 overflow-y-auto border border-gray-300 rounded-md p-2">
              {loadingTestCases ? (
                <p className="text-center py-4">加载中...</p>
              ) : testCases.length === 0 ? (
                <p className="text-center py-4">暂无测试用例</p>
              ) : (
                testCases.map((testCase) => (
                  <div key={testCase.caseId} className="flex items-center mb-2">
                    <input
                      type="checkbox"
                      id={testCase.caseId}
                      checked={selectedCases.includes(testCase.caseId)}
                      onChange={() => toggleTestCase(testCase.caseId)}
                      className="h-4 w-4 text-blue-600 rounded focus:ring-blue-500"
                    />
                    <label htmlFor={testCase.caseId} className="ml-2 text-sm text-gray-700">
                      {testCase.name}
                    </label>
                  </div>
                ))
              )}
            </div>
          </div>
          <div className="flex flex-col justify-end">
            <button
              onClick={handleStartTest}
              disabled={isStartingTest || selectedCases.length === 0}
              className="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-md disabled:opacity-50"
            >
              {isStartingTest ? '测试启动中...' : '开始测试'}
            </button>
          </div>
        </div>
      </div>

      {/* 实时测试结果 */}
      <div className="bg-white rounded-md shadow-md overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-800">实时测试结果</h2>
        </div>
        {loadingRealtimeResults ? (
          <div className="p-6 text-center">加载实时结果中...</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    时间戳
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
                    详情
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {realtimeResults.length > 0 ? (
                  realtimeResults.map((result, index) => (
                    <tr key={index} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {result.timestamp ? new Date(result.timestamp).toLocaleString() : 'N/A'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
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
                      <td className="px-6 py-4 text-sm text-gray-500 max-w-xs">
                        {result.details}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={5} className="px-6 py-4 text-center text-sm text-gray-500">
                      暂无实时测试结果
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 测试说明 */}
      <div className="mt-6 bg-yellow-50 border border-yellow-200 rounded-md p-4">
        <h3 className="text-md font-semibold text-yellow-800 mb-2">测试执行说明</h3>
        <ul className="list-disc pl-5 space-y-1 text-sm text-yellow-700">
          <li>选择要测试的传感器和测试用例，点击"开始测试"按钮启动测试</li>
          <li>实时结果会自动更新，每5秒刷新一次</li>
          <li>测试完成后可以导出测试报告</li>
          <li>测试结果会显示通过或失败状态及详细信息</li>
        </ul>
      </div>
    </div>
  );
};

export default TestExecution;