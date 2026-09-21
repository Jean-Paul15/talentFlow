import { Injectable, NestMiddleware } from '@nestjs/common';
import { NextFunction, Request, Response } from 'express';
import { MaintenanceService } from './maintenance.service';

@Injectable()
export class MaintenanceMiddleware implements NestMiddleware {
  constructor(private readonly maintenance: MaintenanceService) {}

  async use(req: Request, res: Response, next: NextFunction) {
    const path = req.path || '/';
    if (
      path.startsWith('/health') ||
      path.startsWith('/runtime') ||
      path.startsWith('/orchestration')
    ) {
      return next();
    }

    const verdict = await this.maintenance.evaluate(path);
    if (!verdict.blocked) return next();

    res.setHeader('Retry-After', String(verdict.retryAfterSeconds));
    res.status(503).json({
      statusCode: 503,
      code: verdict.code,
      message: verdict.message,
      domain: verdict.domain,
      retryAfterSeconds: verdict.retryAfterSeconds,
      timestamp: new Date().toISOString(),
      path,
    });
  }
}

