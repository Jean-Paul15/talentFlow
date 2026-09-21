import { Args, Context, Int, Mutation, Query, Resolver } from '@nestjs/graphql';
import { GraphApiService } from './graphql-api.service';
import {
  AuthPayloadGql,
  CvRecommendTextResponseGql,
  CvJobStatusGql,
  FavoriteJobGql,
  LoginInput,
  RecommendationHistoryEntryGql,
  RecommendCvTextInput,
  RegisterInput,
  SaveFavoriteInput,
  SaveRecommendationHistoryInput,
  SearchJobsInput,
  SearchJobsResponseGql,
  UpdateProfileInput,
  UserProfileGql,
} from './graphql.types';

@Resolver()
export class GraphApiResolver {
  constructor(private readonly graphApi: GraphApiService) {}

  @Mutation(() => AuthPayloadGql)
  async register(@Args('input', { type: () => RegisterInput }) input: any) {
    return this.graphApi.register(input);
  }

  @Mutation(() => AuthPayloadGql)
  async login(@Args('input', { type: () => LoginInput }) input: any) {
    return this.graphApi.login(input);
  }

  @Query(() => UserProfileGql)
  async me(@Context() context: any) {
    return this.graphApi.me(context);
  }

  @Mutation(() => UserProfileGql)
  async updateMyProfile(
    @Context() context: any,
    @Args('input', { type: () => UpdateProfileInput }) input: any,
  ) {
    return this.graphApi.updateMe(context, input);
  }

  @Query(() => SearchJobsResponseGql)
  async searchJobs(@Args('input', { type: () => SearchJobsInput }) input: any) {
    return this.graphApi.searchJobs(input);
  }

  @Mutation(() => CvRecommendTextResponseGql)
  async recommendFromCvText(
    @Args('input', { type: () => RecommendCvTextInput }) input: any,
  ) {
    return this.graphApi.recommendFromCvText(input);
  }

  @Mutation(() => RecommendationHistoryEntryGql)
  async saveRecommendationHistory(
    @Context() context: any,
    @Args('input', { type: () => SaveRecommendationHistoryInput }) input: any,
  ) {
    return this.graphApi.saveRecommendationHistory(context, input);
  }

  @Query(() => [RecommendationHistoryEntryGql])
  async myRecommendationHistory(
    @Context() context: any,
    @Args('limit', { type: () => Int, nullable: true }) limit?: number,
    @Args('offset', { type: () => Int, nullable: true }) offset?: number,
  ) {
    return this.graphApi.myRecommendationHistory(context, limit, offset);
  }

  @Query(() => RecommendationHistoryEntryGql, { nullable: true })
  async recommendationHistoryEntry(
    @Context() context: any,
    @Args('id') id: string,
  ) {
    return this.graphApi.recommendationHistoryEntry(context, id);
  }

  @Mutation(() => Boolean)
  async deleteRecommendationHistory(
    @Context() context: any,
    @Args('id') id: string,
  ) {
    return this.graphApi.deleteRecommendationHistory(context, id);
  }

  @Query(() => [FavoriteJobGql])
  async myFavorites(
    @Context() context: any,
    @Args('limit', { type: () => Int, nullable: true }) limit?: number,
    @Args('offset', { type: () => Int, nullable: true }) offset?: number,
  ) {
    return this.graphApi.myFavorites(context, limit, offset);
  }

  @Query(() => Boolean)
  async isFavorite(
    @Context() context: any,
    @Args('jobId') jobId: string,
  ) {
    return this.graphApi.isFavorite(context, jobId);
  }

  @Mutation(() => FavoriteJobGql)
  async saveFavorite(
    @Context() context: any,
    @Args('input', { type: () => SaveFavoriteInput }) input: any,
  ) {
    return this.graphApi.saveFavorite(context, input);
  }

  @Mutation(() => Boolean)
  async removeFavorite(
    @Context() context: any,
    @Args('jobId') jobId: string,
  ) {
    return this.graphApi.removeFavorite(context, jobId);
  }

  @Query(() => [CvJobStatusGql])
  async myCvJobs(
    @Context() context: any,
    @Args('limit', { type: () => Int, nullable: true }) limit?: number,
    @Args('status', { nullable: true }) status?: string,
  ) {
    return this.graphApi.myCvJobs(context, limit, status);
  }

  @Query(() => CvJobStatusGql, { nullable: true })
  async cvJob(@Context() context: any, @Args('id') id: string) {
    return this.graphApi.cvJob(context, id);
  }
}
