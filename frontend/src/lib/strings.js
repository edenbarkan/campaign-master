export const UI_STRINGS = {
  common: {
    simpleView: "Simple view",
    advancedView: "Advanced view",
    marketStabilityGuardTitle: "Market Stability Guard",
    marketStabilityGuardNote:
      "Stabilizes delivery quality — never adds hidden costs. Ranking only.",
    scoringDisclaimer: "Scoring affects ranking only — billing is unchanged.",
    recordImpressionTooltip: "Counts a single view for analytics. No billing impact.",
    testClickTooltip: "Opens the tracking link. Click billing follows normal rules.",
    rejectSignalTooltip: "Partner-derived quality signal; not tied to a single ad.",
    partnerPayoutTooltip: "Computed as Max CPC × (1 - platform fee).",
    statusHelper: "Status affects delivery. Paused campaigns will not serve.",
    imageUrlHelper: "Use a full https:// image URL.",
    destinationUrlHelper: "Use the final landing page URL."
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
        "Request an ad and place the tracking link on your site.",
        "Record impressions to keep CTR accurate.",
        "Quality signals protect the marketplace — no hidden costs.",
        "Get paid per accepted click."
      ]
    },
    buyer: {
      title: "Buyer quick start",
      steps: [
        "Create a campaign with budget and max CPC.",
        "Add ads with image + destination URL.",
        "Status controls delivery — paused campaigns do not serve.",
        "Spend is charged only on accepted clicks."
      ]
    },
    admin: {
      title: "Admin quick start",
      steps: [
        "Marketplace health tracks fill, reject rate, and take rate.",
        "Risk trends highlight rejected clicks and causes.",
        "Under-delivery flags pacing issues, not billing errors.",
        "No hidden costs — scoring only changes ranking."
      ]
    }
  }
};
