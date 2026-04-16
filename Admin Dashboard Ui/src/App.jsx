import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AdminLayout } from './components/layout/AdminLayout';

// Pages
import Dashboard from './pages/Dashboard';
import Workers from './pages/Workers';
import Kyc from './pages/Kyc';
import Subscriptions from './pages/Subscriptions';
import Claims from './pages/Claims';
import Payouts from './pages/Payouts';
import Fraud from './pages/Fraud';
import Isolation from './pages/Isolation';
import Zones from './pages/Zones';
import Actuarial from './pages/Actuarial';
import Platform from './pages/Platform';
import Config from './pages/Config';
import PredictiveAnalytics from './pages/PredictiveAnalytics';
import StressTest from './pages/StressTest';

const App = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AdminLayout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/workers" element={<Workers />} />
          <Route path="/kyc" element={<Kyc />} />
          <Route path="/subscriptions" element={<Subscriptions />} />
          <Route path="/claims" element={<Claims />} />
          <Route path="/payouts" element={<Payouts />} />
          <Route path="/fraud" element={<Fraud />} />
          <Route path="/isolation" element={<Isolation />} />
          <Route path="/zones" element={<Zones />} />
          <Route path="/actuarial" element={<Actuarial />} />
          <Route path="/predictive" element={<PredictiveAnalytics />} />
          <Route path="/stress-test" element={<StressTest />} />
          <Route path="/platform" element={<Platform />} />
          <Route path="/config" element={<Config />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;