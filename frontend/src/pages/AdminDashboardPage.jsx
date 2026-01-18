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
import OnboardingOverlay from "../components/OnboardingOverlay.jsx";
import { safeStorage } from "../lib/storage";
import { UI_STRINGS } from "../lib/strings";

const AdminDashboardPage = () => {
  const { token } = useAuth();
  const [summary, setSummary] = useState(null);
  const [series, setSeries] = useState(null);
  const [riskSummary, setRiskSummary] = useState(null);
  const [riskSeries, setRiskSeries] = useState(null);
  const [riskPartners, setRiskPartners] = useState(null);
  const [error, setError] = useState("");
  const [lastUpdatedAt, setLastUpdatedAt] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [tick, setTick] = useState(Date.now());
  const [showOnboarding, setShowOnboarding] = useState(() =>
    safeStorage.get("onboarding_admin_dismissed", "0") !== "1"
  );
  const [rangeDays, setRangeDays] = useState(30);
  const [selectedReason, setSelectedReason] = useState(null);

  const rangeOptions = [7, 30, 90];
  const formatDate = (value) => value.toISOString().slice(0, 10);

  const loadData = async () => {
    if (!token) return;
    setIsRefreshing(true);
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(endDate.getDate() - (rangeDays - 1));
    const fromValue = formatDate(startDate);
    const toValue = formatDate(endDate);
    try {
      const [
        summaryResponse,
        seriesResponse,
        riskSummaryResponse,
        riskSeriesResponse,
        riskPartnersResponse
      ] = await Promise.all([
        apiFetch(`/admin/analytics/summary?days=${rangeDays}`, { token }),
        apiFetch(`/admin/analytics/series?days=${rangeDays}`, { token }),
        apiFetch("/admin/risk/summary", { token }),
        apiFetch(`/admin/risk/series?from=${fromValue}&to=${toValue}`, { token }),
        apiFetch("/admin/risk/top-partners", { token })
      ]);
      setSummary(summaryResponse);
      setSeries(seriesResponse.daily || []);
      setRiskSummary(riskSummaryResponse);
      setRiskSeries(riskSeriesResponse.daily || []);
      setRiskPartners(riskPartnersResponse.partners || []);
      setLastUpdatedAt(Date.now());
      setError("");
    } catch (err) {
      setError("Unable to load admin analytics.");
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [token, rangeDays]);

  const dismissOnboarding = () => {
    safeStorage.set("onboarding_admin_dismissed", "1");
    setShowOnboarding(false);
  };

  useEffect(() => {
    const interval = window.setInterval(() => setTick(Date.now()), 1000);
    return () => window.clearInterval(interval);
  }, []);

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

  const {
    totals,
    top_campaigns: topCampaigns,
    top_partners: topPartners,
    marketplace_health: marketplaceHealth
  } = summary;
  const riskTotals = riskSummary.totals || {};
  const topReason = (riskSummary.top_reasons || [])[0];
  const rejectionRate = (riskTotals.rejection_rate || 0) * 100;
  const marketplaceFillRate = (marketplaceHealth?.fill_rate || 0) * 100;
  const marketplaceRejectRate = (marketplaceHealth?.reject_rate || 0) * 100;
  const marketplaceTakeRate = (marketplaceHealth?.take_rate || 0) * 100;
  const updatedSeconds = lastUpdatedAt
    ? Math.max(0, Math.floor((tick - lastUpdatedAt) / 1000))
    : null;
  const updatedLabel =
    updatedSeconds === null
      ? ""
      : updatedSeconds < 60
      ? `${updatedSeconds}s ago`
      : `${Math.floor(updatedSeconds / 60)}m ago`;
  const hasMarketActivity = (totals?.spend || 0) > 0 || (totals?.earnings || 0) > 0;
  const reasonDetails = {
    DUPLICATE_CLICK: {
      title: "Duplicate click",
      meaning: "Multiple clicks from the same IP within the duplicate window.",
      why: "Often caused by rapid refreshes, aggressive retries, or click spamming.",
      mitigation: "Encourage unique traffic and avoid rapid retries."
    },
    RATE_LIMIT: {
      title: "Rate limit",
      meaning: "Click velocity exceeded the per-minute cap.",
      why: "Traffic spikes from a single source can trip velocity limits.",
      mitigation: "Throttle high-velocity sources and smooth traffic bursts."
    },
    BUDGET_EXHAUSTED: {
      title: "Budget exhausted",
      meaning: "Campaign budget could not cover the max CPC.",
      why: "The remaining balance is below the campaign's max CPC.",
      mitigation: "Increase budget or lower max CPC to resume delivery."
    },
    INVALID_ASSIGNMENT: {
      title: "Invalid assignment",
      meaning: "Tracking code not found or expired.",
      why: "Old or malformed tracking URLs were used in placements.",
      mitigation: "Ensure ads use the latest tracking URL."
    },
    BOT_SUSPECTED: {
      title: "Bot suspected",
      meaning: "Missing or empty user-agent signal.",
      why: "Automated requests or stripped headers can trigger bot suspicion.",
      mitigation: "Filter automated traffic and ensure UA is passed."
    }
  };
  const selectedReasonDetail = selectedReason
    ? reasonDetails[selectedReason] || null
    : null;

  return (
    <main className="page dashboard">
      <section className="panel">
        <RoleHeader subtitle={UI_STRINGS.admin.dashboardSubtitle} />
        <div className="view-toggle" role="group" aria-label="Admin date range">
          {rangeOptions.map((days) => (
            <button
              key={days}
              type="button"
              className={`toggle-button ${rangeDays === days ? "active" : ""}`}
              onClick={() => setRangeDays(days)}
              aria-pressed={rangeDays === days}
              title={`Show the last ${days} days`}
            >
              {days}d
            </button>
          ))}
        </div>
        <div className="refresh-row">
          <span className="muted">
            {lastUpdatedAt ? `${UI_STRINGS.common.lastUpdatedLabel} ${updatedLabel}` : ""}
          </span>
          <button
            className="button ghost"
            type="button"
            onClick={loadData}
            disabled={isRefreshing}
          >
            {isRefreshing ? "Refreshing..." : UI_STRINGS.common.refreshData}
          </button>
        </div>
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
        {!hasMarketActivity ? (
          <div className="empty-state">
            <p className="muted">No marketplace activity in this range.</p>
            <span className="muted">Try 30d or run demo traffic to populate.</span>
          </div>
        ) : null}
        <div className="grid charts">
          <section className="card">
            <h2>Spend, earnings, profit</h2>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={series}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="spend" stroke="#0f766e" strokeWidth={2} />
                <Line type="monotone" dataKey="earnings" stroke="#9333ea" strokeWidth={2} />
                <Line type="monotone" dataKey="profit" stroke="#16a34a" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </section>
        </div>
        {marketplaceHealth ? (
          <div className="grid">
            <section className="card">
              <h2>Marketplace health</h2>
              <div className="metrics compact">
                <div className="metric-card">
                  <p>Fill rate</p>
                  <h3>{marketplaceFillRate.toFixed(1)}%</h3>
                </div>
                <div className="metric-card">
                  <p>Reject rate</p>
                  <h3>{marketplaceRejectRate.toFixed(1)}%</h3>
                </div>
                <div className="metric-card">
                  <p>Take rate</p>
                  <h3>{marketplaceTakeRate.toFixed(1)}%</h3>
                </div>
                <div className="metric-card">
                  <p>Profit</p>
                  <h3>${marketplaceHealth.profit.toFixed(2)}</h3>
                </div>
              </div>
              {marketplaceHealth.market_note ? (
                <p className="muted">{marketplaceHealth.market_note}</p>
              ) : null}
            </section>
            <section className="card">
              <h2>Under-delivering buyers</h2>
              <div className="table">
                {(marketplaceHealth.top_under_delivering_buyers || []).map((buyer) => (
                  <div className="table-row compact" key={buyer.id}>
                    <div>
                      <p className="row-title">{buyer.email}</p>
                      <p className="muted">
                        {(buyer.fill_rate * 100).toFixed(1)}% fill · {buyer.clicks} clicks
                      </p>
                    </div>
                    <div className="row-metrics">
                      <span>{buyer.status.replace("_", " ")}</span>
                    </div>
                  </div>
                ))}
              </div>
            </section>
            <section className="card">
              <h2>Low-quality partners</h2>
              <div className="table">
                {(marketplaceHealth.top_low_quality_partners || []).map((partner) => (
                  <div className="table-row compact" key={partner.id}>
                    <div>
                      <p className="row-title">{partner.email}</p>
                      <p className="muted">
                        {(partner.rejection_rate * 100).toFixed(1)}% rejects ·{" "}
                        {(partner.ctr * 100).toFixed(2)}% CTR
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          </div>
        ) : null}
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
            <h2>Reject reasons</h2>
            <div className="table">
              {(riskSummary.top_reasons || []).map((reason) => (
                <button
                  key={reason.reason}
                  type="button"
                  className="table-row compact button-row"
                  onClick={() => setSelectedReason(reason.reason)}
                  title="Select to view details and mitigation tips."
                >
                  <span className="muted">{reason.reason}</span>
                  <span>{reason.count}</span>
                </button>
              ))}
            </div>
            {selectedReasonDetail ? (
              <div className="detail-panel">
                <p className="row-title">{selectedReasonDetail.title}</p>
                <p className="muted">
                  <strong>Meaning:</strong> {selectedReasonDetail.meaning}
                </p>
                <p className="muted">
                  <strong>Why it happens:</strong> {selectedReasonDetail.why}
                </p>
                <p className="muted">
                  <strong>How to mitigate:</strong> {selectedReasonDetail.mitigation}
                </p>
              </div>
            ) : (
              <p className="muted">
                Select a reject reason to see meaning and mitigation steps.
              </p>
            )}
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
      {showOnboarding ? (
        <OnboardingOverlay role="admin" onDismiss={dismissOnboarding} />
      ) : null}
    </main>
  );
};

export default AdminDashboardPage;
