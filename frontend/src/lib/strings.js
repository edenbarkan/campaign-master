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
    ctrTooltip: "Clicks divided by impressions.",
    epcTooltip: "Avg earnings per accepted click.",
    fillRateTooltip: "Share of partner requests that were filled with an ad.",
    costEfficiencyTooltip: "Accepted clicks per $1 spent.",
    effectiveCpcTooltip: "Avg cost per accepted click.",
    budgetLeftTooltip: "Remaining campaign budget available to spend.",
    maxCpcTooltip: "Max you pay per accepted click (set per campaign).",
    earningsTooltip: "Earnings from accepted clicks only.",
    rejectionRateTooltip: "Rejected clicks never pay; rate reflects quality checks.",
    totalRequestsTooltip: "How many ads you requested.",
    filledRequestsTooltip: "Requests that returned an ad.",
    unfilledRequestsTooltip: "Requests with no eligible ad or capped.",
    totalSpendTooltip: "Total spend from accepted clicks.",
    totalEarningsTooltip: "Total partner earnings from accepted clicks.",
    totalProfitTooltip: "Platform profit from accepted clicks.",
    totalClicksTooltip: "Total accepted clicks.",
    rejectedClicksTooltip: "Rejected clicks in this range.",
    topReasonTooltip: "Most common rejection reason in this range.",
    takeRateTooltip: "Platform profit as a share of spend.",
    qualityStateTooltip: "Partner quality based on recent traffic checks.",
    impressionsTooltip: "Total impressions recorded.",
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
