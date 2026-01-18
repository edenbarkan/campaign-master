import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import RoleHeader from "../components/RoleHeader.jsx";
import { useAuth } from "../contexts/AuthContext";
import { apiFetch } from "../lib/api";
import { safeStorage } from "../lib/storage";
import { UI_STRINGS } from "../lib/strings";

const round2 = (value) => {
  if (Number.isNaN(value)) return 0;
  return Math.round((value + Number.EPSILON) * 100) / 100;
};

const computePayout = (maxCpc, feePercent) => {
  const fee = Number(feePercent);
  if (Number.isNaN(maxCpc) || Number.isNaN(fee)) return 0;
  return round2(maxCpc * (1 - fee / 100));
};

const emptyForm = {
  name: "",
  status: "active",
  budget_total: "",
  budget_spent: 0,
  max_cpc: "",
  targeting_category: "",
  targeting_geo: "",
  targeting_device: "",
  targeting_placement: "",
  start_date: "",
  end_date: ""
};

const BuyerHome = () => {
  const { user, token } = useAuth();
  const [viewMode, setViewMode] = useState(() =>
    safeStorage.get("buyer_view_mode", "simple")
  );
  const [campaigns, setCampaigns] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [toast, setToast] = useState(null);
  const [platformFeePercent, setPlatformFeePercent] = useState(30);
  const maxCpcValue = Number(form.max_cpc);
  const budgetTotalValue = Number(form.budget_total);
  const budgetSpentValue = Number(form.budget_spent || 0);
  const computedPayout = Number.isFinite(maxCpcValue)
    ? computePayout(maxCpcValue, platformFeePercent)
    : null;
  const remainingBudget =
    Number.isFinite(budgetTotalValue) && Number.isFinite(budgetSpentValue)
      ? round2(Math.max(0, budgetTotalValue - budgetSpentValue))
      : null;
  const isAdvanced = viewMode === "advanced";
  const formatMoney = (value) => {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed.toFixed(2) : "0.00";
  };

  const loadCampaigns = async () => {
    try {
      const payload = await apiFetch("/buyer/campaigns", { token });
      setCampaigns(payload.campaigns || []);
      const metaFee = payload.meta?.platform_fee_percent;
      if (typeof metaFee === "number") {
        setPlatformFeePercent(metaFee);
      } else if (payload.campaigns?.length) {
        const fee = payload.campaigns[0]?.platform_fee_percent;
        if (typeof fee === "number") {
          setPlatformFeePercent(fee);
        }
      }
    } catch (err) {
      setError("Unable to load campaigns.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!token) return;
    loadCampaigns();
  }, [token]);

  useEffect(() => {
    safeStorage.set("buyer_view_mode", viewMode);
  }, [viewMode]);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");

    const maxCpc = Number(form.max_cpc);

    if (Number.isNaN(maxCpc)) {
      setError("Enter a numeric max CPC.");
      return;
    }

    if (maxCpc <= 0) {
      setError("Max CPC must be greater than zero.");
      return;
    }

    const payload = {
      name: form.name,
      status: form.status,
      budget_total: Number(form.budget_total),
      max_cpc: maxCpc,
      targeting: {
        category: form.targeting_category || null,
        geo: form.targeting_geo || null,
        device: form.targeting_device || null,
        placement: form.targeting_placement || null
      },
      start_date: form.start_date || null,
      end_date: form.end_date || null
    };

    try {
      if (editingId) {
        const response = await apiFetch(`/buyer/campaigns/${editingId}`, {
          method: "PUT",
          body: payload,
          token
        });
        if (typeof response.campaign?.platform_fee_percent === "number") {
          setPlatformFeePercent(response.campaign.platform_fee_percent);
        }
      } else {
        const response = await apiFetch("/buyer/campaigns", {
          method: "POST",
          body: payload,
          token
        });
        if (typeof response.campaign?.platform_fee_percent === "number") {
          setPlatformFeePercent(response.campaign.platform_fee_percent);
        }
        setToast({
          message: "Campaign created.",
          campaignId: response.campaign?.id
        });
      }
      setForm(emptyForm);
      setEditingId(null);
      loadCampaigns();
    } catch (err) {
      setError("Unable to save campaign. Check the fields and try again.");
    }
  };

  const handleEdit = (campaign) => {
    setEditingId(campaign.id);
    setForm({
      name: campaign.name,
      status: campaign.status,
      budget_total: campaign.budget_total,
      budget_spent: campaign.budget_spent ?? 0,
      max_cpc: campaign.max_cpc ?? campaign.buyer_cpc,
      targeting_category: campaign.targeting?.category || "",
      targeting_geo: campaign.targeting?.geo || "",
      targeting_device: campaign.targeting?.device || "",
      targeting_placement: campaign.targeting?.placement || "",
      start_date: campaign.start_date || "",
      end_date: campaign.end_date || ""
    });
    if (typeof campaign.platform_fee_percent === "number") {
      setPlatformFeePercent(campaign.platform_fee_percent);
    }
  };

  const handleReset = () => {
    setEditingId(null);
    setForm(emptyForm);
    setError("");
  };

  return (
    <main className="page dashboard">
      <section className="panel">
        <RoleHeader
          title={`Hello, ${user?.email}`}
          subtitle={UI_STRINGS.buyer.launchSubtitle}
        />
        {toast ? (
          <div className="toast">
            <span>{toast.message}</span>
            <div className="actions">
              {toast.campaignId ? (
                <Link className="button ghost small" to={`/buyer/campaigns/${toast.campaignId}`}>
                  View campaign
                </Link>
              ) : null}
              <button className="button ghost small" type="button" onClick={() => setToast(null)}>
                Dismiss
              </button>
            </div>
          </div>
        ) : null}
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
        <div className="grid">
          <section className="card">
            <h2>{editingId ? "Edit campaign" : "New campaign"}</h2>
            <form className="form" id="campaign-form" onSubmit={handleSubmit}>
              <label className="field">
                <span>Name</span>
                <input
                  name="name"
                  value={form.name}
                  onChange={handleChange}
                  placeholder="Spring push"
                  required
                />
              </label>
              <label className="field">
                <span>Status</span>
                <select name="status" value={form.status} onChange={handleChange}>
                  <option value="active">Active</option>
                  <option value="paused">Paused</option>
                </select>
                <span className="helper-text">{UI_STRINGS.common.statusHelper}</span>
              </label>
              <div className="field-row">
                <label className="field">
                  <span>Total budget</span>
                  <input
                    name="budget_total"
                    type="number"
                    step="0.01"
                    value={form.budget_total}
                    onChange={handleChange}
                    placeholder="1200"
                    required
                  />
                </label>
                <label className="field">
                  <span>Max CPC</span>
                  <input
                    name="max_cpc"
                    type="number"
                    step="0.01"
                    value={form.max_cpc}
                    onChange={handleChange}
                    placeholder="2.50"
                    required
                  />
                </label>
              </div>
              <div className="field-row">
                <label className="field">
                  <span>Platform fee</span>
                  <input value={`${platformFeePercent}%`} readOnly />
                </label>
                <label className="field">
                  <span title={UI_STRINGS.common.partnerPayoutTooltip}>
                    Partner payout (estimated)
                  </span>
                  <input
                    value={
                      computedPayout === null ? "--" : `$${computedPayout.toFixed(2)}`
                    }
                    readOnly
                  />
                </label>
              </div>
              <div className="field-row">
                <label className="field">
                  <span>Remaining budget (est.)</span>
                  <input
                    value={remainingBudget === null ? "--" : `$${remainingBudget.toFixed(2)}`}
                    readOnly
                  />
                </label>
              </div>
              <span className="helper-text">
                Estimates update as you edit. Final values come from accepted clicks.
              </span>
              {isAdvanced ? (
                <>
                  <div className="field-row">
                    <label className="field">
                      <span>Targeting category</span>
                      <input
                        name="targeting_category"
                        value={form.targeting_category}
                        onChange={handleChange}
                        placeholder="Fitness"
                      />
                    </label>
                    <label className="field">
                      <span>Targeting geo</span>
                      <input
                        name="targeting_geo"
                        value={form.targeting_geo}
                        onChange={handleChange}
                        placeholder="US"
                      />
                    </label>
                  </div>
                  <div className="field-row">
                    <label className="field">
                      <span>Targeting device</span>
                      <input
                        name="targeting_device"
                        value={form.targeting_device}
                        onChange={handleChange}
                        placeholder="Mobile"
                      />
                    </label>
                    <label className="field">
                      <span>Targeting placement</span>
                      <input
                        name="targeting_placement"
                        value={form.targeting_placement}
                        onChange={handleChange}
                        placeholder="Sidebar"
                      />
                    </label>
                  </div>
                  <div className="field-row">
                    <label className="field">
                      <span>Start date</span>
                      <input
                        name="start_date"
                        type="date"
                        value={form.start_date}
                        onChange={handleChange}
                      />
                    </label>
                    <label className="field">
                      <span>End date</span>
                      <input
                        name="end_date"
                        type="date"
                        value={form.end_date}
                        onChange={handleChange}
                      />
                    </label>
                  </div>
                </>
              ) : null}
              {error ? <p className="error">{error}</p> : null}
              <div className="actions">
                <button className="button primary" type="submit">
                  {editingId ? "Update campaign" : "Create campaign"}
                </button>
                {editingId ? (
                  <button className="button ghost" type="button" onClick={handleReset}>
                    Cancel
                  </button>
                ) : null}
              </div>
            </form>
          </section>
          <section className="card">
            <h2>Campaigns</h2>
            {loading ? <p className="muted">Loading campaigns...</p> : null}
            {!loading && campaigns.length === 0 ? (
              <div className="empty-state">
                <p className="muted">No campaigns yet. Start with budget + max CPC.</p>
                <button
                  className="button primary"
                  type="button"
                  onClick={() =>
                    document.getElementById("campaign-form")?.scrollIntoView({
                      behavior: "smooth"
                    })
                  }
                >
                  Create your first campaign
                </button>
              </div>
            ) : null}
            <div className="table">
              {campaigns.map((campaign) => (
                <div className="table-row" key={campaign.id}>
                  <div>
                    <p className="row-title">{campaign.name}</p>
                    <p className="muted">
                      {campaign.status}
                      {isAdvanced
                        ? ` · $${formatMoney(campaign.max_cpc ?? campaign.buyer_cpc)} max CPC`
                        : ""}
                    </p>
                    {campaign.delivery_status ? (
                      <span
                        className={`badge ${
                          Number(campaign.budget_spent || 0) === 0
                            ? "not_serving"
                            : campaign.delivery_status.toLowerCase()
                        }`}
                      >
                        {Number(campaign.budget_spent || 0) === 0
                          ? "Not serving yet"
                          : campaign.delivery_status.replace("_", " ")}
                      </span>
                    ) : null}
                  </div>
                  <div className="row-metrics">
                    <span>${formatMoney(campaign.budget_spent)} spent</span>
                    {isAdvanced ? (
                      <span>${formatMoney(campaign.budget_remaining)} left</span>
                    ) : null}
                  </div>
                  <button
                    className="button ghost"
                    type="button"
                    onClick={() => handleEdit(campaign)}
                  >
                    Edit
                  </button>
                  <Link
                    className="button ghost"
                    to={`/buyer/campaigns/${campaign.id}`}
                  >
                    Ads
                  </Link>
                </div>
              ))}
            </div>
          </section>
        </div>
      </section>
    </main>
  );
};

export default BuyerHome;
