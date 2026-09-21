import {
  Body,
  Controller,
  Get,
  Header,
  Headers,
  HttpCode,
  HttpStatus,
  Post,
  UnauthorizedException,
} from '@nestjs/common';
import { CvQualityMetricsService } from './cv-quality-metrics.service';
import { GuardStatusService } from './guard-status.service';
import { MaintenanceDomain, MaintenanceService } from './maintenance.service';
import { RuntimeCacheService } from './runtime-cache.service';

@Controller('runtime')
export class RuntimeController {
  constructor(
    private readonly runtimeCache: RuntimeCacheService,
    private readonly cvQuality: CvQualityMetricsService,
    private readonly maintenance: MaintenanceService,
    private readonly guardStatus: GuardStatusService,
  ) {}

  @Get('cache-version')
  async cacheVersion() {
    return this.runtimeCache.getVersions();
  }

  @Get('cv-quality')
  async cvQualitySnapshot() {
    return this.cvQuality.snapshot();
  }

  @Get('maintenance/status')
  async maintenanceStatus() {
    return this.maintenance.snapshot();
  }

  @Post('maintenance/toggle')
  @HttpCode(HttpStatus.OK)
  async toggleMaintenance(
    @Headers('x-internal-token') internalToken?: string,
    @Body()
    body?: {
      domain?: MaintenanceDomain;
      active?: boolean;
      retryAfterSeconds?: number;
      message?: string;
    },
  ) {
    this.assertInternalToken(internalToken);
    const domain = (body?.domain || 'global') as MaintenanceDomain;
    return this.maintenance.setDomain({
      domain,
      active: Boolean(body?.active),
      retryAfterSeconds: body?.retryAfterSeconds,
      message: body?.message,
    });
  }

  @Get('guard/status')
  async guardSnapshot() {
    return this.guardStatus.snapshot();
  }

  @Post('guard/status')
  @HttpCode(HttpStatus.OK)
  async ingestGuardStatus(
    @Headers('x-internal-token') internalToken?: string,
    @Body() body?: Record<string, unknown>,
  ) {
    this.assertInternalToken(internalToken);
    return this.guardStatus.ingest(body ?? {});
  }

  @Get('guard/metrics')
  @Header('Content-Type', 'text/plain; version=0.0.4')
  async guardMetrics() {
    return this.guardStatus.metricsText();
  }

  @Get('ops-status')
  async opsStatus() {
    const [cacheVersions, cvQuality, sourcing, search, guard, maintenance] = await Promise.all([
      this.runtimeCache.getVersions(),
      this.cvQuality.snapshot(),
      this.fetchJson(
        `${String(process.env.JOB_SOURCING_URL || 'http://job-sourcing:8000').replace(/\/+$/, '')}/api/scrape/bandit`,
      ),
      this.fetchJson(
        `${String(process.env.SEARCH_ENGINE_URL || 'http://search-engine:8002').replace(/\/+$/, '')}/health`,
      ),
      this.guardStatus.snapshot(),
      this.maintenance.snapshot(),
    ]);
    return {
      generatedAt: new Date().toISOString(),
      uptimeSeconds: Math.floor(process.uptime()),
      cacheVersions,
      cvQuality,
      sourcingBandit: sourcing,
      searchHealth: search,
      guard,
      maintenance,
    };
  }

  @Post('cache-version/bump')
  @HttpCode(HttpStatus.OK)
  async bumpCacheVersion(
    @Headers('x-internal-token') internalToken?: string,
    @Body() body?: { domains?: string[] },
  ) {
    this.assertInternalToken(internalToken);
    const domains = (Array.isArray(body?.domains) ? body!.domains : ['jobs'])
      .map((d) => String(d || '').trim().toLowerCase())
      .filter(Boolean);
    return { ok: true, bumped: await this.runtimeCache.bumpMany(domains) };
  }

  private assertInternalToken(received?: string) {
    const expected = String(process.env.RUNTIME_INTERNAL_TOKEN || '').trim();
    if (expected && String(received || '').trim() !== expected) {
      throw new UnauthorizedException('Internal token invalide');
    }
  }

  private async fetchJson(url: string): Promise<Record<string, unknown>> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 5000);
    try {
      const response = await fetch(url, { signal: controller.signal });
      if (!response.ok) return { ok: false, status: response.status, message: `HTTP ${response.status}` };
      return { ok: true, ...((await response.json()) as Record<string, unknown>) };
    } catch (error) {
      return { ok: false, message: String(error) };
    } finally {
      clearTimeout(timer);
    }
  }
}

