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

const BuyerDashboardPage = () => {
  const { token } = useAuth();
  const [viewMode, setViewMode] = useState(() =>
    safeStorage.get("buyer_view_mode", "simple")
  );
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const isAdvanced = viewMode === "advanced";
  const [showOnboarding, setShowOnboarding] = useState(() =>
    safeStorage.get("onboarding_buyer_dismissed", "0") !== "1"
  );

  useEffect(() => {
    if (!token) return;
    apiFetch("/buyer/analytics/summary", { token })
      .then(setData)
      .catch(() => setError("Unable to load buyer analytics."));
  }, [token]);

  useEffect(() => {
    safeStorage.set("buyer_view_mode", viewMode);
  }, [viewMode]);

  const dismissOnboarding = () => {
    safeStorage.set("onboarding_buyer_dismissed", "1");
    setShowOnboarding(false);
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
  const totalBudgetLeft = (campaigns || []).reduce(
    (acc, campaign) => acc + Number(campaign.budget_remaining || 0),
    0
  );
  const maxCpcValue = (campaigns || []).reduce((acc, campaign) => {
    const value = Number(campaign.max_cpc ?? campaign.buyer_cpc ?? 0);
    return value > acc ? value : acc;
  }, 0);

  return (
    <main className="page dashboard">
      <section className="panel">
        <RoleHeader subtitle={UI_STRINGS.buyer.dashboardSubtitle} />
        <div className="view-toggle" role="group" aria-label="Buyer view mode">
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
        {deliveryStatus ? (
          <div className="status-row">
            <span className={`badge ${deliveryStatus.status.toLowerCase()}`}>
              {deliveryStatus.status.replace("_", " ")}
            </span>
            {deliveryStatus.note ? (
              <span className="muted">{deliveryStatus.note}</span>
            ) : null}
          </div>
        ) : null}
        <div className="metrics">
          <div className="metric-card">
            <p>Spend</p>
            <h3>${totals.spend.toFixed(2)}</h3>
          </div>
          <div className="metric-card">
            <p>Effective CPC</p>
            <h3>${totals.effective_cpc.toFixed(2)}</h3>
          </div>
          {deliveryStatus ? (
            <div className="metric-card">
              <p>Fill rate</p>
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
                <h3>${maxCpcValue.toFixed(2)}</h3>
              </div>
              <div className="metric-card">
                <p>Cost efficiency</p>
                <h3>{totals.cost_efficiency.toFixed(2)} clicks/$</h3>
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
        ) : null}
        <section className="card">
          <h2>Campaign performance</h2>
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
      {showOnboarding ? (
        <OnboardingOverlay role="buyer" onDismiss={dismissOnboarding} />
      ) : null}
    </main>
  );
};

export default BuyerDashboardPage;
