import { mapAssistantStructured, mapAtsLite } from './graphql.shared-mappers';

export function mapSearchResponse(data: any, query: string) {
  return {
    query: data.query ?? query,
    total: Number(data.total ?? 0),
    backend: data.backend ?? null,
    searchType: data.search_type ?? data.searchType ?? null,
    rerankApplied: Boolean(data.rerank_applied ?? data.rerankApplied ?? false),
    results: Array.isArray(data.results)
      ? data.results.map((r: any) => ({
          id: String(r.id ?? ''),
          title: String(r.title ?? ''),
          company: r.company ?? null,
          location: r.location ?? null,
          contractType: r.contract_type ?? r.contractType ?? null,
          sourceName: r.source_name ?? r.sourceName ?? null,
          sourceUrl: r.source_url ?? r.sourceUrl ?? null,
          postedDate: r.posted_date ?? r.postedDate ?? null,
          score: r.score ?? null,
          salary: r.salary ?? null,
          description: r.description ?? null,
        }))
      : [],
  };
}

export function mapRecommendationResponse(data: any) {
  return {
    cvAnalysis: {
      skills: data.cv_analysis?.skills ?? [],
      experienceYears: data.cv_analysis?.experience_years ?? null,
      educationLevel: data.cv_analysis?.education_level ?? null,
      rawTextPreview: data.cv_analysis?.raw_text_preview ?? null,
    },
    atsLite: mapAtsLite(data.ats_lite),
    queryUsed: data.query_used ?? '',
    totalResults: Number(data.total_results ?? 0),
    jobs: Array.isArray(data.jobs)
      ? data.jobs.map((j: any) => ({
          id: String(j.id ?? ''),
          title: String(j.title ?? ''),
          company: j.company ?? null,
          location: j.location ?? null,
          contractType: j.contract_type ?? j.contractType ?? null,
          sourceName: j.source_name ?? j.sourceName ?? null,
          sourceUrl: j.source_url ?? j.sourceUrl ?? null,
          postedDate: j.posted_date ?? j.postedDate ?? null,
          score: j.score ?? null,
          summary: j.summary ?? null,
        }))
      : [],
    assistantMessage: data.assistant_message ?? '',
    llmUsed: Boolean(data.llm_used),
    llmProvider: data.llm_provider ?? null,
    llmModel: data.llm_model ?? null,
    llmError: data.llm_error ?? null,
    llmStatus: data.llm_status ?? null,
    assistantStructured: mapAssistantStructured(data.assistant_structured),
  };
}
