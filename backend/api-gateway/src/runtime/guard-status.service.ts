import { Injectable, Logger } from '@nestjs/common';
import { RedisService } from '../redis/redis.service';

interface GuardCounters {
  [key: string]: number;
}

@Injectable()
export class GuardStatusService {
  private readonly logger = new Logger(GuardStatusService.name);
  private readonly statusKey = 'runtime:guard:status:v1';
  private readonly countersKey = 'runtime:guard:counters:v1';

  constructor(private readonly redis: RedisService) {}

  async snapshot() {
    try {
      const [rawStatus, rawCounters] = await Promise.all([
        this.redis.get(this.statusKey),
        this.redis.hGetAll(this.countersKey),
      ]);
      const status = rawStatus ? JSON.parse(rawStatus) : {};
      const counters = Object.fromEntries(
        Object.entries(rawCounters || {}).map(([k, v]) => [k, Number(v || 0)]),
      ) as GuardCounters;
      return {
        ...status,
        counters,
        generatedAt: new Date().toISOString(),
      };
    } catch (error) {
      this.logger.warn(`Guard status snapshot failed: ${String(error)}`);
      return { counters: {}, generatedAt: new Date().toISOString() };
    }
  }

  async ingest(report: Record<string, unknown>) {
    const payload = {
      ...report,
      updatedAt: new Date().toISOString(),
    };
    try {
      await this.redis.set(this.statusKey, JSON.stringify(payload));
      const counters = (report.counters || {}) as Record<string, unknown>;
      await Promise.all(
        Object.entries(counters).map(([key, value]) =>
          this.redis.hSet(this.countersKey, key, String(Number(value || 0))),
        ),
      );
    } catch (error) {
      this.logger.warn(`Guard status ingest failed: ${String(error)}`);
    }
    return this.snapshot();
  }

  async metricsText() {
    const counters = await this.redis.hGetAll(this.countersKey);
    const lines = ['# HELP talentflow_guard_runtime Runtime counters from guard agents'];
    lines.push('# TYPE talentflow_guard_runtime gauge');
    for (const [key, value] of Object.entries(counters || {})) {
      const safe = key.replace(/[^a-zA-Z0-9_]/g, '_');
      lines.push(`talentflow_guard_runtime{name="${safe}"} ${Number(value || 0)}`);
    }
    return `${lines.join('\n')}\n`;
  }
}
