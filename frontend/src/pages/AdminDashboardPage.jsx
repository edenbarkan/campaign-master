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

const AdminDashboardPage = () => {
  const { token } = useAuth();
  const [summary, setSummary] = useState(null);
  const [series, setSeries] = useState(null);
  const [riskSummary, setRiskSummary] = useState(null);
  const [riskSeries, setRiskSeries] = useState(null);
  const [riskPartners, setRiskPartners] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;
    Promise.all([
      apiFetch("/admin/analytics/summary", { token }),
      apiFetch("/admin/analytics/series", { token }),
      apiFetch("/admin/risk/summary", { token }),
      apiFetch("/admin/risk/series", { token }),
      apiFetch("/admin/risk/top-partners", { token })
    ])
      .then(
        ([
          summaryResponse,
          seriesResponse,
          riskSummaryResponse,
          riskSeriesResponse,
          riskPartnersResponse
        ]) => {
        setSummary(summaryResponse);
        setSeries(seriesResponse.daily || []);
        setRiskSummary(riskSummaryResponse);
        setRiskSeries(riskSeriesResponse.daily || []);
        setRiskPartners(riskPartnersResponse.partners || []);
      })
      .catch(() => setError("Unable to load admin analytics."));
  }, [token]);

  if (!summary || !series || !riskSummary || !riskSeries || !riskPartners) {
    return (
      <main className="page dashboard">
        <section className="panel">
          <RoleHeader subtitle="Monitoring platform profit and payouts." />
          <p className="muted">Loading analytics...</p>
          {error ? <p className="error">{error}</p> : null}
        </section>
      </main>
    );
  }

  const { totals, top_campaigns: topCampaigns, top_partners: topPartners } = summary;
  const riskTotals = riskSummary.totals || {};
  const topReason = (riskSummary.top_reasons || [])[0];
  const rejectionRate = (riskTotals.rejection_rate || 0) * 100;

  return (
    <main className="page dashboard">
      <section className="panel">
        <RoleHeader subtitle="Monitoring platform profit and payouts." />
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
        <div className="grid">
          <section className="card">
            <h2>Risk overview</h2>
            <div className="metrics compact">
              <div className="metric-card">
                <p>Rejected clicks</p>
                <h3>{riskTotals.rejected || 0}</h3>
              </div>
              <div className="metric-card">
                <p>Rejection rate</p>
                <h3>{rejectionRate.toFixed(1)}%</h3>
              </div>
              <div className="metric-card">
                <p>Top reason</p>
                <h3>{topReason ? topReason.reason : "N/A"}</h3>
              </div>
            </div>
          </section>
          <section className="card">
            <h2>Accepted vs rejected</h2>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={riskSeries}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="accepted" stroke="#2563eb" strokeWidth={2} />
                <Line type="monotone" dataKey="rejected" stroke="#dc2626" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </section>
        </div>
        <section className="card">
          <h2>Top partners by rejected clicks</h2>
          <div className="table">
            {riskPartners.map((partner) => (
              <div className="table-row compact" key={partner.id}>
                <div>
                  <p className="row-title">{partner.email}</p>
                  <p className="muted">
                    {partner.rejected} rejects · {(partner.rejection_rate * 100).toFixed(1)}%
                  </p>
                </div>
                <div className="row-metrics">
                  <span>{partner.total} total clicks</span>
                </div>
              </div>
            ))}
          </div>
        </section>
      </section>
    </main>
  );
};

export default AdminDashboardPage;
