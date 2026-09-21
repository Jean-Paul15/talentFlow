// Search Module

import { Module } from '@nestjs/common';
import { SearchService } from './search.service';
import { SearchController } from './search.controller';
import { RedisModule } from '../redis/redis.module';
import { RuntimeModule } from '../runtime/runtime.module';

@Module({
  imports: [RedisModule, RuntimeModule],
  providers: [SearchService],
  controllers: [SearchController],
  exports: [SearchService],
})
export class SearchModule {}
