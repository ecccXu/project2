import React, { useState } from 'react';
import { Link, Outlet } from 'react-router-dom';
import { FaTachometerAlt, FaMicrochip, FaNetworkWired, FaCogs, FaChartBar, FaDatabase, FaBars, FaTimes } from 'react-icons/fa';
import MQTTListener from './MQTTListener';

const Layout: React.FC<{ children?: React.ReactNode }> = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const menuItems = [
    { path: '/', icon: <FaTachometerAlt />, label: '仪表板' },
    { path: '/system-status', icon: <FaChartBar />, label: '系统状态' },
    { path: '/sensors', icon: <FaMicrochip />, label: '传感器管理' },
    { path: '/mqtt-config', icon: <FaNetworkWired />, label: 'MQTT配置' },
    { path: '/test-execution', icon: <FaCogs />, label: '测试执行' },
    { path: '/data-query', icon: <FaDatabase />, label: '数据查询' },
  ];

  return (
    <div className="flex h-screen bg-gray-100">
      <MQTTListener />
      {/* 侧边栏 */}
      <div 
        className={`bg-gray-800 text-white transition-all duration-300 ${
          sidebarOpen ? 'w-64' : 'w-20'
        }`}
      >
        <div className={`p-4 ${sidebarOpen ? 'block' : 'hidden'}`}>
          <h1 className="text-xl font-bold">车载传感器测试系统</h1>
        </div>
        <nav className="mt-6">
          <ul>
            {menuItems.map((item, index) => (
              <li key={index}>
                <Link
                  to={item.path}
                  className="flex items-center py-3 px-6 hover:bg-gray-700 transition-colors"
                >
                  <span className="text-lg">{item.icon}</span>
                  {sidebarOpen && (
                    <span className="ml-4 text-sm">{item.label}</span>
                  )}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      </div>

      {/* 主内容区 */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* 顶部栏 */}
        <header className="bg-white shadow-sm">
          <div className="flex items-center justify-between p-4">
            <button 
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="text-gray-500 focus:outline-none"
            >
              {sidebarOpen ? <FaTimes size={20} /> : <FaBars size={20} />}
            </button>
            <div className="flex items-center space-x-4">
              <span className="text-gray-700">管理员</span>
            </div>
          </div>
        </header>

        {/* 内容 */}
        <main className="flex-1 overflow-y-auto p-4">
          {children || <Outlet />}
        </main>
      </div>
    </div>
  );
};

export default Layout;