import { Injectable } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { AuthService } from '../auth/auth.service';
import { FavoritesService } from '../favorites/favorites.service';
import { HistoryService } from '../history/history.service';
import { UsersService } from '../users/users.service';
import { SearchService } from '../search/search.service';
import { CvJobsService } from '../cv-jobs/cv-jobs.service';
import { extractUserIdFromContext } from './graphql-auth';
import { mapSearchResponse, mapRecommendationResponse } from './graphql.recommendation-mappers';
import { mapAtsLite, mapAssistantStructured } from './graphql.shared-mappers';
import { mapFavoriteEntry, mapHistoryEntry } from './graphql.history-favorite-mappers';

@Injectable()
export class GraphApiService {
  constructor(
    private readonly authService: AuthService,
    private readonly usersService: UsersService,
    private readonly searchService: SearchService,
    private readonly historyService: HistoryService,
    private readonly favoritesService: FavoritesService,
    private readonly cvJobsService: CvJobsService,
    private readonly jwtService: JwtService,
  ) {}

  async register(input: {
    email: string;
    password: string;
    name: string;
    acceptTerms: boolean;
  }) {
    const data = await this.authService.register(
      input.email,
      input.password,
      input.name,
      Boolean(input.acceptTerms),
    );
    return {
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
      user: data.user,
    };
  }

  async login(input: { email: string; password: string }) {
    const data = await this.authService.login(input.email, input.password);
    return {
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
      user: data.user,
    };
  }

  async me(context: any) {
    return this.usersService.findById(this.userId(context));
  }

  async updateMe(context: any, data: any) {
    return this.usersService.updateProfile(this.userId(context), data);
  }

  async searchJobs(input: any) {
    const query = String(input.query || '').trim();
    const filters: any = {
      limit: input.limit,
      location: input.location,
      contract_type: input.contractType,
      country: input.country,
      source_name: input.sourceName,
      rerank: input.rerank,
      candidate_pool_size: input.candidatePoolSize,
    };
    Object.keys(filters).forEach((k) => filters[k] === undefined && delete filters[k]);
    return mapSearchResponse(await this.searchService.searchJobs(query, filters), query);
  }

  async recommendFromCvText(input: any) {
    const data = await this.searchService.recommendFromCvText({
      cv_text: input.cvText,
      file_name: input.fileName,
      top_k: input.topK,
      location: input.location,
      contract_type: input.contractType,
      use_llm: input.useLlm,
      llm_model: input.llmModel,
      rerank: input.rerank,
      candidate_pool_size: input.candidatePoolSize,
    });
    return mapRecommendationResponse(data);
  }

  async saveRecommendationHistory(context: any, input: any) {
    const entry = await this.historyService.saveAnalysis(this.userId(context), {
      cvTextPreview: input.cvTextPreview,
      fileName: input.fileName,
      queryUsed: input.queryUsed,
      locationFilter: input.locationFilter,
      contractTypeFilter: input.contractTypeFilter,
      assistantMessage: input.assistantMessage,
      llmUsed: input.llmUsed,
      llmProvider: input.llmProvider,
      llmModel: input.llmModel,
      llmError: input.llmError,
      llmStatus: input.llmStatus,
      totalResults: input.totalResults,
      assistantStructured: input.assistantStructured ?? null,
      cvAnalysis: input.cvAnalysis ? { ...input.cvAnalysis, atsLite: input.atsLite ?? null } : { atsLite: input.atsLite ?? null },
      jobsSnapshot: Array.isArray(input.jobs) ? input.jobs : [],
    });
    return mapHistoryEntry(entry);
  }

  async myRecommendationHistory(context: any, limit = 20, offset = 0) {
    const entries = await this.historyService.getHistory(this.userId(context), limit, offset);
    return entries.map((entry: any) => mapHistoryEntry(entry));
  }

  async recommendationHistoryEntry(context: any, id: string) {
    return mapHistoryEntry(await this.historyService.getHistoryEntry(this.userId(context), id));
  }

  async deleteRecommendationHistory(context: any, id: string) {
    return this.historyService.deleteAnalysis(this.userId(context), id);
  }

  async myFavorites(context: any, limit = 20, offset = 0) {
    const entries = await this.favoritesService.getFavorites(this.userId(context), limit, offset);
    return entries.map((entry: any) => mapFavoriteEntry(entry));
  }

  async isFavorite(context: any, jobId: string) {
    return this.favoritesService.isFavorite(this.userId(context), jobId);
  }

  async saveFavorite(context: any, input: any) {
    const entry = await this.favoritesService.addFavorite(this.userId(context), input.jobId, input);
    return mapFavoriteEntry(entry);
  }

  async removeFavorite(context: any, jobId: string) {
    return this.favoritesService.removeFavorite(this.userId(context), jobId);
  }

  async myCvJobs(context: any, limit = 20, status?: string) {
    return this.cvJobsService.listJobs(this.userId(context), status, limit);
  }

  async cvJob(context: any, id: string) {
    return this.cvJobsService.getJob(this.userId(context), id);
  }

  private userId(context: any): string {
    return extractUserIdFromContext(context, this.jwtService);
  }

  mapAssistantStructured(value: any) {
    return mapAssistantStructured(value);
  }

  mapAtsLite(value: any) {
    return mapAtsLite(value);
  }
}

