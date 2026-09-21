import { Injectable, NotFoundException } from '@nestjs/common';
import { Prisma } from '@prisma/client';
import { PrismaService } from '../prisma/prisma.service';
import { RuntimeCacheService } from '../runtime/runtime-cache.service';

export interface RecommendationHistoryPayload {
  cvTextPreview: string;
  fileName?: string | null;
  queryUsed?: string | null;
  locationFilter?: string | null;
  contractTypeFilter?: string | null;
  assistantMessage: string;
  llmUsed?: boolean;
  llmProvider?: string | null;
  llmModel?: string | null;
  llmError?: string | null;
  llmStatus?: string | null;
  totalResults?: number;
  assistantStructured?: Prisma.JsonValue | null;
  cvAnalysis?: Prisma.JsonValue | null;
  jobsSnapshot: Prisma.JsonValue;
}

@Injectable()
export class HistoryService {
  constructor(
    private prisma: PrismaService,
    private readonly runtimeCache: RuntimeCacheService,
  ) {}

  async saveAnalysis(userId: string, data: RecommendationHistoryPayload) {
    const entry = await this.prisma.recommendationHistory.create({
      data: {
        userId,
        cvTextPreview: data.cvTextPreview,
        fileName: data.fileName ?? null,
        queryUsed: data.queryUsed ?? '',
        locationFilter: data.locationFilter ?? null,
        contractTypeFilter: data.contractTypeFilter ?? null,
        assistantMessage: data.assistantMessage,
        llmUsed: Boolean(data.llmUsed),
        llmProvider: data.llmProvider ?? null,
        llmModel: data.llmModel ?? null,
        llmError: data.llmError ?? null,
        llmStatus: data.llmStatus ?? 'fallback_used',
        totalResults: Number(data.totalResults ?? 0),
        assistantStructured: data.assistantStructured ?? Prisma.JsonNull,
        cvAnalysis: data.cvAnalysis ?? Prisma.JsonNull,
        jobsSnapshot: data.jobsSnapshot,
      },
    });

    await this.runtimeCache.bumpMany(['history', 'recommendation']);
    return entry;
  }

  async getHistory(userId: string, limit = 50, offset = 0) {
    return this.prisma.recommendationHistory.findMany({
      where: { userId },
      take: limit,
      skip: offset,
      orderBy: { createdAt: 'desc' },
    });
  }

  async getHistoryEntry(userId: string, historyId: string) {
    const entry = await this.prisma.recommendationHistory.findFirst({
      where: { userId, id: historyId },
    });
    if (!entry) {
      throw new NotFoundException('Historique introuvable');
    }
    return entry;
  }

  async deleteAnalysis(userId: string, analysisId: string) {
    const existing = await this.prisma.recommendationHistory.findFirst({
      where: { id: analysisId, userId },
      select: { id: true },
    });
    if (!existing) {
      throw new NotFoundException('Historique introuvable');
    }

    await this.prisma.recommendationHistory.delete({
      where: { id: analysisId },
    });
    await this.runtimeCache.bumpMany(['history', 'recommendation']);
    return true;
  }
}
