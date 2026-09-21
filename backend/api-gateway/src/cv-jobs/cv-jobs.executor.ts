import { Injectable } from '@nestjs/common';
import { CvJobsService } from './cv-jobs.service';
import { SearchService } from '../search/search.service';
import { HistoryService } from '../history/history.service';
import { CV_JOB_STAGES } from './cv-jobs.stage';

@Injectable()
export class CvJobsExecutor {
  constructor(
    private readonly jobs: CvJobsService,
    private readonly search: SearchService,
    private readonly history: HistoryService,
  ) {}

  async run(jobId: string) {
    const job = await this.jobs.getJobById(jobId);
    if (!job || job.status !== 'QUEUED') return;
    const input = await this.jobs.loadInput(jobId);
    if (!input) return this.jobs.failJob(jobId, 'Entrée de tâche expirée');

    try {
      await this.jobs.updateJob(jobId, {
        status: 'IN_PROGRESS',
        stage: CV_JOB_STAGES.EXTRACT_TEXT,
        progress: 10,
        error: null,
      });
      const prepared = await this.prepareCvText(job.inputType, input);
      const extractionMeta = prepared.meta ?? {};

      await this.jobs.updateJob(jobId, {
        stage: CV_JOB_STAGES.OCR_IF_NEEDED,
        progress: 30,
        extractionMeta: extractionMeta as any,
      });
      await this.jobs.updateJob(jobId, {
        stage: CV_JOB_STAGES.ANALYZE_PROFILE,
        progress: 50,
      });
      await this.jobs.updateJob(jobId, {
        stage: CV_JOB_STAGES.SEARCH_MATCHING,
        progress: 68,
      });
      const reco = await this.search.recommendFromCvText({
        cv_text: prepared.cvText,
        file_name: prepared.fileName,
        top_k: Math.max(1, Number(input.topK ?? 5)),
        location: String(input.location ?? '').trim() || undefined,
        contract_type: String(input.contractType ?? '').trim() || undefined,
        use_llm: true,
        rerank: false,
      });

      await this.jobs.updateJob(jobId, {
        stage: CV_JOB_STAGES.LLM_SYNTHESIS,
        progress: 82,
      });
      await this.jobs.updateJob(jobId, {
        stage: CV_JOB_STAGES.SAVE_HISTORY,
        progress: 92,
      });
      const history = await this.history.saveAnalysis(job.userId, {
        cvTextPreview: prepared.cvText.slice(0, 600),
        fileName: prepared.fileName,
        queryUsed: String(reco.query_used ?? ''),
        assistantMessage: String(reco.assistant_message ?? ''),
        llmUsed: Boolean(reco.llm_used),
        llmProvider: reco.llm_provider ?? null,
        llmModel: reco.llm_model ?? null,
        llmError: reco.llm_error ?? null,
        llmStatus: reco.llm_status ?? null,
        totalResults: Number(reco.total_results ?? 0),
        assistantStructured: (reco.assistant_structured ?? null) as any,
        cvAnalysis: ({ ...(reco.cv_analysis ?? {}), atsLite: reco.ats_lite ?? null }) as any,
        jobsSnapshot: (Array.isArray(reco.jobs) ? reco.jobs : []) as any,
      });

      await this.jobs.updateJob(jobId, {
        status: 'COMPLETED',
        stage: CV_JOB_STAGES.COMPLETED,
        progress: 100,
        completedAt: new Date(),
        resultPayload: {
          historyId: history.id,
          queryUsed: reco.query_used ?? '',
          totalResults: Number(reco.total_results ?? 0),
          llmStatus: reco.llm_status ?? 'fallback_used',
        } as any,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erreur inattendue';
      await this.jobs.failJob(jobId, message);
    }
  }

  private async prepareCvText(inputType: string, input: Record<string, unknown>) {
    if (inputType === 'TEXT') {
      const cvText = String(input.cvText ?? '').trim();
      if (cvText.length < 10) throw new Error('CV texte trop court');
      const assessment = await this.search.assessCvTextWithModel(cvText, {
        useLlm: true,
      });
      if (assessment.documentKind === 'non_cv') {
        throw new Error(assessment.userMessage);
      }
      return {
        cvText,
        fileName: String(input.fileName ?? 'cv.txt'),
        meta: {
          strategy: 'plain_text',
          ocrUsed: false,
          extractedChars: cvText.length,
          documentKind: assessment.documentKind,
          cvConfidence: assessment.cvConfidence,
        },
      };
    }

    const bytesBase64 = String(input.bytesBase64 ?? '');
    const fileName = String(input.fileName ?? 'cv.pdf');
    if (!bytesBase64) throw new Error('Fichier importé expiré');

    const bytes = Buffer.from(bytesBase64, 'base64');
    const extracted = await this.search.extractCvText({
      originalname: fileName,
      mimetype: String(input.mimeType ?? 'application/pdf'),
      size: bytes.length,
      buffer: bytes,
    } as any);
    const cvText = String(extracted.text ?? '').trim();
    if (cvText.length < 10) throw new Error('Extraction CV insuffisante');

    return {
      cvText,
      fileName,
      meta: {
        strategy: extracted.strategy,
        qualityScore: extracted.qualityScore,
        pagesProcessed: extracted.pagesProcessed,
        ocrUsed: extracted.ocrUsed,
        extractedChars: extracted.extractedChars,
        documentKind: extracted.documentKind,
        cvConfidence: extracted.cvConfidence,
      },
    };
  }
}

