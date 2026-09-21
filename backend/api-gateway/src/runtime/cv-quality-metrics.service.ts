import { Injectable, Logger } from '@nestjs/common';
import { RedisService } from '../redis/redis.service';

type CvKind = 'cv' | 'non_cv' | 'ambiguous';

export interface CvAssessmentSnapshot {
  counters: Record<string, number>;
  rates: {
    acceptanceRate: number;
    nonCvRejectionRate: number;
    ambiguousRate: number;
    noiseRate: number;
  };
  updatedAt: string | null;
}

@Injectable()
export class CvQualityMetricsService {
  private readonly logger = new Logger(CvQualityMetricsService.name);
  private readonly key = 'runtime:cv-quality:v1';
  private readonly updatedAtKey = 'runtime:cv-quality:v1:updated_at';

  constructor(private readonly redis: RedisService) {}

  async recordAssessment(input: {
    documentKind: CvKind;
    accepted: boolean;
    cvConfidence: number;
    signalSummary?: {
      negativeSignals?: number;
      sectionSignals?: number;
      contactSignals?: number;
      [key: string]: number | undefined;
    };
  }) {
    try {
      await this.redis.hIncrBy(this.key, 'total', 1);
      await this.redis.hIncrBy(this.key, `kind_${input.documentKind}`, 1);
      if (input.accepted) {
        await this.redis.hIncrBy(this.key, 'accepted', 1);
      }
      if (input.documentKind === 'non_cv') {
        await this.redis.hIncrBy(this.key, 'rejected_non_cv', 1);
      }
      if (input.documentKind === 'ambiguous') {
        await this.redis.hIncrBy(this.key, 'ambiguous', 1);
      }
      if (Number(input.cvConfidence) < 0.5) {
        await this.redis.hIncrBy(this.key, 'low_confidence', 1);
      }
      const noiseSignals = Number(input.signalSummary?.negativeSignals ?? 0);
      if (noiseSignals > 0) {
        await this.redis.hIncrBy(this.key, 'noise_cases', 1);
      }
      await this.redis.set(this.updatedAtKey, new Date().toISOString());
    } catch (error) {
      this.logger.warn(`Impossible d'enregistrer les metriques CV: ${String(error)}`);
    }
  }

  async recordExtractionError() {
    try {
      await this.redis.hIncrBy(this.key, 'extraction_errors', 1);
      await this.redis.hIncrBy(this.key, 'total', 1);
      await this.redis.set(this.updatedAtKey, new Date().toISOString());
    } catch (error) {
      this.logger.warn(`Impossible d'enregistrer l'erreur d'extraction CV: ${String(error)}`);
    }
  }

  async snapshot(): Promise<CvAssessmentSnapshot> {
    let counters: Record<string, number> = {};
    let updatedAt: string | null = null;
    try {
      const raw = await this.redis.hGetAll(this.key);
      counters = Object.fromEntries(
        Object.entries(raw || {}).map(([k, v]) => [k, Number(v || 0)]),
      );
      const ts = await this.redis.get(this.updatedAtKey);
      updatedAt = ts ? String(ts) : null;
    } catch (error) {
      this.logger.warn(`Impossible de lire les metriques CV: ${String(error)}`);
    }

    const total = Math.max(1, Number(counters.total || 0));
    const accepted = Number(counters.accepted || 0);
    const rejected = Number(counters.rejected_non_cv || 0);
    const ambiguous = Number(counters.ambiguous || 0);
    const noise = Number(counters.noise_cases || 0);

    return {
      counters,
      rates: {
        acceptanceRate: Number((accepted / total).toFixed(4)),
        nonCvRejectionRate: Number((rejected / total).toFixed(4)),
        ambiguousRate: Number((ambiguous / total).toFixed(4)),
        noiseRate: Number((noise / total).toFixed(4)),
      },
      updatedAt,
    };
  }
}
