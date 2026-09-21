// Search Service - Proxy vers Search Engine + Cache Redis

import {
  BadRequestException,
  Injectable,
  InternalServerErrorException,
  Logger,
  UnprocessableEntityException,
  UnsupportedMediaTypeException,
  ServiceUnavailableException,
} from '@nestjs/common';
import axios from 'axios';
import * as FormDataModule from 'form-data';
import mammoth from 'mammoth';
import * as pdfParseModule from 'pdf-parse';
import { RedisService } from '../redis/redis.service';
import { CvQualityMetricsService } from '../runtime/cv-quality-metrics.service';
import {
  assessCvText,
  captureCvAssessmentSample,
  type CvDocumentAssessment,
} from './cv-document-classifier';

const FormDataCtor = (((FormDataModule as unknown as { default?: unknown }).default ??
  FormDataModule) as unknown as typeof import('form-data'));
const pdfParse = (((pdfParseModule as unknown as { default?: unknown }).default ??
  pdfParseModule) as (
  dataBuffer: Buffer,
) => Promise<{ text?: string; numpages?: number }>);

@Injectable()
export class SearchService {
  private readonly SEARCH_ENGINE_URL = process.env.SEARCH_ENGINE_URL || 'http://localhost:8003';
  private readonly RECOMMENDATION_URL = process.env.RECOMMENDATION_URL || 'http://localhost:8001';
  private readonly CACHE_TTL = 3600;
  private readonly logger = new Logger(SearchService.name);

  constructor(
    private redis: RedisService,
    private readonly cvQualityMetrics: CvQualityMetricsService,
  ) {}

  async searchJobs(query: string, filters?: any) {
    const cacheKey = `search:${query}:${JSON.stringify(filters)}`;
    const cached = await this.redis.get(cacheKey);

    if (cached) return JSON.parse(cached);

    try {
      const response = await axios.post(`${this.SEARCH_ENGINE_URL}/search`, {
        query,
        ...filters,
      });

      await this.redis.set(cacheKey, JSON.stringify(response.data), this.CACHE_TTL);
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        const status = Number(error.response?.status ?? 0);
        const data = (error.response?.data || {}) as { code?: string; message?: string };
        const code = String(data.code || '').toUpperCase();
        const message = String(data.message || '').trim();
        if (status === 503 && code === 'INDEX_MAINTENANCE') {
          throw new ServiceUnavailableException(
            message || 'Indexation des offres en cours. Patiente quelques instants puis réessaie.',
          );
        }
      }
      throw new InternalServerErrorException('Recherche temporairement indisponible. Réessaie dans quelques instants.');
    }
  }

  async analyzeCV(cvId: string, jobId: string) {
    const cacheKey = `analysis:${cvId}:${jobId}`;
    const cached = await this.redis.get(cacheKey);

    if (cached) return JSON.parse(cached);

    const response = await axios.post(`${this.RECOMMENDATION_URL}/analyze/match`, {
      cv_id: cvId,
      job_id: jobId,
    });

    await this.redis.set(cacheKey, JSON.stringify(response.data), this.CACHE_TTL);
    return response.data;
  }

  async improveCv(cvId: string, jobId: string) {
    return axios.post(`${this.RECOMMENDATION_URL}/analyze/improve-cv`, {
      cv_id: cvId,
      job_id: jobId,
    });
  }

  async recommendFromCvText(payload: {
    cv_text: string;
    file_name?: string;
    top_k?: number;
    location?: string;
    contract_type?: string;
    use_llm?: boolean;
    llm_model?: string;
    rerank?: boolean;
    candidate_pool_size?: number;
  }) {
    const cacheKey = `cv-reco:${JSON.stringify(payload)}`;
    const cached = await this.redis.get(cacheKey);
    if (cached) return JSON.parse(cached);

    try {
      const response = await axios.post(`${this.RECOMMENDATION_URL}/cv/recommend-text`, payload);
      await this.redis.set(cacheKey, JSON.stringify(response.data), 300);
      return response.data;
    } catch (error) {
      const message = this.recommendationErrorMessage(
        error,
        'Impossible d’analyser ce CV pour le moment. Réessaie dans quelques instants.',
      );
      throw new Error(message);
    }
  }

  assessCvText(text: string): CvDocumentAssessment {
    return assessCvText(text);
  }

  async assessCvTextWithModel(
    text: string,
    options?: { useLlm?: boolean },
  ): Promise<CvDocumentAssessment> {
    const normalized = String(text ?? '').trim();
    if (!normalized) {
      return assessCvText(normalized);
    }

    try {
      const response = await axios.post(
        `${this.RECOMMENDATION_URL}/cv/document-assess`,
        {
          cv_text: normalized,
          use_llm: options?.useLlm ?? true,
        },
        {
          timeout: 20000,
          headers: { 'Content-Type': 'application/json' },
        },
      );
      const payload = (response.data ?? {}) as {
        document_kind?: string;
        cv_confidence?: number;
        user_message?: string;
      };
      const documentKind = String(payload.document_kind ?? '').trim();
      const cvConfidence = Number(payload.cv_confidence ?? 0);
      const userMessage = String(payload.user_message ?? '').trim();

      if (documentKind === 'cv' || documentKind === 'ambiguous' || documentKind === 'non_cv') {
        return {
          documentKind,
          cvConfidence: Number.isFinite(cvConfidence)
            ? Math.max(0, Math.min(1, cvConfidence))
            : 0,
          userMessage:
            userMessage ||
            'Le document a été lu. Une validation complémentaire est appliquée.',
          signalSummary: {
            contactSignals: 0,
            sectionSignals: 0,
            chronologySignals: 0,
            experienceSignals: 0,
            roleSignals: 0,
            educationSignals: 0,
            candidateHintSignals: 0,
            skillSignals: 0,
            negativeSignals: 0,
            academicProgramSignals: 0,
            jobPostingSignals: 0,
          },
        };
      }
    } catch (error) {
      this.logger.warn(`Remote CV assessment unavailable, fallback to local classifier: ${String(error)}`);
    }

    return assessCvText(normalized);
  }

  async extractCvText(file: {
    originalname: string;
    mimetype: string;
    size: number;
    buffer: Buffer;
  }) {
    try {
      const fileName = file.originalname || 'cv';
      const normalizedName = fileName.toLowerCase();
      const mimetype = (file.mimetype || '').toLowerCase();
      const isPdf =
        mimetype.includes('pdf') || normalizedName.endsWith('.pdf');
      const isDocx =
        mimetype.includes('wordprocessingml') ||
        normalizedName.endsWith('.docx');
      const isText =
        mimetype.startsWith('text/') ||
        mimetype.includes('json') ||
        normalizedName.endsWith('.txt') ||
        normalizedName.endsWith('.md') ||
        normalizedName.endsWith('.json');

      let extractedText = '';
      let strategy = 'plain_text';
      let pagesProcessed = 0;
      let ocrUsed = false;
      let qualityScore = 1;

      if (isPdf) {
        strategy = 'pdf_parse';
        let nativeParseFailed = false;
        try {
          const result = await pdfParse(file.buffer);
          extractedText = (result.text || '').trim();
          pagesProcessed = Number(result.numpages ?? 0);
        } catch (error) {
          nativeParseFailed = true;
          this.logger.warn(
            `Native PDF extraction failed for ${fileName}: ${String(error)}`,
          );
        }
        qualityScore = this.computeQualityScore(extractedText);

        if (nativeParseFailed || this.shouldRunOcrFallback(qualityScore)) {
          try {
            const ocrResult = await this.ocrPdfFallback(file);
            const ocrText = String(ocrResult.text || '').trim();
            const ocrScore = this.computeQualityScore(ocrText);
            if (
              ocrText.length > 0 &&
              (nativeParseFailed ||
                ocrText.length > extractedText.length ||
                ocrScore > qualityScore)
            ) {
              extractedText = ocrText;
              strategy = nativeParseFailed
                ? 'ocr_recovery'
                : 'ocr_fallback';
              pagesProcessed = ocrResult.pages_processed;
              qualityScore = ocrScore;
              ocrUsed = true;
            } else if (nativeParseFailed) {
              throw new BadRequestException(
                'Le PDF est protégé ou illisible. Essaie une version exportée en texte ou un autre fichier.',
              );
            } else {
              strategy = 'extraction_native';
            }
          } catch (error) {
            if (nativeParseFailed) {
              throw error;
            }
            this.logger.warn(
              `OCR fallback failed for ${fileName}: ${String(error)}`,
            );
            strategy = 'extraction_native';
          }
        } else {
          strategy = 'extraction_native';
        }
      } else if (isDocx) {
        strategy = 'docx_mammoth';
        const result = await mammoth.extractRawText({ buffer: file.buffer });
        extractedText = (result.value || '').trim();
        qualityScore = this.computeQualityScore(extractedText);
      } else if (isText) {
        extractedText = file.buffer.toString('utf8').trim();
        qualityScore = this.computeQualityScore(extractedText);
      } else {
        throw new UnsupportedMediaTypeException(
          'Format non support?. Utilise TXT, PDF ou DOCX.',
        );
      }

      if (!extractedText.trim()) {
        throw new BadRequestException(
          'Le contenu du CV est vide ou illisible. Essaie un autre fichier.',
        );
      }

      const assessment = await this.assessCvTextWithModel(extractedText, {
        useLlm: true,
      });
      await captureCvAssessmentSample(extractedText, assessment);
      if (assessment.documentKind === 'non_cv') {
        await this.cvQualityMetrics.recordAssessment({
          documentKind: 'non_cv',
          accepted: false,
          cvConfidence: assessment.cvConfidence,
          signalSummary: assessment.signalSummary,
        });
        throw new UnprocessableEntityException({
          code: 'NOT_A_CV',
          message: assessment.userMessage,
          documentKind: assessment.documentKind,
          cvConfidence: assessment.cvConfidence,
        });
      }
      await this.cvQualityMetrics.recordAssessment({
        documentKind: assessment.documentKind,
        accepted: true,
        cvConfidence: assessment.cvConfidence,
        signalSummary: assessment.signalSummary,
      });

      return {
        fileName,
        mimeType: file.mimetype,
        size: file.size,
        strategy,
        qualityScore: Number(qualityScore.toFixed(3)),
        pagesProcessed,
        ocrUsed,
        extractedChars: extractedText.length,
        text: extractedText,
        documentKind: assessment.documentKind,
        cvConfidence: assessment.cvConfidence,
        userMessage: assessment.userMessage,
      };
    } catch (error) {
      if (
        error instanceof BadRequestException ||
        error instanceof UnprocessableEntityException ||
        error instanceof UnsupportedMediaTypeException
      ) {
        throw error;
      }
      await this.cvQualityMetrics.recordExtractionError();
      this.logger.error(`extractCvText failed: ${String(error)}`);
      throw new InternalServerErrorException(
        'Impossible de traiter ce CV pour le moment. Réessaie avec un autre fichier.',
      );
    }
  }

  private computeQualityScore(text: string) {
    const value = String(text || '').trim();
    if (!value) return 0;
    const words = value.split(/\s+/).filter(Boolean).length;
    const weird = (value.match(/[^\p{L}\p{N}\s.,;:!?'"()%\-\/@+#]/gu) || []).length;
    const weirdRatio = weird / Math.max(value.length, 1);
    const lengthScore = Math.min(value.length / 1600, 1);
    const wordsScore = Math.min(words / 280, 1);
    const cleanScore = Math.max(0, 1 - weirdRatio * 10);
    return Number(((lengthScore * 0.45) + (wordsScore * 0.35) + (cleanScore * 0.2)).toFixed(3));
  }

  private shouldRunOcrFallback(qualityScore: number) {
    const enabled = String(process.env.CV_INGESTION_OCR_ENABLED ?? 'true').toLowerCase() !== 'false';
    const threshold = Number(process.env.CV_INGESTION_QUALITY_THRESHOLD ?? '0.42');
    return enabled && qualityScore < threshold;
  }

  private async ocrPdfFallback(file: { originalname: string; buffer: Buffer }) {
    const form = new FormDataCtor();
    form.append('file', file.buffer, { filename: file.originalname || 'cv.pdf', contentType: 'application/pdf' });
    const token = String(process.env.CV_INGESTION_INTERNAL_TOKEN || '').trim();
    const maxPages = Number(process.env.CV_INGESTION_OCR_MAX_PAGES || '10');
    const languages = String(process.env.CV_INGESTION_OCR_LANG || 'fra+eng');
    const url = `${this.RECOMMENDATION_URL}/cv-ingestion/ocr-pdf?max_pages=${maxPages}&languages=${encodeURIComponent(languages)}`;
    const response = await axios.post(url, form, {
      headers: {
        ...form.getHeaders(),
        ...(token ? { 'X-Internal-Token': token } : {}),
      },
      timeout: 60000,
    });
    return response.data as { text: string; pages_processed: number };
  }

  private recommendationErrorMessage(error: unknown, fallbackMessage: string) {
    if (axios.isAxiosError(error)) {
      const status = Number(error.response?.status ?? 0);
      const data = error.response?.data;
      const code = String((data as { code?: string } | undefined)?.code || '').trim().toUpperCase();
      const extracted = this.extractApiMessage(data);
      if (status === 422 && code === 'NOT_A_CV') {
        return extracted || 'Ce document ne ressemble pas à un CV exploitable.';
      }
      if (extracted) return extracted;
      if (status >= 500) return fallbackMessage;
      if (status === 401 || status === 403) {
        return 'Session expirée. Reconnecte-toi pour continuer.';
      }
    }
    return fallbackMessage;
  }

  private extractApiMessage(data: unknown) {
    if (!data) return '';
    if (typeof data === 'string') {
      return data.trim();
    }
    if (typeof data !== 'object') {
      return '';
    }
    const value = data as { message?: string | string[]; detail?: unknown };
    if (Array.isArray(value.message)) {
      return value.message.map((item) => String(item)).join(', ').trim();
    }
    if (typeof value.message === 'string' && value.message.trim()) {
      return value.message.trim();
    }
    if (typeof value.detail === 'string' && value.detail.trim()) {
      return value.detail.trim();
    }
    if (
      value.detail &&
      typeof value.detail === 'object' &&
      typeof (value.detail as { message?: string }).message === 'string'
    ) {
      return String((value.detail as { message?: string }).message).trim();
    }
    return '';
  }
}



