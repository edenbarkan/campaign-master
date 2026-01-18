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
  const isAdvanced = viewMode === "advanced";

  useEffect(() => {
    safeStorage.set("partner_view_mode", viewMode);
  }, [viewMode]);

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
            ? "Frequency cap hit. Try again in a minute or change filters."
            : "No fill available. Try adjusting category, geo, placement, or device.";
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

  const breakdown = assignment?.score_breakdown || null;
  const formatNumber = (value, digits = 2) => {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed.toFixed(digits) : "0.00";
  };
  const formatPercent = (value) => {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? `${(parsed * 100).toFixed(2)}%` : "0.00%";
  };
  const tldrBullets = breakdown
    ? [
        `Profit potential: $${formatNumber(breakdown.profit)} per click.`,
        `CTR estimate: ${formatPercent(breakdown.ctr)}.`,
        breakdown.targeting_bonus > 0 ? "Targeting match boosts rank." : null,
        breakdown.partner_quality_state
          ? `Partner quality: ${breakdown.partner_quality_state}.`
          : null,
        breakdown.delivery_boost > 0 ? "Delivery boost applied to improve pacing." : null,
        breakdown.exploration_applied ? "Exploration bonus applied for new inventory." : null
      ].filter(Boolean)
    : [];
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

  return (
    <main className="page dashboard">
      <section className="panel">
        <RoleHeader
          title={`Welcome, ${user?.email}`}
          subtitle={UI_STRINGS.partner.welcomeSubtitle}
        />
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
        <div className="grid">
          <section className="card">
            <h2>Get an ad</h2>
            <div className="form">
              <label className="field">
                <span>Category</span>
                <input
                  name="category"
                  value={filters.category}
                  onChange={handleChange}
                  placeholder="Fitness"
                />
              </label>
              <label className="field">
                <span>Geo</span>
                <input
                  name="geo"
                  value={filters.geo}
                  onChange={handleChange}
                  placeholder="US"
                />
              </label>
              <label className="field">
                <span>Placement</span>
                <input
                  name="placement"
                  value={filters.placement}
                  onChange={handleChange}
                  placeholder="Sidebar"
                />
              </label>
              <label className="field">
                <span>Device</span>
                <input
                  name="device"
                  value={filters.device}
                  onChange={handleChange}
                  placeholder="Mobile"
                />
              </label>
              <button className="button primary" type="button" onClick={requestAd}>
                {loading ? "Requesting..." : "Request ad"}
              </button>
              {error ? <p className="error">{error}</p> : null}
            </div>
          </section>
          <section className="card">
            <h2>Ad preview</h2>
            {!assignment ? (
              <p className="muted">Request an ad to see the creative.</p>
            ) : (
              <div className="ad-preview">
                <div className="ad-placement">
                  <img src={assignment.ad.image_url} alt={assignment.ad.title} />
                  <div className="ad-placement-body">
                    <span className="ad-domain">{destinationDomain}</span>
                    <h3>{assignment.ad.title}</h3>
                    <p>{assignment.ad.body}</p>
                  </div>
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
                  <p className="muted">{UI_STRINGS.common.scoringDisclaimer}</p>
                  {isAdvanced ? (
                    <>
                      <p className="muted">{assignment.explanation}</p>
                      {breakdown?.partner_quality_state ? (
                        <p className="muted">
                          Partner quality state: {breakdown.partner_quality_state}
                        </p>
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
                            <strong>Profit multiplier</strong> — Adaptive scaling based on
                            market health.
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
                            <strong>Partner reject penalty</strong> — Base penalty from reject
                            rate and its weight.
                          </li>
                          <li>
                            <strong>Quality multiplier</strong> — Scales penalties based on
                            partner state and market conditions.
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
                    </>
                  ) : null}
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
