export function mapAssistantStructured(value: any) {
  if (!value || typeof value !== 'object') {
    return null;
  }
  const recommendedJobs = Array.isArray(value.recommendedJobs)
    ? value.recommendedJobs
    : Array.isArray(value.recommended_jobs)
      ? value.recommended_jobs
      : [];

  return {
    mode: String(value.mode ?? ''),
    profileSummary: String(value.profileSummary ?? value.profile_summary ?? ''),
    strengths: Array.isArray(value.strengths)
      ? value.strengths.map((x: any) => String(x))
      : [],
    gaps: Array.isArray(value.gaps) ? value.gaps.map((x: any) => String(x)) : [],
    recommendedJobs: recommendedJobs.map((item: any) => ({
      jobId: String(item.jobId ?? item.job_id ?? ''),
      title: String(item.title ?? ''),
      why: String(item.why ?? ''),
      url: String(item.url ?? ''),
      cvImprovement: String(item.cvImprovement ?? item.cv_improvement ?? ''),
    })),
    scoreExplanation: String(value.scoreExplanation ?? value.score_explanation ?? ''),
    offerPlaybooks: (Array.isArray(value.offerPlaybooks)
      ? value.offerPlaybooks
      : Array.isArray(value.offer_playbooks)
        ? value.offer_playbooks
        : []
    ).map((item: any) => ({
      jobId: String(item.jobId ?? item.job_id ?? ''),
      title: String(item.title ?? ''),
      url: String(item.url ?? ''),
      whyFit: String(item.whyFit ?? item.why_fit ?? ''),
      cvDelta: String(item.cvDelta ?? item.cv_delta ?? ''),
      rewrite: {
        targetTitle: String(
          item?.rewrite?.targetTitle ?? item?.rewrite?.target_title ?? '',
        ),
        targetSummary: String(
          item?.rewrite?.targetSummary ?? item?.rewrite?.target_summary ?? '',
        ),
        experienceBullets: Array.isArray(
          item?.rewrite?.experienceBullets ?? item?.rewrite?.experience_bullets,
        )
          ? (item?.rewrite?.experienceBullets ?? item?.rewrite?.experience_bullets).map(
              (x: any) => String(x),
            )
          : [],
      },
      evidence: Array.isArray(item?.evidence)
        ? item.evidence.map((x: any) => String(x))
        : [],
    })),
    actions: Array.isArray(value.actions)
      ? value.actions.map((x: any) => String(x))
      : [],
    reasonIfNoMatch: value.reasonIfNoMatch ?? value.reason_if_no_match ?? null,
  };
}

export function mapAtsLite(value: any) {
  if (!value || typeof value !== 'object') {
    return null;
  }
  return {
    overallScore: Number(value.overallScore ?? value.overall_score ?? 0),
    structureScore: Number(value.structureScore ?? value.structure_score ?? 0),
    alignmentScore: Number(value.alignmentScore ?? value.alignment_score ?? 0),
    evidenceScore: Number(value.evidenceScore ?? value.evidence_score ?? 0),
    readinessLabel: String(value.readinessLabel ?? value.readiness_label ?? ''),
    summary: String(value.summary ?? ''),
    matchedKeywords: Array.isArray(value.matchedKeywords ?? value.matched_keywords)
      ? (value.matchedKeywords ?? value.matched_keywords).map((x: any) => String(x))
      : [],
    missingKeywords: Array.isArray(value.missingKeywords ?? value.missing_keywords)
      ? (value.missingKeywords ?? value.missing_keywords).map((x: any) => String(x))
      : [],
    suggestions: Array.isArray(value.suggestions)
      ? value.suggestions.map((x: any) => String(x))
      : [],
    actionPlan: Array.isArray(value.actionPlan ?? value.action_plan)
      ? (value.actionPlan ?? value.action_plan).map((x: any) => String(x))
      : [],
  };
}
