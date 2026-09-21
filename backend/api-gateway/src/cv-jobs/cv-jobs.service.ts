import { Injectable, NotFoundException } from '@nestjs/common';
import { Prisma } from '@prisma/client';
import { PrismaService } from '../prisma/prisma.service';
import { RedisService } from '../redis/redis.service';
import { CV_JOB_STAGES } from './cv-jobs.stage';
import { toCvJobDto } from './cv-jobs.mapper';

const QUEUE_KEY = 'cv_jobs:queue:v1';
const INPUT_TTL_SECONDS = 24 * 3600;

@Injectable()
export class CvJobsService {
  constructor(
    private readonly prisma: PrismaService,
    private readonly redis: RedisService,
  ) {}

  async createTextJob(
    userId: string,
    payload: { cvText: string; fileName?: string; topK?: number; location?: string; contractType?: string },
  ) {
    const job = await this.prisma.cvAnalysisJob.create({
      data: { userId, inputType: 'TEXT', fileName: payload.fileName || null, inputPayload: {} },
    });
    await this.storeInput(job.id, {
      cvText: payload.cvText,
      fileName: payload.fileName || 'cv.txt',
      mimeType: 'text/plain',
      topK: payload.topK ?? 5,
      location: payload.location,
      contractType: payload.contractType,
    });
    await this.redis.lPush(QUEUE_KEY, job.id);
    return toCvJobDto(job);
  }

  async createUploadJob(
    userId: string,
    payload: {
      fileName: string;
      mimeType: string;
      bytes: Buffer;
      topK?: number;
      location?: string;
      contractType?: string;
    },
  ) {
    const job = await this.prisma.cvAnalysisJob.create({
      data: {
        userId,
        inputType: 'UPLOAD',
        fileName: payload.fileName,
        inputPayload: { mimeType: payload.mimeType, size: payload.bytes.length },
      },
    });
    await this.storeInput(job.id, {
      ...payload,
      topK: payload.topK ?? 5,
      location: payload.location,
      contractType: payload.contractType,
      bytesBase64: payload.bytes.toString('base64'),
    });
    await this.redis.lPush(QUEUE_KEY, job.id);
    return toCvJobDto(job);
  }

  async getJob(userId: string, jobId: string) {
    const job = await this.prisma.cvAnalysisJob.findFirst({ where: { id: jobId, userId } });
    if (!job) throw new NotFoundException('Job introuvable');
    return toCvJobDto(job);
  }

  async listJobs(userId: string, status?: string, limit = 20) {
    const normalized = String(status || '').trim().toUpperCase();
    const statusFilter =
      normalized === 'ACTIVE'
        ? { in: ['QUEUED', 'IN_PROGRESS'] }
        : normalized === 'COMPLETED'
          ? 'COMPLETED'
          : normalized === 'FAILED'
            ? 'FAILED'
            : normalized || undefined;
    const jobs = await this.prisma.cvAnalysisJob.findMany({
      where: { userId, ...(statusFilter ? { status: statusFilter as any } : {}) },
      orderBy: { updatedAt: 'desc' },
      take: Math.min(Math.max(limit, 1), 100),
    });
    return jobs.map(toCvJobDto);
  }

  async popQueuedJobId() {
    return this.redis.rPop(QUEUE_KEY);
  }

  async updateJob(jobId: string, patch: Prisma.CvAnalysisJobUpdateInput) {
    return this.prisma.cvAnalysisJob.update({ where: { id: jobId }, data: patch });
  }

  async getJobById(jobId: string) {
    return this.prisma.cvAnalysisJob.findUnique({ where: { id: jobId } });
  }

  async loadInput(jobId: string) {
    const raw = await this.redis.get(this.inputKey(jobId));
    return raw ? (JSON.parse(raw) as Record<string, unknown>) : null;
  }

  async failJob(jobId: string, message: string) {
    await this.updateJob(jobId, {
      status: 'FAILED',
      stage: CV_JOB_STAGES.FAILED,
      progress: 100,
      error: message.slice(0, 2000),
      completedAt: new Date(),
    });
  }

  private async storeInput(jobId: string, payload: Record<string, unknown>) {
    await this.redis.setEx(this.inputKey(jobId), INPUT_TTL_SECONDS, JSON.stringify(payload));
  }

  private inputKey(jobId: string) {
    return `cv_jobs:input:${jobId}`;
  }
}
