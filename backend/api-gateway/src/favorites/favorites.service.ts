// Favorites Service - Sauvegarde des offres

import { Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { RuntimeCacheService } from '../runtime/runtime-cache.service';

@Injectable()
export class FavoritesService {
  constructor(
    private prisma: PrismaService,
    private readonly runtimeCache: RuntimeCacheService,
  ) {}

  async addFavorite(userId: string, jobId: string, jobData: any) {
    const entry = await this.prisma.favorite.upsert({
      where: { userId_jobId: { userId, jobId } },
      create: {
        userId,
        jobId,
        title: jobData.title,
        company: jobData.company ?? '',
        description: jobData.description ?? jobData.summary ?? '',
        location: jobData.location ?? '',
        contractType: jobData.contractType ?? jobData.contract_type ?? null,
        salary: jobData.salary ?? null,
        sourceName: jobData.sourceName ?? jobData.source_name ?? null,
        sourceUrl: jobData.sourceUrl ?? jobData.source_url ?? null,
        postedDate: jobData.postedDate ?? jobData.posted_date ?? null,
        score: jobData.score ?? null,
      },
      update: {
        title: jobData.title,
        company: jobData.company ?? '',
        description: jobData.description ?? jobData.summary ?? '',
        location: jobData.location ?? '',
        contractType: jobData.contractType ?? jobData.contract_type ?? null,
        salary: jobData.salary ?? null,
        sourceName: jobData.sourceName ?? jobData.source_name ?? null,
        sourceUrl: jobData.sourceUrl ?? jobData.source_url ?? null,
        postedDate: jobData.postedDate ?? jobData.posted_date ?? null,
        score: jobData.score ?? null,
      },
    });

    await this.runtimeCache.bump('favorites');
    return entry;
  }

  async removeFavorite(userId: string, jobId: string) {
    const existing = await this.prisma.favorite.findUnique({
      where: { userId_jobId: { userId, jobId } },
      select: { id: true },
    });

    if (!existing) {
      return false;
    }

    await this.prisma.favorite.delete({
      where: { userId_jobId: { userId, jobId } },
    });
    await this.runtimeCache.bump('favorites');
    return true;
  }

  async getFavorites(userId: string, limit = 20, offset = 0) {
    return this.prisma.favorite.findMany({
      where: { userId },
      take: limit,
      skip: offset,
      orderBy: { createdAt: 'desc' },
    });
  }

  async isFavorite(userId: string, jobId: string) {
    const fav = await this.prisma.favorite.findUnique({
      where: { userId_jobId: { userId, jobId } },
    });
    return !!fav;
  }
}
