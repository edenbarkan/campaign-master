import React, { useEffect, useState } from "react";
import {
  CartesianGrid,
  Legend,
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
import { safeStorage } from "../lib/storage";
import { UI_STRINGS } from "../lib/strings";

const BuyerDashboardPage = () => {
  const { token } = useAuth();
  const [viewMode, setViewMode] = useState(() =>
    safeStorage.get("buyer_view_mode", "simple")
  );
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [lastUpdatedAt, setLastUpdatedAt] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [tick, setTick] = useState(Date.now());
  const isAdvanced = viewMode === "advanced";
  const [showNudge, setShowNudge] = useState(() =>
    safeStorage.get("onboarding_nudge_buyer_dismissed", "0") !== "1"
  );

  const loadData = async () => {
    if (!token) return;
    setIsRefreshing(true);
    try {
      const payload = await apiFetch("/buyer/analytics/summary", { token });
      setData(payload);
      setLastUpdatedAt(Date.now());
      setError("");
    } catch (err) {
      setError("Unable to load buyer analytics.");
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [token]);

  useEffect(() => {
    safeStorage.set("buyer_view_mode", viewMode);
  }, [viewMode]);

  useEffect(() => {
    const interval = window.setInterval(() => setTick(Date.now()), 1000);
    return () => window.clearInterval(interval);
  }, []);

  const dismissNudge = () => {
    safeStorage.set("onboarding_nudge_buyer_dismissed", "1");
    setShowNudge(false);
  };

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

  const { daily, totals, campaigns, delivery_status: deliveryStatus } = data;
  const spendValue = Number(totals.spend || 0);
  const effectiveCpcValue = Number(totals.effective_cpc || 0);
  const costEfficiencyValue = Number(totals.cost_efficiency || 0);
  const updatedSeconds = lastUpdatedAt
    ? Math.max(0, Math.floor((tick - lastUpdatedAt) / 1000))
    : null;
  const updatedLabel =
    updatedSeconds === null
      ? ""
      : updatedSeconds < 60
      ? `${updatedSeconds}s ago`
      : `${Math.floor(updatedSeconds / 60)}m ago`;
  const totalBudgetLeft = (campaigns || []).reduce(
    (acc, campaign) => acc + Number(campaign.budget_remaining || 0),
    0
  );
  const maxCpcValue = (campaigns || []).reduce((acc, campaign) => {
    const value = Number(campaign.max_cpc ?? campaign.buyer_cpc ?? 0);
    return value > acc ? value : acc;
  }, 0);
  const maxCpcDisplay =
    maxCpcValue > 0 ? `$${maxCpcValue.toFixed(2)}` : "— (per campaign)";

  return (
    <main className="page dashboard">
      <section className="panel">
        <RoleHeader subtitle={UI_STRINGS.buyer.dashboardSubtitle} />
        <div className="view-toggle tabs" role="group" aria-label="Buyer view mode">
          <button
            type="button"
            className={`toggle-button ${!isAdvanced ? "active" : ""}`}
            onClick={() => setViewMode("simple")}
            aria-pressed={!isAdvanced}
          >
            {UI_STRINGS.common.simpleView}
          </button>
          <button
            type="button"
            className={`toggle-button ${isAdvanced ? "active" : ""}`}
            onClick={() => setViewMode("advanced")}
            aria-pressed={isAdvanced}
          >
            {UI_STRINGS.common.advancedView}
          </button>
        </div>
        <p className="toggle-hint">{UI_STRINGS.common.viewModeHint}</p>
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
        {showNudge ? (
          <div className="nudge-banner">
            <div>
              <p className="row-title">New here?</p>
              <p className="muted">Start with your first campaign.</p>
            </div>
            <div className="actions">
              <a className="button primary" href="/buyer/campaigns">
                Create your first campaign
              </a>
              <button className="button ghost small" type="button" onClick={dismissNudge}>
                Dismiss
              </button>
            </div>
          </div>
        ) : null}
        {deliveryStatus ? (
          <div className="status-row">
            <span
              className={`badge ${
                spendValue === 0 ? "not_serving" : deliveryStatus.status.toLowerCase()
              }`}
            >
              {spendValue === 0
                ? "Not serving yet"
                : deliveryStatus.status.replace("_", " ")}
            </span>
            {deliveryStatus.note ? (
              <span className="muted">{deliveryStatus.note}</span>
            ) : null}
          </div>
        ) : null}
        <div className="metrics">
          <div className="metric-card">
            <p>Spend</p>
            <h3>${spendValue.toFixed(2)}</h3>
          </div>
          <div className="metric-card">
            <p>Effective CPC</p>
            <h3>${effectiveCpcValue.toFixed(2)}</h3>
          </div>
          {deliveryStatus ? (
            <div className="metric-card">
              <p title={UI_STRINGS.common.fillRateTooltip}>Fill rate</p>
              <h3>{(deliveryStatus.fill_rate * 100).toFixed(1)}%</h3>
            </div>
          ) : null}
          {isAdvanced ? (
            <>
              <div className="metric-card">
                <p>Clicks</p>
                <h3>{totals.clicks}</h3>
              </div>
              <div className="metric-card">
                <p>Budget left</p>
                <h3>${totalBudgetLeft.toFixed(2)}</h3>
              </div>
              <div className="metric-card">
                <p>Max CPC</p>
                <h3>{maxCpcDisplay}</h3>
              </div>
              <div className="metric-card">
                <p title={UI_STRINGS.common.costEfficiencyTooltip}>Cost efficiency</p>
                <h3>{costEfficiencyValue.toFixed(2)} clicks/$</h3>
              </div>
            </>
          ) : null}
        </div>
        {isAdvanced ? (
          <div className="grid charts">
            <section className="card">
              <h2>Spend over time</h2>
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={daily}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" label={{ value: "Date", position: "insideBottom", offset: -6 }} />
                  <YAxis label={{ value: "Spend ($)", angle: -90, position: "insideLeft" }} />
                  <Tooltip />
                  <Line
                    type="monotone"
                    dataKey="spend"
                    name="Spend ($)"
                    stroke="#0f766e"
                    strokeWidth={2}
                  />
                  <Legend />
                </LineChart>
              </ResponsiveContainer>
            </section>
            <section className="card">
              <h2>Clicks over time</h2>
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={daily}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" label={{ value: "Date", position: "insideBottom", offset: -6 }} />
                  <YAxis label={{ value: "Clicks", angle: -90, position: "insideLeft" }} />
                  <Tooltip />
                  <Line
                    type="monotone"
                    dataKey="clicks"
                    name="Clicks"
                    stroke="#2563eb"
                    strokeWidth={2}
                  />
                  <Legend />
                </LineChart>
              </ResponsiveContainer>
            </section>
          </div>
        ) : null}
        <section className="card">
          <h2>Campaign performance</h2>
          {campaigns.length === 0 ? (
            <div className="empty-state">
              <p className="muted">No campaigns yet. Start with a budget and max CPC.</p>
              <a className="button primary" href="/buyer/campaigns">
                Create your first campaign
              </a>
            </div>
          ) : null}
          <div className="table">
            {campaigns.map((campaign) => (
              <div className="table-row" key={campaign.id}>
                <div>
                  <p className="row-title">{campaign.name}</p>
                  <p className="muted">
                    {campaign.status} · {campaign.clicks} clicks{" "}
                    {isAdvanced
                      ? `· ${(campaign.ctr * 100).toFixed(2)}% CTR`
                      : ""}
                  </p>
                </div>
                <div className="row-metrics">
                  <span>${campaign.spend.toFixed(2)} spend</span>
                  <span>${campaign.budget_remaining.toFixed(2)} left</span>
                </div>
                {isAdvanced ? (
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
                ) : null}
              </div>
            ))}
          </div>
        </section>
      </section>
    </main>
  );
};

export default BuyerDashboardPage;
