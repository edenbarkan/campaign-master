export const UI_STRINGS = {
  common: {
    simpleView: "Simple view",
    advancedView: "Advanced view",
    marketStabilityGuardTitle: "Market Stability Guard",
    marketStabilityGuardNote:
      "Stabilizes delivery quality — never adds hidden costs. Ranking only.",
    scoringDisclaimer: "Scoring affects ranking only — billing is unchanged.",
    viewModeHint: "Simple shows essentials. Advanced shows full details.",
    recordImpressionTooltip: "Counts a single view for analytics. No billing impact.",
    testClickTooltip: "Opens the tracking link. Click billing follows normal rules.",
    rejectSignalTooltip: "Partner-derived quality signal; not tied to a single ad.",
    partnerPayoutTooltip: "Computed as Max CPC × (1 - platform fee).",
    statusHelper: "Status affects delivery. Paused campaigns will not serve.",
    imageUrlHelper: "Use a full https:// image URL.",
    destinationUrlHelper: "Use the final landing page URL.",
    howItWorksLabel: "How it works"
  },
  partner: {
    welcomeSubtitle: "Request a fresh ad and start earning.",
    dashboardSubtitle: "Tracking earnings and click quality.",
    getAdCta: "Get a fresh ad"
  },
  buyer: {
    dashboardSubtitle: "Tracking spend, clicks, and efficiency.",
    launchSubtitle: "Launch campaigns and manage pricing."
  },
  admin: {
    dashboardSubtitle: "Monitoring platform profit and payouts."
  },
  onboarding: {
    partner: {
      title: "Partner quick start",
      steps: [
        "Request an ad and use the tracking link or embed snippet.",
        "Record impressions to keep CTR accurate.",
        "Quality matters — avoid rapid refreshes and duplicate clicks."
      ]
    },
    buyer: {
      title: "Buyer quick start",
      steps: [
        "Create a campaign with budget and max CPC.",
        "Add ads with an image URL and destination URL.",
        "Billing happens only on accepted clicks."
      ]
    },
    admin: {
      title: "Admin quick start",
      steps: [
        "Review market health: fill, delivery, and take rate.",
        "Monitor risk reasons for rejected clicks.",
        "Use date ranges to interpret trends."
      ]
    }
  }
};
