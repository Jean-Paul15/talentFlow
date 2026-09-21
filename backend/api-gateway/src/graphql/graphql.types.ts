import { Field, Float, InputType, Int, ObjectType } from '@nestjs/graphql';
import {
  IsArray,
  IsBoolean,
  IsEmail,
  IsInt,
  IsOptional,
  IsString,
  Max,
  MaxLength,
  Min,
  MinLength,
} from 'class-validator';

@ObjectType()
export class AuthUserGql {
  @Field()
  id: string;

  @Field()
  email: string;

  @Field({ nullable: true })
  name?: string;
}

@ObjectType()
export class AuthPayloadGql {
  @Field()
  accessToken: string;

  @Field()
  refreshToken: string;

  @Field(() => AuthUserGql)
  user: AuthUserGql;
}

@InputType()
export class RegisterInput {
  @Field()
  @IsEmail()
  email: string;

  @Field()
  @IsString()
  @MinLength(6)
  password: string;

  @Field()
  @IsString()
  @MinLength(2)
  name: string;

  @Field(() => Boolean)
  @IsBoolean()
  acceptTerms: boolean;
}

@InputType()
export class LoginInput {
  @Field()
  @IsEmail()
  email: string;

  @Field()
  @IsString()
  @MinLength(1)
  password: string;
}

@ObjectType()
export class UserProfileGql {
  @Field()
  id: string;

  @Field()
  email: string;

  @Field()
  name: string;

  @Field({ nullable: true })
  phone?: string;

  @Field({ nullable: true })
  location?: string;

  @Field({ nullable: true })
  headline?: string;

  @Field(() => [String], { nullable: 'itemsAndList' })
  preferredRoles?: string[];

  @Field({ nullable: true })
  preferredCountry?: string;
}

@InputType()
export class UpdateProfileInput {
  @Field({ nullable: true })
  @IsOptional()
  @IsString()
  name?: string;

  @Field({ nullable: true })
  @IsOptional()
  @IsString()
  phone?: string;

  @Field({ nullable: true })
  @IsOptional()
  @IsString()
  location?: string;

  @Field({ nullable: true })
  @IsOptional()
  @IsString()
  @MaxLength(255)
  headline?: string;

  @Field(() => [String], { nullable: true })
  @IsOptional()
  @IsArray()
  preferredRoles?: string[];

  @Field({ nullable: true })
  @IsOptional()
  @IsString()
  preferredCountry?: string;
}

@InputType()
export class SearchJobsInput {
  @Field()
  @IsString()
  @MinLength(1)
  query: string;

  @Field(() => Int, { nullable: true })
  @IsOptional()
  @IsInt()
  @Min(1)
  @Max(100)
  limit?: number;

  @Field({ nullable: true })
  @IsOptional()
  @IsString()
  location?: string;

  @Field({ nullable: true })
  @IsOptional()
  @IsString()
  contractType?: string;

  @Field({ nullable: true })
  @IsOptional()
  @IsString()
  country?: string;

  @Field({ nullable: true })
  @IsOptional()
  @IsString()
  sourceName?: string;

  @Field({ nullable: true })
  @IsOptional()
  @IsBoolean()
  rerank?: boolean;

  @Field(() => Int, { nullable: true })
  @IsOptional()
  @IsInt()
  @Min(1)
  @Max(200)
  candidatePoolSize?: number;
}

@ObjectType()
export class SearchJobGql {
  @Field()
  id: string;

  @Field()
  title: string;

  @Field({ nullable: true })
  company?: string;

  @Field({ nullable: true })
  location?: string;

  @Field({ nullable: true })
  contractType?: string;

  @Field({ nullable: true })
  sourceName?: string;

  @Field({ nullable: true })
  sourceUrl?: string;

  @Field({ nullable: true })
  postedDate?: string;

  @Field(() => Float, { nullable: true })
  score?: number;

  @Field({ nullable: true })
  salary?: string;

  @Field({ nullable: true })
  description?: string;
}

@ObjectType()
export class SearchJobsResponseGql {
  @Field()
  query: string;

  @Field(() => Int)
  total: number;

  @Field({ nullable: true })
  backend?: string;

  @Field({ nullable: true })
  searchType?: string;

  @Field({ nullable: true })
  rerankApplied?: boolean;

  @Field(() => [SearchJobGql])
  results: SearchJobGql[];
}

@ObjectType()
export class CvAnalysisGql {
  @Field(() => [String])
  skills: string[];

  @Field(() => Int, { nullable: true })
  experienceYears?: number;

  @Field({ nullable: true })
  educationLevel?: string;

  @Field({ nullable: true })
  rawTextPreview?: string;
}

@ObjectType()
export class RecommendedJobPreviewGql {
  @Field()
  id: string;

  @Field()
  title: string;

  @Field({ nullable: true })
  company?: string;

  @Field({ nullable: true })
  location?: string;

  @Field({ nullable: true })
  contractType?: string;

  @Field({ nullable: true })
  sourceName?: string;

  @Field({ nullable: true })
  sourceUrl?: string;

  @Field({ nullable: true })
  postedDate?: string;

  @Field(() => Float, { nullable: true })
  score?: number;

  @Field({ nullable: true })
  salary?: string;

  @Field({ nullable: true })
  description?: string;

  @Field({ nullable: true })
  summary?: string;
}

@ObjectType()
export class AssistantRecommendedJobGql {
  @Field()
  jobId: string;

  @Field()
  title: string;

  @Field()
  why: string;

  @Field()
  url: string;

  @Field()
  cvImprovement: string;
}

@ObjectType()
export class AssistantOfferRewriteGql {
  @Field()
  targetTitle: string;

  @Field()
  targetSummary: string;

  @Field(() => [String])
  experienceBullets: string[];
}

@ObjectType()
export class AssistantOfferPlaybookGql {
  @Field()
  jobId: string;

  @Field()
  title: string;

  @Field()
  url: string;

  @Field()
  whyFit: string;

  @Field()
  cvDelta: string;

  @Field(() => AssistantOfferRewriteGql)
  rewrite: AssistantOfferRewriteGql;

  @Field(() => [String])
  evidence: string[];
}

@ObjectType()
export class AssistantStructuredGql {
  @Field()
  mode: string;

  @Field()
  profileSummary: string;

  @Field(() => [String])
  strengths: string[];

  @Field(() => [String])
  gaps: string[];

  @Field(() => [AssistantRecommendedJobGql])
  recommendedJobs: AssistantRecommendedJobGql[];

  @Field({ nullable: true })
  scoreExplanation?: string;

  @Field(() => [AssistantOfferPlaybookGql])
  offerPlaybooks: AssistantOfferPlaybookGql[];

  @Field(() => [String])
  actions: string[];

  @Field({ nullable: true })
  reasonIfNoMatch?: string;
}

@ObjectType()
export class AtsLiteGql {
  @Field(() => Int)
  overallScore: number;

  @Field(() => Int)
  structureScore: number;

  @Field(() => Int)
  alignmentScore: number;

  @Field(() => Int)
  evidenceScore: number;

  @Field()
  readinessLabel: string;

  @Field()
  summary: string;

  @Field(() => [String])
  matchedKeywords: string[];

  @Field(() => [String])
  missingKeywords: string[];

  @Field(() => [String])
  suggestions: string[];

  @Field(() => [String])
  actionPlan: string[];
}

@InputType()
export class AtsLiteInput {
  @Field(() => Int)
  @IsInt()
  @Min(0)
  @Max(100)
  overallScore: number;

  @Field(() => Int)
  @IsInt()
  @Min(0)
  @Max(100)
  structureScore: number;

  @Field(() => Int)
  @IsInt()
  @Min(0)
  @Max(100)
  alignmentScore: number;

  @Field(() => Int)
  @IsInt()
  @Min(0)
  @Max(100)
  evidenceScore: number;

  @Field()
  @IsString()
  readinessLabel: string;

  @Field()
  @IsString()
  summary: string;

  @Field(() => [String])
  @IsArray()
  matchedKeywords: string[];

  @Field(() => [String])
  @IsArray()
  missingKeywords: string[];

  @Field(() => [String])
  @IsArray()
  suggestions: string[];

  @Field(() => [String])
  @IsArray()
  actionPlan: string[];
}

@InputType()
export class RecommendCvTextInput {
  @Field()
  @IsString()
  @MinLength(10)
  cvText: string;

  @Field({ nullable: true })
  @IsOptional()
  @IsString()
  fileName?: string;

  @Field(() => Int, { nullable: true })
  @IsOptional()
  @IsInt()
  @Min(1)
  @Max(20)
  topK?: number;

  @Field({ nullable: true })
  @IsOptional()
  @IsString()
  location?: string;

  @Field({ nullable: true })
  @IsOptional()
  @IsString()
  contractType?: string;

  @Field({ nullable: true })
  @IsOptional()
  @IsBoolean()
  useLlm?: boolean;

  @Field({ nullable: true })
  @IsOptional()
  @IsString()
  llmModel?: string;

  @Field({ nullable: true })
  @IsOptional()
  @IsBoolean()
  rerank?: boolean;

  @Field(() => Int, { nullable: true })
  @IsOptional()
  @IsInt()
  @Min(1)
  @Max(200)
  candidatePoolSize?: number;
}

@ObjectType()
export class CvRecommendTextResponseGql {
  @Field(() => CvAnalysisGql)
  cvAnalysis: CvAnalysisGql;

  @Field()
  queryUsed: string;

  @Field(() => Int)
  totalResults: number;

  @Field(() => [RecommendedJobPreviewGql])
  jobs: RecommendedJobPreviewGql[];

  @Field()
  assistantMessage: string;

  @Field()
  llmUsed: boolean;

  @Field({ nullable: true })
  llmProvider?: string;

  @Field({ nullable: true })
  llmModel?: string;

  @Field({ nullable: true })
  llmError?: string;

  @Field({ nullable: true })
  llmStatus?: string;

  @Field(() => AssistantStructuredGql, { nullable: true })
  assistantStructured?: AssistantStructuredGql;

  @Field(() => AtsLiteGql, { nullable: true })
  atsLite?: AtsLiteGql;
}

@InputType()
export class RecommendationHistoryJobInput {
  @Field()
  @IsString()
  id: string;

  @Field()
  @IsString()
  title: string;

  @Field({ nullable: true })
  @IsOptional()
  @IsString()
  company?: string;

  @Field({ nullable: true })
  @IsOptional()
  @IsString()
  location?: string;

  @Field({ nullable: true })
  @IsOptional()
  @IsString()
  contractType?: string;

  @Field({ nullable: true })
  @IsOptional()
  @IsString()
  sourceName?: string;

  @Field({ nullable: true })
  @IsOptional()
  @IsString()
  sourceUrl?: string;

  @Field({ nullable: true })
  @IsOptional()
  @IsString()
  postedDate?: string;

  @Field(() => Float, { nullable: true })
  @IsOptional()
  score?: number;

  @Field({ nullable: true })
  @IsOptional()
  @IsString()
  summary?: string;
}

@InputType()
export class RecommendationHistoryCvAnalysisInput {
  @Field(() => [String], { nullable: 'itemsAndList' })
  @IsOptional()
  @IsArray()
  skills?: string[];

  @Field(() => Int, { nullable: true })
  @IsOptional()
  @IsInt()
  experienceYears?: number;

  @Field({ nullable: true })
  @IsOptional()
  @IsString()
  educationLevel?: string;

  @Field({ nullable: true })
  @IsOptional()
  @IsString()
  rawTextPreview?: string;
}

@InputType()
export class AssistantRecommendedJobInput {
  @Field()
  @IsString()
  jobId: string;

  @Field()
  @IsString()
  title: string;

  @Field()
  @IsString()
  why: string;

  @Field()
  @IsString()
  url: string;

  @Field()
  @IsString()
  cvImprovement: string;
}

@InputType()
export class AssistantOfferRewriteInput {
  @Field()
  @IsString()
  targetTitle: string;

  @Field()
  @IsString()
  targetSummary: string;

  @Field(() => [String])
  @IsArray()
  experienceBullets: string[];
}

@InputType()
export class AssistantOfferPlaybookInput {
  @Field()
  @IsString()
  jobId: string;

  @Field()
  @IsString()
  title: string;

  @Field()
  @IsString()
  url: string;

  @Field()
  @IsString()
  whyFit: string;

  @Field()
  @IsString()
  cvDelta: string;

  @Field(() => AssistantOfferRewriteInput)
  rewrite: AssistantOfferRewriteInput;

  @Field(() => [String])
  @IsArray()
  evidence: string[];
}

@InputType()
export class AssistantStructuredInput {
  @Field()
  @IsString()
  mode: string;

  @Field()
  @IsString()
  profileSummary: string;

  @Field(() => [String])
  @IsArray()
  strengths: string[];

  @Field(() => [String])
  @IsArray()
  gaps: string[];

  @Field(() => [AssistantRecommendedJobInput])
  @IsArray()
  recommendedJobs: AssistantRecommendedJobInput[];

  @Field({ nullable: true })
  @IsOptional()
  @IsString()
  scoreExplanation?: string;

  @Field(() => [AssistantOfferPlaybookInput], { nullable: true })
  @IsOptional()
  @IsArray()
  offerPlaybooks?: AssistantOfferPlaybookInput[];

  @Field(() => [String])
  @IsArray()
  actions: string[];

  @Field({ nullable: true })
  @IsOptional()
  @IsString()
  reasonIfNoMatch?: string;
}

@InputType()
export class SaveRecommendationHistoryInput {
  @Field()
  @IsString()
  @MinLength(1)
  cvTextPreview: string;

  @Field({ nullable: true })
  @IsOptional()
  @IsString()
  fileName?: string;

  @Field({ nullable: true })
  @IsOptional()
  @IsString()
  queryUsed?: string;

  @Field({ nullable: true })
  @IsOptional()
  @IsString()
  locationFilter?: string;

  @Field({ nullable: true })
  @IsOptional()
  @IsString()
  contractTypeFilter?: string;

  @Field()
  @IsString()
  assistantMessage: string;

  @Field()
  @IsBoolean()
  llmUsed: boolean;

  @Field({ nullable: true })
  @IsOptional()
  @IsString()
  llmProvider?: string;

  @Field({ nullable: true })
  @IsOptional()
  @IsString()
  llmModel?: string;

  @Field({ nullable: true })
  @IsOptional()
  @IsString()
  llmError?: string;

  @Field({ nullable: true })
  @IsOptional()
  @IsString()
  llmStatus?: string;

  @Field(() => Int)
  @IsInt()
  @Min(0)
  totalResults: number;

  @Field(() => AssistantStructuredInput, { nullable: true })
  @IsOptional()
  assistantStructured?: AssistantStructuredInput;

  @Field(() => RecommendationHistoryCvAnalysisInput, { nullable: true })
  @IsOptional()
  cvAnalysis?: RecommendationHistoryCvAnalysisInput;

  @Field(() => AtsLiteInput, { nullable: true })
  @IsOptional()
  atsLite?: AtsLiteInput;

  @Field(() => [RecommendationHistoryJobInput])
  @IsArray()
  jobs: RecommendationHistoryJobInput[];
}

@ObjectType()
export class RecommendationHistoryEntryGql {
  @Field()
  id: string;

  @Field()
  cvTextPreview: string;

  @Field({ nullable: true })
  fileName?: string;

  @Field()
  queryUsed: string;

  @Field({ nullable: true })
  locationFilter?: string;

  @Field({ nullable: true })
  contractTypeFilter?: string;

  @Field()
  assistantMessage: string;

  @Field()
  llmUsed: boolean;

  @Field({ nullable: true })
  llmProvider?: string;

  @Field({ nullable: true })
  llmModel?: string;

  @Field({ nullable: true })
  llmError?: string;

  @Field({ nullable: true })
  llmStatus?: string;

  @Field(() => Int)
  totalResults: number;

  @Field(() => AssistantStructuredGql, { nullable: true })
  assistantStructured?: AssistantStructuredGql;

  @Field(() => CvAnalysisGql, { nullable: true })
  cvAnalysis?: CvAnalysisGql;

  @Field(() => AtsLiteGql, { nullable: true })
  atsLite?: AtsLiteGql;

  @Field(() => [RecommendedJobPreviewGql])
  jobs: RecommendedJobPreviewGql[];

  @Field()
  createdAt: string;
}

@ObjectType()
export class FavoriteJobGql {
  @Field()
  id: string;

  @Field()
  jobId: string;

  @Field()
  title: string;

  @Field({ nullable: true })
  company?: string;

  @Field({ nullable: true })
  description?: string;

  @Field({ nullable: true })
  location?: string;

  @Field({ nullable: true })
  contractType?: string;

  @Field({ nullable: true })
  salary?: string;

  @Field({ nullable: true })
  sourceName?: string;

  @Field({ nullable: true })
  sourceUrl?: string;

  @Field({ nullable: true })
  postedDate?: string;

  @Field(() => Float, { nullable: true })
  score?: number;

  @Field()
  createdAt: string;
}

@InputType()
export class SaveFavoriteInput {
  @Field()
  @IsString()
  @MinLength(1)
  jobId: string;

  @Field()
  @IsString()
  @MinLength(1)
  title: string;

  @Field({ nullable: true })
  @IsOptional()
  @IsString()
  company?: string;

  @Field({ nullable: true })
  @IsOptional()
  @IsString()
  description?: string;

  @Field({ nullable: true })
  @IsOptional()
  @IsString()
  location?: string;

  @Field({ nullable: true })
  @IsOptional()
  @IsString()
  contractType?: string;

  @Field({ nullable: true })
  @IsOptional()
  @IsString()
  salary?: string;

  @Field({ nullable: true })
  @IsOptional()
  @IsString()
  sourceName?: string;

  @Field({ nullable: true })
  @IsOptional()
  @IsString()
  sourceUrl?: string;

  @Field({ nullable: true })
  @IsOptional()
  @IsString()
  postedDate?: string;

  @Field(() => Float, { nullable: true })
  @IsOptional()
  score?: number;
}

@ObjectType()
export class CvJobStatusGql {
  @Field()
  jobId: string;

  @Field()
  status: string;

  @Field()
  stage: string;

  @Field(() => Int)
  progress: number;

  @Field()
  stageLabel: string;

  @Field()
  etaHint: string;

  @Field({ nullable: true })
  inputType?: string;

  @Field({ nullable: true })
  fileName?: string;

  @Field({ nullable: true })
  error?: string;

  @Field()
  updatedAt: string;

  @Field({ nullable: true })
  completedAt?: string;

  @Field()
  resultReady: boolean;

  @Field({ nullable: true })
  historyId?: string;
}
