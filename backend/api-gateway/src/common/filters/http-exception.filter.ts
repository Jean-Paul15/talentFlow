// Exception Filter

import {
  ExceptionFilter,
  Catch,
  ArgumentsHost,
  HttpException,
  HttpStatus,
  Logger,
} from '@nestjs/common';
import { randomUUID } from 'crypto';

@Catch()
export class HttpExceptionFilter implements ExceptionFilter {
  private logger = new Logger('HttpExceptionFilter');

  catch(exception: unknown, host: ArgumentsHost) {
    const hostType = host.getType();
    if (hostType !== 'http') {
      if (exception instanceof Error) {
        this.logger.error(exception.message, exception.stack);
      } else {
        this.logger.error(`Unhandled non-http exception: ${String(exception)}`);
      }
      throw exception;
    }

    const ctx = host.switchToHttp();
    const response = ctx.getResponse();
    const request = ctx.getRequest();

    let status = HttpStatus.INTERNAL_SERVER_ERROR;
    let message = 'Erreur serveur interne';
    let code = 'INTERNAL_ERROR';

    if (exception instanceof HttpException) {
      status = exception.getStatus();
      const raw = exception.getResponse() as
        | string
        | { message?: string | string[]; code?: string; error?: string };
      if (typeof raw === 'string') {
        message = raw;
      } else {
        const rawMessage = raw?.message;
        if (Array.isArray(rawMessage)) {
          message = rawMessage.filter(Boolean).join(', ');
        } else if (typeof rawMessage === 'string' && rawMessage.trim().length > 0) {
          message = rawMessage;
        }
        if (typeof raw?.code === 'string' && raw.code.trim().length > 0) {
          code = raw.code.trim().toUpperCase();
        }
      }
      if (!code || code === 'INTERNAL_ERROR') {
        code = this.defaultCodeForStatus(status);
      }
    }

    const method = request?.method ?? 'UNKNOWN_METHOD';
    const url = request?.url ?? 'UNKNOWN_URL';
    const traceId = randomUUID();
    this.logger.error(`[${traceId}] ${method} ${url} - ${status} - ${message}`);

    response.status(status).json({
      statusCode: status,
      code,
      message,
      traceId,
      timestamp: new Date().toISOString(),
      path: url,
    });
  }

  private defaultCodeForStatus(status: number): string {
    if (status >= 500) return 'INTERNAL_ERROR';
    if (status === HttpStatus.BAD_REQUEST) return 'BAD_REQUEST';
    if (status === HttpStatus.UNAUTHORIZED) return 'UNAUTHORIZED';
    if (status === HttpStatus.FORBIDDEN) return 'FORBIDDEN';
    if (status === HttpStatus.NOT_FOUND) return 'NOT_FOUND';
    if (status === HttpStatus.CONFLICT) return 'CONFLICT';
    if (status === HttpStatus.UNSUPPORTED_MEDIA_TYPE) {
      return 'UNSUPPORTED_MEDIA_TYPE';
    }
    return 'REQUEST_ERROR';
  }
}


