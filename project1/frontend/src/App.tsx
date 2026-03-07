import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Sensors from './pages/Sensors';
import MQTTConfig from './pages/MQTTConfig';
import TestExecution from './pages/TestExecution';
import DataQuery from './pages/DataQuery';
import SystemStatus from './pages/SystemStatus';

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/sensors" element={<Sensors />} />
          <Route path="/mqtt-config" element={<MQTTConfig />} />
          <Route path="/test-execution" element={<TestExecution />} />
          <Route path="/data-query" element={<DataQuery />} />
          <Route path="/system-status" element={<SystemStatus />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;