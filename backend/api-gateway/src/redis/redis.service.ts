// Redis Service - Cache

import { Injectable } from '@nestjs/common';
import { createClient } from 'redis';

@Injectable()
export class RedisService {
  private client;

  async onModuleInit() {
    this.client = createClient({
      url: process.env.REDIS_URL || 'redis://localhost:6379',
    });
    await this.client.connect();
  }

  async onModuleDestroy() {
    await this.client.quit();
  }

  async get(key: string) {
    return this.client.get(key);
  }

  async set(key: string, value: string, ttl?: number) {
    if (ttl) {
      return this.client.setEx(key, ttl, value);
    }
    return this.client.set(key, value);
  }

  async del(key: string) {
    return this.client.del(key);
  }

  async setEx(key: string, ttl: number, value: string) {
    return this.client.setEx(key, ttl, value);
  }

  async lPush(key: string, value: string) {
    return this.client.lPush(key, value);
  }

  async rPop(key: string) {
    return this.client.rPop(key);
  }

  async invalidatePattern(pattern: string) {
    const keys = await this.client.keys(pattern);
    if (keys.length > 0) {
      return this.client.del(keys);
    }
  }

  async incr(key: string, by = 1) {
    return this.client.incrBy(key, by);
  }

  async hIncrBy(key: string, field: string, by = 1) {
    return this.client.hIncrBy(key, field, by);
  }

  async hSet(key: string, field: string, value: string) {
    return this.client.hSet(key, field, value);
  }

  async hGetAll(key: string) {
    return this.client.hGetAll(key);
  }

  async expire(key: string, ttlSeconds: number) {
    return this.client.expire(key, ttlSeconds);
  }
}
