import React from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { useAuth } from "./contexts/AuthContext";
import BuyerDashboardPage from "./pages/BuyerDashboardPage.jsx";
import BuyerHome from "./pages/BuyerHome.jsx";
import CampaignDetailPage from "./pages/CampaignDetailPage.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import PartnerDashboardPage from "./pages/PartnerDashboardPage.jsx";
import PartnerHome from "./pages/PartnerHome.jsx";
import RegisterPage from "./pages/RegisterPage.jsx";

const ProtectedRoute = ({ children, role }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <main className="page">
        <p className="loading">Loading session...</p>
      </main>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (role && user.role !== role) {
    return <Navigate to={user.role === "buyer" ? "/buyer" : "/partner"} replace />;
  }

  return children;
};

const IndexRoute = () => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <main className="page">
        <p className="loading">Loading session...</p>
      </main>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <Navigate to={user.role === "buyer" ? "/buyer" : "/partner"} replace />;
};

const App = () => {
  return (
    <Routes>
      <Route path="/" element={<IndexRoute />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        path="/buyer"
        element={
          <ProtectedRoute role="buyer">
            <Navigate to="/buyer/dashboard" replace />
          </ProtectedRoute>
        }
      />
      <Route
        path="/buyer/dashboard"
        element={
          <ProtectedRoute role="buyer">
            <BuyerDashboardPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/buyer/campaigns"
        element={
          <ProtectedRoute role="buyer">
            <BuyerHome />
          </ProtectedRoute>
        }
      />
      <Route
        path="/buyer/campaigns/:campaignId"
        element={
          <ProtectedRoute role="buyer">
            <CampaignDetailPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/partner"
        element={
          <ProtectedRoute role="partner">
            <Navigate to="/partner/dashboard" replace />
          </ProtectedRoute>
        }
      />
      <Route
        path="/partner/dashboard"
        element={
          <ProtectedRoute role="partner">
            <PartnerDashboardPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/partner/get-ad"
        element={
          <ProtectedRoute role="partner">
            <PartnerHome />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

export default App;
