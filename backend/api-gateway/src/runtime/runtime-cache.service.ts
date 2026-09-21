import { Injectable, Logger } from '@nestjs/common';
import { RedisService } from '../redis/redis.service';

export type CacheDomain = 'jobs' | 'profile' | 'recommendation' | 'history' | 'favorites';

const DOMAINS: CacheDomain[] = [
  'jobs',
  'profile',
  'recommendation',
  'history',
  'favorites',
];

@Injectable()
export class RuntimeCacheService {
  private readonly logger = new Logger(RuntimeCacheService.name);
  private readonly key = 'runtime:cache:versions:v1';
  private fallbackVersions: Record<CacheDomain, number> = this.createDefaultVersions();
  private fallbackSyncedAt: string = new Date().toISOString();
  private lastIndexRunAt: string | null = null;

  constructor(private readonly redis: RedisService) {}

  async getVersions() {
    const fromStore = await this.readFromStore();
    const versions = fromStore?.versions ?? this.fallbackVersions;
    const syncedAt = fromStore?.syncedAt ?? this.fallbackSyncedAt;
    return {
      versions,
      syncedAt,
      domains: DOMAINS,
      uptimeSeconds: Math.round(process.uptime()),
      lastIndexRunAt: this.lastIndexRunAt,
    };
  }

  async bump(domain: CacheDomain) {
    const current = await this.readFromStore();
    const baseline = current?.versions ?? this.fallbackVersions;
    const next = {
      ...baseline,
      [domain]: Date.now(),
    };
    const syncedAt = new Date().toISOString();

    this.fallbackVersions = next;
    this.fallbackSyncedAt = syncedAt;
    if (domain === 'jobs') {
      this.lastIndexRunAt = syncedAt;
    }
    await this.writeToStore({ versions: next, syncedAt });
    return { domain, version: next[domain], syncedAt };
  }

  async bumpMany(domains: string[]) {
    const unique = Array.from(new Set(domains)).filter((d): d is CacheDomain =>
      DOMAINS.includes(d as CacheDomain),
    );
    const result: Record<string, number> = {};
    for (const domain of unique) {
      const bumped = await this.bump(domain);
      result[domain] = bumped.version;
    }
    return result;
  }

  private createDefaultVersions(): Record<CacheDomain, number> {
    const now = Date.now();
    return {
      jobs: now,
      profile: now,
      recommendation: now,
      history: now,
      favorites: now,
    };
  }

  private async readFromStore(): Promise<{
    versions: Record<CacheDomain, number>;
    syncedAt: string;
  } | null> {
    try {
      const raw = await this.redis.get(this.key);
      if (!raw) return null;
      const parsed = JSON.parse(raw) as {
        versions?: Record<string, number>;
        syncedAt?: string;
      };
      const versions = this.createDefaultVersions();
      for (const domain of DOMAINS) {
        const value = Number(parsed.versions?.[domain]);
        if (Number.isFinite(value) && value > 0) {
          versions[domain] = value;
        }
      }
      return {
        versions,
        syncedAt: String(parsed.syncedAt || new Date().toISOString()),
      };
    } catch (error) {
      this.logger.warn(`Impossible de lire les versions de cache: ${String(error)}`);
      return null;
    }
  }

  private async writeToStore(payload: {
    versions: Record<CacheDomain, number>;
    syncedAt: string;
  }) {
    try {
      await this.redis.set(this.key, JSON.stringify(payload));
    } catch (error) {
      this.logger.warn(`Impossible d'ecrire les versions de cache: ${String(error)}`);
    }
  }
}


