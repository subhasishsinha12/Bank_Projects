import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import HomeDashboard from './components/HomeDashboard';
import XAIDashboard from './components/viveka/XAIDashboard';
import FairnessAudit from './components/viveka/FairnessAudit';
import BorrowerExplain from './components/viveka/BorrowerExplain';
import ModelInventory from './components/raksha/ModelInventory';
import ComplianceScorecard from './components/raksha/ComplianceScorecard';
import ValidationWorkflow from './components/raksha/ValidationWorkflow';
import EWSDashboard from './components/satya/EWSDashboard';
import PortfolioView from './components/satya/PortfolioView';
import PSIMonitor from './components/satya/PSIMonitor';
import BorrowerDetail from './components/satya/BorrowerDetail';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<HomeDashboard />} />
          <Route path="viveka" element={<XAIDashboard />} />
          <Route path="viveka/fairness" element={<FairnessAudit />} />
          <Route path="viveka/explain/:id" element={<BorrowerExplain />} />
          <Route path="raksha" element={<ModelInventory />} />
          <Route path="raksha/compliance" element={<ComplianceScorecard />} />
          <Route path="raksha/workflow" element={<ValidationWorkflow />} />
          <Route path="satya" element={<EWSDashboard />} />
          <Route path="satya/portfolio" element={<PortfolioView />} />
          <Route path="satya/psi" element={<PSIMonitor />} />
          <Route path="satya/borrower/:id" element={<BorrowerDetail />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
