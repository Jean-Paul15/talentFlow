import { CvAnalysisJob } from '@prisma/client';
import { etaHint, stageLabel } from './cv-jobs.stage';

export function toCvJobDto(job: CvAnalysisJob) {
  const result = asRecord(job.resultPayload);
  const historyId = String(result?.historyId ?? '');
  return {
    jobId: job.id,
    status: job.status,
    stage: job.stage,
    progress: job.progress,
    stageLabel: stageLabel(job.stage),
    etaHint: etaHint(job.stage),
    inputType: job.inputType,
    fileName: job.fileName,
    error: job.error,
    updatedAt: job.updatedAt.toISOString(),
    createdAt: job.createdAt.toISOString(),
    completedAt: job.completedAt?.toISOString() ?? null,
    resultReady: Boolean(historyId),
    historyId: historyId || null,
    extractionMeta: job.extractionMeta,
  };
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : null;
}
