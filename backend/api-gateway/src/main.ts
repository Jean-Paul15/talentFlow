// Main - bootstrap NestJS

import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';
import { ValidationPipe } from '@nestjs/common';
import { HttpExceptionFilter } from './common/filters/http-exception.filter';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  // Validation
  app.useGlobalPipes(new ValidationPipe({ whitelist: true }));
  
  // Exception filter
  app.useGlobalFilters(new HttpExceptionFilter());
  
  // CORS - Mobile friendly
  const corsOrigin =
    process.env.CORS_ORIGIN ||
    process.env.ALLOWED_ORIGINS ||
    (process.env.NODE_ENV === 'production' ? '' : '*');
  
  app.enableCors({
    origin: corsOrigin === '*' ? true : corsOrigin.split(','),
    credentials: corsOrigin !== '*',
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowedHeaders: '*',
  });

  const port = Number(process.env.PORT || 3000);
  const host = process.env.HOST || '0.0.0.0';
  const graphqlPath = process.env.GRAPHQL_PATH || '/graphql';

  await app.listen(port, host);

  console.log(
    `API Gateway lancée sur http://${host}:${port}${graphqlPath}`,
  );
}

bootstrap();
