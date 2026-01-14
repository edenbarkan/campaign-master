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

import AdminHeader from "../components/AdminHeader.jsx";
import { useAuth } from "../contexts/AuthContext";
import { apiFetch } from "../lib/api";

const AdminDashboardPage = () => {
  const { token } = useAuth();
  const [summary, setSummary] = useState(null);
  const [series, setSeries] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;
    Promise.all([
      apiFetch("/admin/analytics/summary", { token }),
      apiFetch("/admin/analytics/series", { token })
    ])
      .then(([summaryResponse, seriesResponse]) => {
        setSummary(summaryResponse);
        setSeries(seriesResponse.daily || []);
      })
      .catch(() => setError("Unable to load admin analytics."));
  }, [token]);

  if (!summary || !series) {
    return (
      <main className="page dashboard">
        <section className="panel">
          <AdminHeader subtitle="Monitoring platform profit and payouts." />
          <p className="muted">Loading analytics...</p>
          {error ? <p className="error">{error}</p> : null}
        </section>
      </main>
    );
  }

  const { totals, top_campaigns: topCampaigns, top_partners: topPartners } = summary;

  return (
    <main className="page dashboard">
      <section className="panel">
        <AdminHeader subtitle="Monitoring platform profit and payouts." />
        <div className="metrics">
          <div className="metric-card">
            <p>Total spend</p>
            <h3>${totals.spend.toFixed(2)}</h3>
          </div>
          <div className="metric-card">
            <p>Total earnings</p>
            <h3>${totals.earnings.toFixed(2)}</h3>
          </div>
          <div className="metric-card">
            <p>Total profit</p>
            <h3>${totals.profit.toFixed(2)}</h3>
          </div>
          <div className="metric-card">
            <p>Total clicks</p>
            <h3>{totals.clicks}</h3>
          </div>
        </div>
        <div className="grid charts">
          <section className="card">
            <h2>Profit over time</h2>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={series}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="profit" stroke="#16a34a" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </section>
        </div>
        <div className="grid">
          <section className="card">
            <h2>Top campaigns by spend</h2>
            <div className="table">
              {topCampaigns.map((campaign) => (
                <div className="table-row compact" key={campaign.id}>
                  <div>
                    <p className="row-title">{campaign.name}</p>
                    <p className="muted">{campaign.clicks} clicks</p>
                  </div>
                  <div className="row-metrics">
                    <span>${campaign.spend.toFixed(2)} spend</span>
                  </div>
                </div>
              ))}
            </div>
          </section>
          <section className="card">
            <h2>Top partners by earnings</h2>
            <div className="table">
              {topPartners.map((partner) => (
                <div className="table-row compact" key={partner.id}>
                  <div>
                    <p className="row-title">{partner.email}</p>
                    <p className="muted">{partner.clicks} clicks</p>
                  </div>
                  <div className="row-metrics">
                    <span>${partner.earnings.toFixed(2)} earned</span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>
      </section>
    </main>
  );
};

export default AdminDashboardPage;
