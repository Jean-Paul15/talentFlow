import { Module } from '@nestjs/common';
import { HistoryModule } from '../history/history.module';
import { ReportsController } from './reports.controller';
import { ReportsService } from './reports.service';

@Module({
  imports: [HistoryModule],
  controllers: [ReportsController],
  providers: [ReportsService],
})
export class ReportsModule {}
