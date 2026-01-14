import React from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { useAuth } from "./contexts/AuthContext";
import AdminDashboardPage from "./pages/AdminDashboardPage.jsx";
import BuyerDashboardPage from "./pages/BuyerDashboardPage.jsx";
import BuyerHome from "./pages/BuyerHome.jsx";
import CampaignDetailPage from "./pages/CampaignDetailPage.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import PartnerDashboardPage from "./pages/PartnerDashboardPage.jsx";
import PartnerHome from "./pages/PartnerHome.jsx";
import RegisterPage from "./pages/RegisterPage.jsx";

const normalizeRole = (role) => (role ? role.toUpperCase() : "");

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

  const currentRole = normalizeRole(user.role);
  const expectedRole = normalizeRole(role);

  if (role && currentRole !== expectedRole) {
    if (currentRole === "BUYER") {
      return <Navigate to="/buyer/dashboard" replace />;
    }
    if (currentRole === "PARTNER") {
      return <Navigate to="/partner/dashboard" replace />;
    }
    return <Navigate to="/admin/dashboard" replace />;
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

  const currentRole = normalizeRole(user.role);

  if (currentRole === "BUYER") {
    return <Navigate to="/buyer/dashboard" replace />;
  }
  if (currentRole === "PARTNER") {
    return <Navigate to="/partner/dashboard" replace />;
  }
  return <Navigate to="/admin/dashboard" replace />;
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
          <ProtectedRoute role="BUYER">
            <Navigate to="/buyer/dashboard" replace />
          </ProtectedRoute>
        }
      />
      <Route
        path="/buyer/dashboard"
        element={
          <ProtectedRoute role="BUYER">
            <BuyerDashboardPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/buyer/campaigns"
        element={
          <ProtectedRoute role="BUYER">
            <BuyerHome />
          </ProtectedRoute>
        }
      />
      <Route
        path="/buyer/campaigns/:campaignId"
        element={
          <ProtectedRoute role="BUYER">
            <CampaignDetailPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/partner"
        element={
          <ProtectedRoute role="PARTNER">
            <Navigate to="/partner/dashboard" replace />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/dashboard"
        element={
          <ProtectedRoute role="ADMIN">
            <AdminDashboardPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/partner/dashboard"
        element={
          <ProtectedRoute role="PARTNER">
            <PartnerDashboardPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/partner/get-ad"
        element={
          <ProtectedRoute role="PARTNER">
            <PartnerHome />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

export default App;
