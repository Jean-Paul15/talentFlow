import { getJwtSecret } from '../auth/jwt-secret';
import { Module } from '@nestjs/common';
import { JwtModule } from '@nestjs/jwt';
import { GraphQLModule } from '@nestjs/graphql';
import { ApolloDriver, ApolloDriverConfig } from '@nestjs/apollo';
import { join } from 'path';
import { AuthModule } from '../auth/auth.module';
import { FavoritesModule } from '../favorites/favorites.module';
import { HistoryModule } from '../history/history.module';
import { UsersModule } from '../users/users.module';
import { SearchModule } from '../search/search.module';
import { CvJobsModule } from '../cv-jobs/cv-jobs.module';
import { GraphApiResolver } from './graphql.resolver';
import { GraphApiService } from './graphql-api.service';

@Module({
  imports: [
    GraphQLModule.forRoot<ApolloDriverConfig>({
      driver: ApolloDriver,
      path: process.env.GRAPHQL_PATH || '/graphql',
      autoSchemaFile: join(process.cwd(), 'schema.gql'),
      sortSchema: true,
      playground: true,
      introspection: true,
      context: ({ req }) => ({ req }),
    }),
    JwtModule.register({
      secret: getJwtSecret(),
      signOptions: { expiresIn: (process.env.JWT_EXPIRATION || '7d') as any },
    }),
    AuthModule,
    FavoritesModule,
    HistoryModule,
    UsersModule,
    SearchModule,
    CvJobsModule,
  ],
  providers: [GraphApiResolver, GraphApiService],
})
export class GraphApiModule {}
