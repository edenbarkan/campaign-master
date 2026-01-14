import React, { useEffect, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

import PartnerHeader from "../components/PartnerHeader.jsx";
import { useAuth } from "../contexts/AuthContext";
import { apiFetch } from "../lib/api";

const PartnerDashboardPage = () => {
  const { token } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;
    apiFetch("/partner/analytics/summary", { token })
      .then(setData)
      .catch(() => setError("Unable to load partner analytics."));
  }, [token]);

  if (!data) {
    return (
      <main className="page dashboard">
        <section className="panel">
          <PartnerHeader subtitle="Tracking earnings and click quality." />
          <p className="muted">Loading analytics...</p>
          {error ? <p className="error">{error}</p> : null}
        </section>
      </main>
    );
  }

  const { daily, totals, campaigns } = data;

  return (
    <main className="page dashboard">
      <section className="panel">
        <PartnerHeader subtitle="Tracking earnings and click quality." />
        <div className="metrics">
          <div className="metric-card">
            <p>Earnings</p>
            <h3>${totals.earnings.toFixed(2)}</h3>
          </div>
          <div className="metric-card">
            <p>Clicks</p>
            <h3>{totals.clicks}</h3>
          </div>
          <div className="metric-card">
            <p>EPC</p>
            <h3>${totals.epc.toFixed(2)}</h3>
          </div>
          <div className="metric-card">
            <p>Impressions</p>
            <h3>{totals.impressions}</h3>
          </div>
        </div>
        <div className="grid charts">
          <section className="card">
            <h2>Earnings over time</h2>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={daily}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="earnings" stroke="#0f766e" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </section>
          <section className="card">
            <h2>Clicks over time</h2>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={daily}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="clicks" stroke="#9333ea" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </section>
        </div>
        <section className="card">
          <h2>Top campaigns</h2>
          <div className="table">
            {campaigns.map((campaign) => (
              <div className="table-row compact" key={campaign.id}>
                <div>
                  <p className="row-title">{campaign.name}</p>
                  <p className="muted">{campaign.clicks} clicks</p>
                </div>
                <div className="row-metrics">
                  <span>${campaign.earnings.toFixed(2)} earned</span>
                </div>
              </div>
            ))}
          </div>
        </section>
      </section>
    </main>
  );
};

export default PartnerDashboardPage;
