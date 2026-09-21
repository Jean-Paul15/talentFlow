import { Module } from '@nestjs/common';
import { PrismaModule } from '../prisma/prisma.module';
import { RedisModule } from '../redis/redis.module';
import { SearchModule } from '../search/search.module';
import { HistoryModule } from '../history/history.module';
import { CvJobsService } from './cv-jobs.service';
import { CvJobsController } from './cv-jobs.controller';
import { CvJobsWorker } from './cv-jobs.worker';
import { CvJobsExecutor } from './cv-jobs.executor';

@Module({
  imports: [PrismaModule, RedisModule, SearchModule, HistoryModule],
  providers: [CvJobsService, CvJobsWorker, CvJobsExecutor],
  controllers: [CvJobsController],
  exports: [CvJobsService],
})
export class CvJobsModule {}
