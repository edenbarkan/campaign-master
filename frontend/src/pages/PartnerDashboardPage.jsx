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

const PartnerDashboardPage = () => {
  const { token } = useAuth();
  const [data, setData] = useState(null);
  const [quality, setQuality] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;
    Promise.all([
      apiFetch("/partner/analytics/summary", { token }),
      apiFetch("/partner/quality/summary", { token })
    ])
      .then(([summaryResponse, qualityResponse]) => {
        setData(summaryResponse);
        setQuality(qualityResponse);
      })
      .catch(() => setError("Unable to load partner analytics."));
  }, [token]);

  if (!data || !quality) {
    return (
      <main className="page dashboard">
        <section className="panel">
          <RoleHeader subtitle="Tracking earnings and click quality." />
          <p className="muted">Loading analytics...</p>
          {error ? <p className="error">{error}</p> : null}
        </section>
      </main>
    );
  }

  const {
    daily,
    totals,
    campaigns,
    fill_rate: fillRate = 0,
    unfilled_requests: unfilledRequests = 0,
    total_requests: totalRequests = 0,
    filled_requests: filledRequests = 0
  } = data;
  const ctr = (quality.ctr || 0) * 100;
  const rejectionRate = (quality.rejection_rate || 0) * 100;
  const latestRequest = data.latest_request || (() => {
    try {
      const stored = localStorage.getItem("partnerLatestAd");
      return stored ? JSON.parse(stored) : null;
    } catch (err) {
      return null;
    }
  })();

  return (
    <main className="page dashboard">
      <section className="panel">
        <RoleHeader subtitle="Tracking earnings and click quality." />
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
          <div className="metric-card">
            <p>CTR</p>
            <h3>{ctr.toFixed(2)}%</h3>
          </div>
          <div className="metric-card">
            <p>Rejection rate</p>
            <h3>{rejectionRate.toFixed(2)}%</h3>
          </div>
          <div className="metric-card">
            <p>Fill rate</p>
            <h3>{(fillRate * 100).toFixed(1)}%</h3>
          </div>
          <div className="metric-card">
            <p>Total requests</p>
            <h3>{totalRequests}</h3>
          </div>
          <div className="metric-card">
            <p>Filled requests</p>
            <h3>{filledRequests}</h3>
          </div>
          <div className="metric-card">
            <p>Unfilled requests</p>
            <h3>{unfilledRequests}</h3>
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
        <section className="card">
          <h2>Top ads</h2>
          <div className="table">
            {(data.top_ads || []).map((ad) => (
              <div className="table-row compact" key={ad.id}>
                <div>
                  <p className="row-title">{ad.title}</p>
                  <p className="muted">
                    {ad.clicks} clicks · {(ad.ctr * 100).toFixed(2)}% CTR
                  </p>
                </div>
                <div className="row-metrics">
                  <span>${ad.earnings.toFixed(2)} earned</span>
                </div>
              </div>
            ))}
          </div>
        </section>
        {latestRequest ? (
          <section className="card">
            <h2>Why this ad?</h2>
            <p className="muted">{latestRequest.explanation || "No explanation yet."}</p>
            {latestRequest.score_breakdown ? (
              <div className="table compact">
                {[
                  ["Profit", latestRequest.score_breakdown.profit],
                  [
                    "Smoothed CTR",
                    `${((latestRequest.score_breakdown.ctr || 0) * 100).toFixed(2)}%`
                  ],
                  ["CTR weight", latestRequest.score_breakdown.ctr_weight],
                  ["Targeting bonus", latestRequest.score_breakdown.targeting_bonus],
                  [
                    "Partner reject rate",
                    `${(
                      (latestRequest.score_breakdown.partner_reject_rate || 0) * 100
                    ).toFixed(2)}%`
                  ],
                  [
                    "Partner quality penalty",
                    latestRequest.score_breakdown.partner_reject_penalty
                  ],
                  ["Total score", latestRequest.score_breakdown.total]
                ].map(([label, value]) => (
                  <div className="table-row compact" key={label}>
                    <span className="muted">{label}</span>
                    <span>{value}</span>
                  </div>
                ))}
              </div>
            ) : null}
            <details className="score-legend">
              <summary>What do these numbers mean?</summary>
              <ul className="legend-list">
                <li>
                  <strong>Profit</strong> — Expected profit for this impression.
                </li>
                <li>
                  <strong>Smoothed CTR</strong> — Recent click-through rate estimate.
                </li>
                <li>
                  <strong>CTR weight</strong> — How strongly CTR influences final score.
                </li>
                <li>
                  <strong>Targeting bonus</strong> — Extra score for matching partner targeting.
                </li>
                <li>
                  <strong>Partner reject rate</strong> — Partner’s recent rejected-click ratio.
                </li>
                <li>
                  <strong>Partner quality penalty</strong> — Score reduction caused by partner
                  reject rate.
                </li>
                <li>
                  <strong>Total score</strong> — Final ranking score used by the matcher.
                </li>
              </ul>
            </details>
          </section>
        ) : null}
      </section>
    </main>
  );
};

export default PartnerDashboardPage;
