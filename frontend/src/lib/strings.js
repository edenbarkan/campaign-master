export const UI_STRINGS = {
  common: {
    simpleView: "Simple view",
    advancedView: "Advanced view",
    marketStabilityGuardTitle: "Market Stability Guard",
    marketStabilityGuardNote:
      "Stabilizes delivery quality — never adds hidden costs. Ranking only.",
    scoringDisclaimer: "Scoring affects ranking only — billing is unchanged.",
    viewModeHint: "Simple shows essentials. Advanced shows full details.",
    refreshData: "Refresh data",
    lastUpdatedLabel: "Updated",
    ctrTooltip: "CTR = accepted clicks / accepted impressions. Display only; billing unchanged.",
    epcTooltip: "EPC = earnings per accepted click. Display only; billing unchanged.",
    fillRateTooltip: "Fill rate = filled requests / total requests. Display only; billing unchanged.",
    costEfficiencyTooltip: "Cost efficiency = clicks per $ spend. Display only; billing unchanged.",
    recordImpressionTooltip: "Counts a single view for analytics. No billing impact.",
    testClickTooltip: "Opens the tracking link. Click billing follows normal rules.",
    rejectSignalTooltip: "Partner-derived quality signal; not tied to a single ad.",
    partnerPayoutTooltip: "Computed as Max CPC × (1 - platform fee).",
    statusHelper: "Status affects delivery. Paused campaigns will not serve.",
    imageUrlHelper: "Use a full https:// image URL.",
    destinationUrlHelper: "Use the final landing page URL.",
    howItWorksLabel: "How it works",
    restartOnboarding: "Restart onboarding"
  },
  partner: {
    welcomeSubtitle: "Request a fresh ad and start earning.",
    dashboardSubtitle: "Tracking earnings and click quality.",
    getAdCta: "Get a fresh ad",
    filterCategoryTooltip: "Examples: Fitness, Finance. Optional targeting hint.",
    filterGeoTooltip: "Examples: US, UK. Optional location hint.",
    filterPlacementTooltip: "Examples: Sidebar, Feed. Optional placement hint.",
    filterDeviceTooltip: "Examples: Mobile, Desktop. Optional device hint."
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
        "Get an ad and embed the tracking link (filters are optional).",
        "Track clicks safely — only accepted clicks pay.",
        "Quality stays stable when you avoid duplicate clicks."
      ]
    },
    buyer: {
      title: "Buyer quick start",
      steps: [
        "Create a campaign with budget and max CPC.",
        "Add ads with title, image, and destination URL.",
        "Delivery depends on supply; billing only on accepted clicks."
      ]
    },
    admin: {
      title: "Admin quick start",
      steps: [
        "Review marketplace health at a glance.",
        "Open reject reasons for meaning and mitigation.",
        "Good looks like steady fill and stable rejects."
      ]
    }
  }
};
