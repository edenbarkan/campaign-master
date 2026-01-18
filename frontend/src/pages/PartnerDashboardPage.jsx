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

const PartnerDashboardPage = () => {
  const { token } = useAuth();
  const [viewMode, setViewMode] = useState(() =>
    safeStorage.get("partner_view_mode", "simple")
  );
  const [data, setData] = useState(null);
  const [quality, setQuality] = useState(null);
  const [error, setError] = useState("");
  const isAdvanced = viewMode === "advanced";
  const [showOnboarding, setShowOnboarding] = useState(() =>
    safeStorage.get("onboarding_partner_dismissed", "0") !== "1"
  );

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

  useEffect(() => {
    safeStorage.set("partner_view_mode", viewMode);
  }, [viewMode]);

  const dismissOnboarding = () => {
    safeStorage.set("onboarding_partner_dismissed", "1");
    setShowOnboarding(false);
  };

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
    filled_requests: filledRequests = 0,
    partner_quality_state: partnerQualityState,
    partner_quality_note: partnerQualityNote
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

  const latestBreakdown = latestRequest?.score_breakdown || null;
  const formatPercent = (value) => {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? `${(parsed * 100).toFixed(2)}%` : "0.00%";
  };
  const formatNumber = (value) => {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed.toFixed(2) : "0.00";
  };
  const tldrBullets = latestBreakdown
    ? [
        `Profit potential: $${formatNumber(latestBreakdown.profit)} per click.`,
        `CTR estimate: ${formatPercent(latestBreakdown.ctr)}.`,
        latestBreakdown.targeting_bonus > 0 ? "Targeting match boosts rank." : null,
        latestBreakdown.partner_quality_state
          ? `Partner quality: ${latestBreakdown.partner_quality_state}.`
          : null,
        latestBreakdown.delivery_boost > 0
          ? "Delivery boost applied to improve pacing."
          : null,
        latestBreakdown.exploration_applied ? "Exploration bonus applied for new inventory." : null
      ].filter(Boolean)
    : [];
  const qualityAlerts = {
    NEW: {
      label: "! NEW",
      tone: "new",
      note: "Building history. Keep traffic clean to establish a strong baseline.",
      tooltip: "Early data only. Quality signals will stabilize with more traffic."
    },
    STABLE: {
      label: "OK STABLE",
      tone: "stable",
      note: "Quality is within normal range.",
      tooltip: "Stable quality signal."
    },
    RISKY: {
      label: "! AT RISK",
      tone: "risky",
      note: "At risk: reduce repeat clicks and avoid rapid refreshes.",
      tooltip: "Elevated reject rate for this partner."
    },
    RECOVERING: {
      label: "~ RECOVERING",
      tone: "recovering",
      note: "Improving quality. Keep traffic steady and policy-compliant.",
      tooltip: "Quality is improving after recent rejects."
    }
  };
  const qualityAlert = partnerQualityState ? qualityAlerts[partnerQualityState] : null;
  const breakdownRows = latestBreakdown
    ? [
        ["Profit", latestBreakdown.profit],
        ["Profit multiplier", latestBreakdown.alpha_profit],
        [
          "Smoothed CTR",
          formatPercent(latestBreakdown.ctr)
        ],
        ["CTR weight", latestBreakdown.ctr_weight],
        ["CTR multiplier", latestBreakdown.beta_ctr],
        ["Targeting bonus", latestBreakdown.targeting_bonus],
        ["Targeting multiplier", latestBreakdown.gamma_targeting],
        [
          "Partner reject rate",
          formatPercent(latestBreakdown.partner_reject_rate),
          UI_STRINGS.common.rejectSignalTooltip
        ],
        [
          "Partner reject penalty",
          latestBreakdown.partner_reject_penalty,
          UI_STRINGS.common.rejectSignalTooltip
        ],
        ["Quality multiplier", latestBreakdown.delta_quality],
        ["Partner quality penalty", latestBreakdown.partner_quality_penalty],
        ["Delivery boost", latestBreakdown.delivery_boost ?? 0],
        ["Exploration bonus", latestBreakdown.exploration_bonus ?? 0],
        ["Total score", latestBreakdown.total]
      ]
    : [];

  return (
    <main className="page dashboard">
        <section className="panel">
          <RoleHeader subtitle={UI_STRINGS.partner.dashboardSubtitle} />
          <div className="view-toggle" role="group" aria-label="Partner view mode">
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
        <div className="metrics">
          <div className="metric-card">
            <p>Earnings</p>
            <h3>${totals.earnings.toFixed(2)}</h3>
          </div>
          <div className="metric-card">
            <p>CTR</p>
            <h3>{ctr.toFixed(2)}%</h3>
          </div>
          <div className="metric-card">
            <p>Quality state</p>
            <h3>{partnerQualityState || "N/A"}</h3>
          </div>
          <div className="metric-card">
            <p>Fill rate</p>
            <h3>{(fillRate * 100).toFixed(1)}%</h3>
          </div>
          {isAdvanced ? (
            <>
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
                <p title={UI_STRINGS.common.rejectSignalTooltip}>Rejection rate</p>
                <h3>{rejectionRate.toFixed(2)}%</h3>
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
            </>
          ) : null}
        </div>
        {partnerQualityNote ? <p className="muted">{partnerQualityNote}</p> : null}
        {qualityAlert ? (
          <div className="quality-alert">
            <span
              className={`badge ${qualityAlert.tone}`}
              title={qualityAlert.tooltip}
            >
              {qualityAlert.label}
            </span>
            <span className="muted">{qualityAlert.note}</span>
          </div>
        ) : null}
        {!isAdvanced ? (
          <div className="simple-cta">
            <a className="button primary" href="/partner/get-ad">
              {UI_STRINGS.partner.getAdCta}
            </a>
          </div>
        ) : (
          <>
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
          </>
        )}
        {latestRequest ? (
          <section className="card">
            <h2>Why this ad?</h2>
            <div className="guard-note">
              <strong>{UI_STRINGS.common.marketStabilityGuardTitle}</strong> —{" "}
              {UI_STRINGS.common.marketStabilityGuardNote}
            </div>
            {tldrBullets.length ? (
              <ul className="tldr-list">
                {tldrBullets.map((bullet) => (
                  <li key={bullet}>{bullet}</li>
                ))}
              </ul>
            ) : null}
            <p className="muted">{UI_STRINGS.common.scoringDisclaimer}</p>
            {isAdvanced ? (
              <>
                <p className="muted">{latestRequest.explanation || "No explanation yet."}</p>
                {latestBreakdown?.partner_quality_state ? (
                  <p className="muted">
                    Partner quality state: {latestBreakdown.partner_quality_state}
                  </p>
                ) : null}
                {latestBreakdown?.market_note ? (
                  <p className="muted">Market note: {latestBreakdown.market_note}</p>
                ) : null}
                {latestBreakdown ? (
                  <div className="table compact">
                    {breakdownRows.map(([label, value, tooltip]) => (
                      <div className="table-row compact" key={label}>
                        <span className="muted" title={tooltip}>
                          {label}
                        </span>
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
                      <strong>Profit multiplier</strong> — Adaptive scaling based on market
                      health.
                    </li>
                    <li>
                      <strong>Smoothed CTR</strong> — Recent click-through rate estimate.
                    </li>
                    <li>
                      <strong>CTR weight</strong> — How strongly CTR influences final score.
                    </li>
                    <li>
                      <strong>CTR multiplier</strong> — Adaptive scaling applied to CTR.
                    </li>
                    <li>
                      <strong>Targeting bonus</strong> — Extra score for matching partner targeting.
                    </li>
                    <li>
                      <strong>Targeting multiplier</strong> — Adaptive scaling applied to targeting
                      match.
                    </li>
                    <li>
                      <strong>Partner reject rate</strong> — Partner’s recent rejected-click ratio.
                    </li>
                    <li>
                      <strong>Partner reject penalty</strong> — Base penalty from reject rate and
                      its weight.
                    </li>
                    <li>
                      <strong>Quality multiplier</strong> — Scales penalties based on partner state
                      and market conditions.
                    </li>
                    <li>
                      <strong>Partner quality penalty</strong> — Final penalty applied after
                      multipliers.
                    </li>
                    <li>
                      <strong>Delivery boost</strong> — Temporary boost for under-delivering
                      campaigns.
                    </li>
                    <li>
                      <strong>Exploration bonus</strong> — Bonus for new ads or partners during
                      exploration.
                    </li>
                    <li>
                      <strong>Total score</strong> — Final ranking score used by the matcher.
                    </li>
                  </ul>
                </details>
              </>
            ) : null}
          </section>
        ) : null}
      </section>
      {showOnboarding ? (
        <OnboardingOverlay role="partner" onDismiss={dismissOnboarding} />
      ) : null}
    </main>
  );
};

export default PartnerDashboardPage;
