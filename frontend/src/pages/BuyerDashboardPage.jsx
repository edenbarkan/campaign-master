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

import RoleHeader from "../components/RoleHeader.jsx";
import { useAuth } from "../contexts/AuthContext";
import { apiFetch } from "../lib/api";

const BuyerDashboardPage = () => {
  const { token } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;
    apiFetch("/buyer/analytics/summary", { token })
      .then(setData)
      .catch(() => setError("Unable to load buyer analytics."));
  }, [token]);

  if (!data) {
    return (
      <main className="page dashboard">
        <section className="panel">
          <RoleHeader subtitle="Tracking spend, clicks, and efficiency." />
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
        <RoleHeader subtitle="Tracking spend, clicks, and efficiency." />
        <div className="metrics">
          <div className="metric-card">
            <p>Spend</p>
            <h3>${totals.spend.toFixed(2)}</h3>
          </div>
          <div className="metric-card">
            <p>Clicks</p>
            <h3>{totals.clicks}</h3>
          </div>
          <div className="metric-card">
            <p>Effective CPC</p>
            <h3>${totals.effective_cpc.toFixed(2)}</h3>
          </div>
          <div className="metric-card">
            <p>Cost efficiency</p>
            <h3>{totals.cost_efficiency.toFixed(2)} clicks/$</h3>
          </div>
        </div>
        <div className="grid charts">
          <section className="card">
            <h2>Spend over time</h2>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={daily}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="spend" stroke="#0f766e" strokeWidth={2} />
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
                <Line type="monotone" dataKey="clicks" stroke="#2563eb" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </section>
        </div>
        <section className="card">
          <h2>Campaign performance</h2>
          <div className="table">
            {campaigns.map((campaign) => (
              <div className="table-row" key={campaign.id}>
                <div>
                  <p className="row-title">{campaign.name}</p>
                  <p className="muted">
                    {campaign.status} · {campaign.clicks} clicks
                  </p>
                </div>
                <div className="row-metrics">
                  <span>${campaign.spend.toFixed(2)} spend</span>
                  <span>${campaign.budget_remaining.toFixed(2)} left</span>
                </div>
                <div className="row-metrics">
                  <span>Top partners</span>
                  <span>
                    {campaign.top_partners.length
                      ? campaign.top_partners
                          .map((partner) => `${partner.email} (${partner.clicks})`)
                          .join(", ")
                      : "None yet"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </section>
      </section>
    </main>
  );
};

export default BuyerDashboardPage;
