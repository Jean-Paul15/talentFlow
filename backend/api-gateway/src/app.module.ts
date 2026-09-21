// API Gateway - Configuration principale

import { MiddlewareConsumer, Module, NestModule, RequestMethod } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { TypeOrmModule } from '@nestjs/typeorm';
import { JwtModule } from '@nestjs/jwt';
import { PassportModule } from '@nestjs/passport';
import { ThrottlerModule } from '@nestjs/throttler';

import { PrismaModule } from './prisma/prisma.module';
import { AuthModule } from './auth/auth.module';
import { UsersModule } from './users/users.module';
import { FavoritesModule } from './favorites/favorites.module';
import { HistoryModule } from './history/history.module';
import { SearchModule } from './search/search.module';
import { GraphApiModule } from './graphql/graphql.module';
import { HealthController } from './health.controller';
import { ReportsModule } from './reports/reports.module';
import { CvJobsModule } from './cv-jobs/cv-jobs.module';
import { RuntimeModule } from './runtime/runtime.module';
import { MaintenanceMiddleware } from './runtime/maintenance.middleware';

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      envFilePath: '.env',
    }),
    ThrottlerModule.forRoot({
      ttl: 60000,
      limit: 100,
    }),
    PrismaModule,
    AuthModule,
    UsersModule,
    FavoritesModule,
    HistoryModule,
    SearchModule,
    GraphApiModule,
    ReportsModule,
    CvJobsModule,
    RuntimeModule,
  ],
  controllers: [HealthController],
  providers: [MaintenanceMiddleware],
})
export class AppModule implements NestModule {
  configure(consumer: MiddlewareConsumer) {
    consumer
      .apply(MaintenanceMiddleware)
      .exclude(
        { path: 'health', method: RequestMethod.ALL },
        { path: 'health/(.*)', method: RequestMethod.ALL },
        { path: 'runtime', method: RequestMethod.ALL },
        { path: 'runtime/(.*)', method: RequestMethod.ALL },
        { path: 'orchestration', method: RequestMethod.ALL },
        { path: 'orchestration/(.*)', method: RequestMethod.ALL },
      )
      .forRoutes({ path: '*', method: RequestMethod.ALL });
  }
}

