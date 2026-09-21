import { Injectable, Logger } from '@nestjs/common';
import { RedisService } from '../redis/redis.service';

export type MaintenanceDomain =
  | 'global'
  | 'search'
  | 'graphql'
  | 'auth'
  | 'reports'
  | 'cv_jobs';

const DOMAINS: MaintenanceDomain[] = [
  'global',
  'search',
  'graphql',
  'auth',
  'reports',
  'cv_jobs',
];

export interface DomainState {
  active: boolean;
  message: string;
  retryAfterSeconds: number;
  updatedAt: string;
}

@Injectable()
export class MaintenanceService {
  private readonly logger = new Logger(MaintenanceService.name);
  private readonly key = 'runtime:maintenance:v1';
  private fallback: Record<MaintenanceDomain, DomainState> = this.defaultState();

  constructor(private readonly redis: RedisService) {}

  async snapshot() {
    const state = (await this.readState()) ?? this.fallback;
    return {
      domains: DOMAINS,
      state,
      activeDomains: DOMAINS.filter((d) => state[d].active),
      updatedAt: new Date().toISOString(),
    };
  }

  async setDomain(input: {
    domain: MaintenanceDomain;
    active: boolean;
    message?: string;
    retryAfterSeconds?: number;
  }) {
    const state = (await this.readState()) ?? this.fallback;
    const retryAfterSeconds = Math.max(
      30,
      Math.min(3600, Number(input.retryAfterSeconds ?? 180)),
    );
    state[input.domain] = {
      active: Boolean(input.active),
      message:
        String(input.message || '').trim() ||
        'Maintenance en cours. Réessaie dans quelques instants.',
      retryAfterSeconds,
      updatedAt: new Date().toISOString(),
    };
    this.fallback = state;
    await this.writeState(state);
    return { domain: input.domain, ...state[input.domain] };
  }

  async evaluate(path: string) {
    const state = (await this.readState()) ?? this.fallback;
    const domain = this.routeDomain(path);
    const globalState = state.global;
    const domainState = state[domain];
    const active = globalState.active || domainState.active;
    const winner = globalState.active ? globalState : domainState;
    return {
      blocked: active,
      domain,
      code: 'SERVICE_MAINTENANCE',
      retryAfterSeconds: winner.retryAfterSeconds,
      message: winner.message,
      updatedAt: winner.updatedAt,
    };
  }

  private routeDomain(path: string): MaintenanceDomain {
    if (path.startsWith('/search')) return 'search';
    if (path.startsWith('/graphql')) return 'graphql';
    if (path.startsWith('/auth')) return 'auth';
    if (path.startsWith('/reports')) return 'reports';
    if (path.startsWith('/cv-jobs')) return 'cv_jobs';
    return 'global';
  }

  private defaultState(): Record<MaintenanceDomain, DomainState> {
    const now = new Date().toISOString();
    const base: DomainState = {
      active: false,
      message: 'Maintenance en cours. Réessaie dans quelques instants.',
      retryAfterSeconds: 180,
      updatedAt: now,
    };
    return Object.fromEntries(DOMAINS.map((d) => [d, { ...base }])) as Record<
      MaintenanceDomain,
      DomainState
    >;
  }

  private async readState() {
    try {
      const raw = await this.redis.get(this.key);
      if (!raw) return null;
      const parsed = JSON.parse(raw) as Record<MaintenanceDomain, DomainState>;
      const base = this.defaultState();
      for (const domain of DOMAINS) {
        if (parsed?.[domain]) base[domain] = parsed[domain];
      }
      return base;
    } catch (error) {
      this.logger.warn(`Maintenance state read failed: ${String(error)}`);
      return null;
    }
  }

  private async writeState(payload: Record<MaintenanceDomain, DomainState>) {
    try {
      await this.redis.set(this.key, JSON.stringify(payload));
    } catch (error) {
      this.logger.warn(`Maintenance state write failed: ${String(error)}`);
    }
  }
}
