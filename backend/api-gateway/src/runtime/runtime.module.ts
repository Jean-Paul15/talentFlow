import { Module } from '@nestjs/common';
import { RedisModule } from '../redis/redis.module';
import { CvQualityMetricsService } from './cv-quality-metrics.service';
import { GuardStatusService } from './guard-status.service';
import { MaintenanceService } from './maintenance.service';
import { RuntimeController } from './runtime.controller';
import { RuntimeCacheService } from './runtime-cache.service';

@Module({
  imports: [RedisModule],
  controllers: [RuntimeController],
  providers: [
    RuntimeCacheService,
    CvQualityMetricsService,
    MaintenanceService,
    GuardStatusService,
  ],
  exports: [
    RuntimeCacheService,
    CvQualityMetricsService,
    MaintenanceService,
    GuardStatusService,
  ],
})
export class RuntimeModule {}

