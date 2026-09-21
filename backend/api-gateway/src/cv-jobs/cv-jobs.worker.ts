import { Injectable, Logger, OnModuleDestroy, OnModuleInit } from '@nestjs/common';
import { CvJobsService } from './cv-jobs.service';
import { CvJobsExecutor } from './cv-jobs.executor';

@Injectable()
export class CvJobsWorker implements OnModuleInit, OnModuleDestroy {
  private readonly logger = new Logger(CvJobsWorker.name);
  private running = false;
  private timer?: NodeJS.Timeout;

  constructor(
    private readonly jobs: CvJobsService,
    private readonly executor: CvJobsExecutor,
  ) {}

  onModuleInit() {
    this.running = true;
    this.loop();
  }

  onModuleDestroy() {
    this.running = false;
    if (this.timer) clearTimeout(this.timer);
  }

  private loop() {
    this.timer = setTimeout(async () => {
      if (!this.running) return;
      try {
        const jobId = await this.jobs.popQueuedJobId();
        if (jobId) await this.executor.run(jobId);
      } catch (err) {
        this.logger.error(`Worker cv-jobs: ${err}`);
      } finally {
        this.loop();
      }
    }, 500);
  }
}
