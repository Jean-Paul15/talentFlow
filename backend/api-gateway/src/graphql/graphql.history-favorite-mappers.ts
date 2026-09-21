import { mapAssistantStructured, mapAtsLite } from './graphql.shared-mappers';

export function mapHistoryEntry(entry: any) {
  const cvAnalysis =
    entry?.cvAnalysis && typeof entry.cvAnalysis === 'object'
      ? entry.cvAnalysis
      : null;
  const jobs = Array.isArray(entry?.jobsSnapshot) ? entry.jobsSnapshot : [];

  return {
    id: String(entry.id ?? ''),
    cvTextPreview: String(entry.cvTextPreview ?? ''),
    fileName: entry.fileName ?? null,
    queryUsed: String(entry.queryUsed ?? ''),
    locationFilter: entry.locationFilter ?? null,
    contractTypeFilter: entry.contractTypeFilter ?? null,
    assistantMessage: String(entry.assistantMessage ?? ''),
    llmUsed: Boolean(entry.llmUsed),
    llmProvider: entry.llmProvider ?? null,
    llmModel: entry.llmModel ?? null,
    llmError: entry.llmError ?? null,
    llmStatus: entry.llmStatus ?? null,
    totalResults: Number(entry.totalResults ?? 0),
    assistantStructured: mapAssistantStructured(entry.assistantStructured),
    atsLite: mapAtsLite(cvAnalysis?.atsLite ?? null),
    cvAnalysis: cvAnalysis
      ? {
          skills: Array.isArray(cvAnalysis.skills) ? cvAnalysis.skills : [],
          experienceYears: cvAnalysis.experienceYears ?? null,
          educationLevel: cvAnalysis.educationLevel ?? null,
          rawTextPreview: cvAnalysis.rawTextPreview ?? null,
        }
      : null,
    jobs: jobs.map((job: any) => ({
      id: String(job.id ?? ''),
      title: String(job.title ?? ''),
      company: job.company ?? null,
      location: job.location ?? null,
      contractType: job.contractType ?? job.contract_type ?? null,
      sourceName: job.sourceName ?? job.source_name ?? null,
      sourceUrl: job.sourceUrl ?? job.source_url ?? null,
      postedDate: job.postedDate ?? job.posted_date ?? null,
      score: job.score ?? null,
      salary: job.salary ?? null,
      description: job.description ?? null,
      summary: job.summary ?? null,
    })),
    createdAt:
      entry.createdAt instanceof Date
        ? entry.createdAt.toISOString()
        : String(entry.createdAt ?? ''),
  };
}

export function mapFavoriteEntry(entry: any) {
  return {
    id: String(entry.id ?? ''),
    jobId: String(entry.jobId ?? ''),
    title: String(entry.title ?? ''),
    company: entry.company ?? null,
    description: entry.description ?? null,
    location: entry.location ?? null,
    contractType: entry.contractType ?? null,
    salary: entry.salary ?? null,
    sourceName: entry.sourceName ?? null,
    sourceUrl: entry.sourceUrl ?? null,
    postedDate: entry.postedDate ?? null,
    score: entry.score ?? null,
    createdAt:
      entry.createdAt instanceof Date
        ? entry.createdAt.toISOString()
        : String(entry.createdAt ?? ''),
  };
}
