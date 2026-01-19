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
  const [lastUpdatedAt, setLastUpdatedAt] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [tick, setTick] = useState(Date.now());
  const isAdvanced = viewMode === "advanced";
  const [showNudge, setShowNudge] = useState(() =>
    safeStorage.get("onboarding_nudge_partner_dismissed", "0") !== "1"
  );

  const loadData = async () => {
    if (!token) return;
    setIsRefreshing(true);
    try {
      const [summaryResponse, qualityResponse] = await Promise.all([
        apiFetch("/partner/analytics/summary", { token }),
        apiFetch("/partner/quality/summary", { token })
      ]);
      setData(summaryResponse);
      setQuality(qualityResponse);
      setLastUpdatedAt(Date.now());
      setError("");
    } catch (err) {
      setError("Unable to load partner analytics.");
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [token]);

  useEffect(() => {
    safeStorage.set("partner_view_mode", viewMode);
  }, [viewMode]);

  useEffect(() => {
    const interval = window.setInterval(() => setTick(Date.now()), 1000);
    return () => window.clearInterval(interval);
  }, []);

  const dismissNudge = () => {
    safeStorage.set("onboarding_nudge_partner_dismissed", "1");
    setShowNudge(false);
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
  const tldrBullets = [
    "Matches your targeting hints (if provided).",
    "Quality affects ranking — never billing.",
    "Market Stability Guard reduces abuse, not earnings."
  ];
  const qualityAlerts = {
    NEW: {
      label: "~ NEW",
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
    AT_RISK: {
      label: "! AT RISK",
      tone: "at-risk",
      note: "Quality is slipping. Reduce rapid refreshes and retries.",
      tooltip: "Rising reject rate for this partner."
    },
    RISKY: {
      label: "!! RISKY",
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
  const breakdownQualityAlert = latestBreakdown?.partner_quality_state
    ? qualityAlerts[latestBreakdown.partner_quality_state] || null
    : qualityAlert;
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
  const updatedSeconds = lastUpdatedAt
    ? Math.max(0, Math.floor((tick - lastUpdatedAt) / 1000))
    : null;
  const updatedLabel =
    updatedSeconds === null
      ? ""
      : updatedSeconds < 60
      ? `${updatedSeconds}s ago`
      : `${Math.floor(updatedSeconds / 60)}m ago`;

  return (
    <main className="page dashboard">
        <section className="panel">
          <RoleHeader subtitle={UI_STRINGS.partner.dashboardSubtitle} />
        <div className="view-toggle tabs" role="group" aria-label="Partner view mode">
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
              <p className="muted">Get a fresh ad and test placement.</p>
            </div>
            <div className="actions">
              <a className="button primary" href="/partner/get-ad">
                {UI_STRINGS.partner.getAdCta}
              </a>
              <button className="button ghost small" type="button" onClick={dismissNudge}>
                Dismiss
              </button>
            </div>
          </div>
        ) : null}
        <div className="metrics">
          <div className="metric-card">
            <p className="metric-label">
              Earnings
              <span className="tooltip" tabIndex="0" data-tooltip={UI_STRINGS.common.earningsTooltip}>
                i
              </span>
            </p>
            <h3>${totals.earnings.toFixed(2)}</h3>
          </div>
          <div className="metric-card">
            <p className="metric-label">
              CTR
              <span className="tooltip" tabIndex="0" data-tooltip={UI_STRINGS.common.ctrTooltip}>
                i
              </span>
            </p>
            <h3>{ctr.toFixed(2)}%</h3>
          </div>
          <div className="metric-card">
            <p className="metric-label">
              Quality state
              <span
                className="tooltip"
                tabIndex="0"
                data-tooltip={UI_STRINGS.common.qualityStateTooltip}
              >
                i
              </span>
            </p>
            {qualityAlert ? (
              <span className={`badge ${qualityAlert.tone}`} title={qualityAlert.tooltip}>
                {qualityAlert.label}
              </span>
            ) : (
              <h3>—</h3>
            )}
          </div>
          <div className="metric-card">
            <p className="metric-label">
              Fill rate
              <span className="tooltip" tabIndex="0" data-tooltip={UI_STRINGS.common.fillRateTooltip}>
                i
              </span>
            </p>
            <h3>{(fillRate * 100).toFixed(1)}%</h3>
          </div>
          {isAdvanced ? (
            <>
              <div className="metric-card">
                <p className="metric-label">
                  Clicks
                  <span className="tooltip" tabIndex="0" data-tooltip={UI_STRINGS.common.totalClicksTooltip}>
                    i
                  </span>
                </p>
                <h3>{totals.clicks}</h3>
              </div>
              <div className="metric-card">
                <p className="metric-label">
                  EPC
                  <span className="tooltip" tabIndex="0" data-tooltip={UI_STRINGS.common.epcTooltip}>
                    i
                  </span>
                </p>
                <h3>${totals.epc.toFixed(2)}</h3>
              </div>
              <div className="metric-card">
                <p className="metric-label">
                  Impressions
                  <span
                    className="tooltip"
                    tabIndex="0"
                    data-tooltip={UI_STRINGS.common.impressionsTooltip}
                  >
                    i
                  </span>
                </p>
                <h3>{totals.impressions}</h3>
              </div>
              <div className="metric-card">
                <p className="metric-label">
                  Rejection rate
                  <span
                    className="tooltip"
                    tabIndex="0"
                    data-tooltip={UI_STRINGS.common.rejectionRateTooltip}
                  >
                    i
                  </span>
                </p>
                <h3>{rejectionRate.toFixed(2)}%</h3>
              </div>
              <div className="metric-card">
                <p className="metric-label">
                  Total requests
                  <span
                    className="tooltip"
                    tabIndex="0"
                    data-tooltip={UI_STRINGS.common.totalRequestsTooltip}
                  >
                    i
                  </span>
                </p>
                <h3>{totalRequests}</h3>
              </div>
              <div className="metric-card">
                <p className="metric-label">
                  Filled requests
                  <span
                    className="tooltip"
                    tabIndex="0"
                    data-tooltip={UI_STRINGS.common.filledRequestsTooltip}
                  >
                    i
                  </span>
                </p>
                <h3>{filledRequests}</h3>
              </div>
              <div className="metric-card">
                <p className="metric-label">
                  Unfilled requests
                  <span
                    className="tooltip"
                    tabIndex="0"
                    data-tooltip={UI_STRINGS.common.unfilledRequestsTooltip}
                  >
                    i
                  </span>
                </p>
                <h3>{unfilledRequests}</h3>
              </div>
            </>
          ) : null}
        </div>
        <div className="earnings-note">
          <p className="row-title">How you earn</p>
          <p className="muted">
            You earn only from accepted clicks. Rejected clicks never pay. Better traffic
            quality means better ads and higher earnings.
          </p>
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
        {totalRequests === 0 ? (
          <div className="empty-state">
            <p className="muted">No ad requests yet. Try broad filters first.</p>
            <a className="button primary" href="/partner/get-ad">
              {UI_STRINGS.partner.getAdCta}
            </a>
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
            <details className="score-details">
              <summary>Show details</summary>
              <p className="muted">{latestRequest.explanation || "No explanation yet."}</p>
              {breakdownQualityAlert ? (
                <div className="quality-alert">
                  <span
                    className={`badge ${breakdownQualityAlert.tone}`}
                    title={breakdownQualityAlert.tooltip}
                  >
                    {breakdownQualityAlert.label}
                  </span>
                  <span className="muted">Partner quality state</span>
                </div>
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
                    <strong>Profit multiplier</strong> — Adaptive scaling based on market health.
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
                    <strong>Partner reject penalty</strong> — Base penalty from reject rate and its
                    weight.
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
            </details>
          </section>
        ) : null}
      </section>
    </main>
  );
};

export default PartnerDashboardPage;
