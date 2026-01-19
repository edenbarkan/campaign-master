import React, { useEffect, useState } from "react";

import RoleHeader from "../components/RoleHeader.jsx";
import { useAuth } from "../contexts/AuthContext";
import { apiFetch } from "../lib/api";
import { safeStorage } from "../lib/storage";
import { UI_STRINGS } from "../lib/strings";

const PartnerHome = () => {
  const { user, token } = useAuth();
  const [viewMode, setViewMode] = useState(() =>
    safeStorage.get("partner_view_mode", "simple")
  );
  const [filters, setFilters] = useState({
    category: "",
    geo: "",
    placement: "",
    device: ""
  });
  const [assignment, setAssignment] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [previewBlocked, setPreviewBlocked] = useState(false);
  const [snippetCopied, setSnippetCopied] = useState(false);
  const isAdvanced = viewMode === "advanced";

  useEffect(() => {
    safeStorage.set("partner_view_mode", viewMode);
  }, [viewMode]);

  useEffect(() => {
    setPreviewBlocked(false);
  }, [assignment?.ad?.image_url]);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setFilters((prev) => ({ ...prev, [name]: value }));
  };

  const buildQuery = () => {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value) params.append(key, value);
    });
    return params.toString();
  };

  const requestAd = async () => {
    setError("");
    setLoading(true);
    try {
      const query = buildQuery();
      const payload = await apiFetch(`/partner/ad${query ? `?${query}` : ""}`, {
        token
      });
      if (!payload.filled) {
        const reason = payload.reason || "NO_ELIGIBLE_ADS";
        const message =
          reason === "FREQ_CAP"
            ? "Frequency cap is active. Try again in a minute or change filters."
            : "No eligible ads for these filters. Try broader category, geo, placement, or device.";
        setError(message);
        setAssignment(null);
        return;
      }
      setAssignment(payload);
      localStorage.setItem("partnerLatestAd", JSON.stringify(payload));
    } catch (err) {
      setError("Unable to request an ad. Check your connection and try again.");
      setAssignment(null);
    } finally {
      setLoading(false);
    }
  };

  const recordImpression = async () => {
    if (!assignment) return;
    try {
      await apiFetch(`/track/impression?code=${assignment.assignment_code}`, {
        method: "POST"
      });
    } catch (err) {
      setError("Unable to record impression.");
    }
  };

  const trackingUrl = assignment
    ? `${window.location.origin}${assignment.tracking_url}`
    : "";

  const embedSnippet = assignment
    ? `<a href="${trackingUrl}" target="_blank" rel="noreferrer"><img src="${assignment.ad.image_url}" alt="${assignment.ad.title}" /></a>`
    : "";

  const copySnippet = async () => {
    if (!embedSnippet) return;
    if (!navigator?.clipboard) {
      setError("Copy is not supported in this browser.");
      return;
    }
    try {
      await navigator.clipboard.writeText(embedSnippet);
      setSnippetCopied(true);
      window.setTimeout(() => setSnippetCopied(false), 1500);
    } catch (err) {
      setError("Unable to copy the embed snippet.");
    }
  };

  const breakdown = assignment?.score_breakdown || null;
  const formatNumber = (value, digits = 2) => {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed.toFixed(digits) : "0.00";
  };
  const formatPercent = (value) => {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? `${(parsed * 100).toFixed(2)}%` : "0.00%";
  };
  const tldrBullets = [
    "Matches your targeting hints (if provided).",
    "Quality affects ranking — never billing.",
    "Market Stability Guard reduces abuse, not earnings."
  ];
  const getDomain = (url) => {
    if (!url) return "";
    try {
      const parsed = new URL(url);
      return parsed.hostname.replace(/^www\./, "");
    } catch (err) {
      return url.replace(/^https?:\/\//, "").split("/")[0];
    }
  };
  const destinationDomain = assignment ? getDomain(assignment.ad.destination_url) : "";
  const breakdownRows = breakdown
    ? [
        ["Profit", breakdown.profit],
        ["Profit multiplier", breakdown.alpha_profit],
        [
          "Smoothed CTR",
          formatPercent(breakdown.ctr)
        ],
        ["CTR weight", breakdown.ctr_weight],
        ["CTR multiplier", breakdown.beta_ctr],
        ["Targeting bonus", breakdown.targeting_bonus],
        ["Targeting multiplier", breakdown.gamma_targeting],
        [
          "Partner reject rate",
          formatPercent(breakdown.partner_reject_rate),
          UI_STRINGS.common.rejectSignalTooltip
        ],
        [
          "Partner reject penalty",
          breakdown.partner_reject_penalty,
          UI_STRINGS.common.rejectSignalTooltip
        ],
        ["Quality multiplier", breakdown.delta_quality],
        ["Partner quality penalty", breakdown.partner_quality_penalty],
        ["Delivery boost", breakdown.delivery_boost ?? 0],
        ["Exploration bonus", breakdown.exploration_bonus ?? 0],
        ["Total score", breakdown.total]
      ]
    : [];
  const qualityStates = {
    NEW: {
      label: "~ NEW",
      tone: "new",
      tooltip: "New partner signal. Quality will stabilize with more data."
    },
    STABLE: {
      label: "OK STABLE",
      tone: "stable",
      tooltip: "Stable quality signal."
    },
    AT_RISK: {
      label: "! AT RISK",
      tone: "at-risk",
      tooltip: "Rising reject rate. Avoid rapid refreshes."
    },
    RISKY: {
      label: "!! RISKY",
      tone: "risky",
      tooltip: "High reject rate. Reduce duplicate clicks."
    },
    RECOVERING: {
      label: "~ RECOVERING",
      tone: "recovering",
      tooltip: "Quality is improving after recent rejects."
    }
  };
  const qualityBadge = breakdown?.partner_quality_state
    ? qualityStates[breakdown.partner_quality_state] || null
    : null;

  const showFallback = previewBlocked || !assignment?.ad?.image_url;
  const fallbackTitle = previewBlocked
    ? "Preview blocked by your browser"
    : "Preview unavailable";
  const fallbackNote = previewBlocked
    ? "This does NOT affect delivery or tracking. Try incognito or allow images for localhost."
    : "Delivery and tracking are unaffected. Check the image URL if available.";

  return (
    <main className="page dashboard">
      <section className="panel">
        <RoleHeader
          title={`Welcome, ${user?.email}`}
          subtitle={UI_STRINGS.partner.welcomeSubtitle}
        />
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
        <div className="grid">
          <section className="card">
            <h2>Get an ad</h2>
            <div className="form">
              <label className="field">
                <span className="field-label">
                  Category
                  <span
                    className="tooltip"
                    tabIndex="0"
                    data-tooltip={UI_STRINGS.partner.filterCategoryTooltip}
                  >
                    i
                  </span>
                </span>
                <input
                  name="category"
                  value={filters.category}
                  onChange={handleChange}
                  placeholder="Fitness"
                />
                <span className="helper-text">{UI_STRINGS.partner.filterCategoryTooltip}</span>
              </label>
              <label className="field">
                <span className="field-label">
                  Geo
                  <span
                    className="tooltip"
                    tabIndex="0"
                    data-tooltip={UI_STRINGS.partner.filterGeoTooltip}
                  >
                    i
                  </span>
                </span>
                <input
                  name="geo"
                  value={filters.geo}
                  onChange={handleChange}
                  placeholder="US"
                />
                <span className="helper-text">{UI_STRINGS.partner.filterGeoTooltip}</span>
              </label>
              <label className="field">
                <span className="field-label">
                  Placement
                  <span
                    className="tooltip"
                    tabIndex="0"
                    data-tooltip={UI_STRINGS.partner.filterPlacementTooltip}
                  >
                    i
                  </span>
                </span>
                <input
                  name="placement"
                  value={filters.placement}
                  onChange={handleChange}
                  placeholder="Sidebar"
                />
                <span className="helper-text">{UI_STRINGS.partner.filterPlacementTooltip}</span>
              </label>
              <label className="field">
                <span className="field-label">
                  Device
                  <span
                    className="tooltip"
                    tabIndex="0"
                    data-tooltip={UI_STRINGS.partner.filterDeviceTooltip}
                  >
                    i
                  </span>
                </span>
                <input
                  name="device"
                  value={filters.device}
                  onChange={handleChange}
                  placeholder="Mobile"
                />
                <span className="helper-text">{UI_STRINGS.partner.filterDeviceTooltip}</span>
              </label>
              <button className="button primary" type="button" onClick={requestAd}>
                {loading ? "Requesting..." : "Request ad"}
              </button>
              {error ? <p className="error">{error}</p> : null}
              <p className="muted earnings-note">
                You earn only from accepted clicks. Rejected clicks never pay.
              </p>
            </div>
          </section>
          <section className="card">
            <h2>Ad preview</h2>
            {!assignment ? (
              <p className="muted">Request an ad to see the creative.</p>
            ) : (
              <div className="ad-preview">
                <div className="ad-placement">
                  {showFallback ? (
                    <div className="ad-preview-fallback">
                      <p className="row-title">{fallbackTitle}</p>
                      <p className="muted">{fallbackNote}</p>
                      <span className="ad-domain">{destinationDomain}</span>
                      <h3>{assignment.ad.title}</h3>
                      <p>{assignment.ad.body}</p>
                    </div>
                  ) : (
                    <>
                      <img
                        src={assignment.ad.image_url}
                        alt={assignment.ad.title}
                        onError={() => setPreviewBlocked(true)}
                      />
                      <div className="ad-placement-body">
                        <span className="ad-domain">{destinationDomain}</span>
                        <h3>{assignment.ad.title}</h3>
                        <p>{assignment.ad.body}</p>
                      </div>
                    </>
                  )}
                </div>
                <div className="actions">
                  <button
                    className="button ghost"
                    type="button"
                    onClick={recordImpression}
                    title={UI_STRINGS.common.recordImpressionTooltip}
                  >
                    Record impression
                  </button>
                  <a
                    className="button primary"
                    href={trackingUrl}
                    target="_blank"
                    rel="noreferrer"
                    title={UI_STRINGS.common.testClickTooltip}
                  >
                    Test click
                  </a>
                </div>
                <div className="snippet">
                  <p className="muted">Embed snippet</p>
                  <textarea readOnly value={embedSnippet} rows={3} />
                  <button className="button ghost" type="button" onClick={copySnippet}>
                    {snippetCopied ? "Copied" : "Copy snippet"}
                  </button>
                </div>
                <div className="card subtle">
                  <h3>Why this ad?</h3>
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
                    <p className="muted">{assignment.explanation || "No explanation yet."}</p>
                    {qualityBadge ? (
                      <div className="quality-alert">
                        <span
                          className={`badge ${qualityBadge.tone}`}
                          title={qualityBadge.tooltip}
                        >
                          {qualityBadge.label}
                        </span>
                        <span className="muted">Partner quality state</span>
                      </div>
                    ) : null}
                    {breakdown?.market_note ? (
                      <p className="muted">Market note: {breakdown.market_note}</p>
                    ) : null}
                    {breakdown ? (
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
                          <strong>Targeting bonus</strong> — Extra score for matching partner
                          targeting.
                        </li>
                        <li>
                          <strong>Targeting multiplier</strong> — Adaptive scaling applied to
                          targeting match.
                        </li>
                        <li>
                          <strong>Partner reject rate</strong> — Partner’s recent rejected-click
                          ratio.
                        </li>
                        <li>
                          <strong>Partner reject penalty</strong> — Base penalty from reject rate
                          and its weight.
                        </li>
                        <li>
                          <strong>Quality multiplier</strong> — Scales penalties based on partner
                          state and market conditions.
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
                          <strong>Exploration bonus</strong> — Bonus for new ads or partners
                          during exploration.
                        </li>
                        <li>
                          <strong>Total score</strong> — Final ranking score used by the matcher.
                        </li>
                      </ul>
                    </details>
                  </details>
                </div>
              </div>
            )}
          </section>
        </div>
      </section>
    </main>
  );
};

export default PartnerHome;
