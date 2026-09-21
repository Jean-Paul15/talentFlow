import { readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { Injectable } from '@nestjs/common';
import fontkit from '@pdf-lib/fontkit';
import {
  PDFDocument,
  StandardFonts,
  rgb,
  type PDFImage,
  type PDFPage,
  type PDFFont,
} from 'pdf-lib';
import { HistoryService } from '../history/history.service';

const PAGE_WIDTH = 595.28;
const PAGE_HEIGHT = 841.89;
const PAGE_LEFT = 32;
const PAGE_RIGHT = 563;
const CONTENT_WIDTH = PAGE_RIGHT - PAGE_LEFT;
const REPORT_LOGO_CANDIDATES = [
  join(process.cwd(), 'dist', 'src', 'reports', 'assets', 'talentflow-logo.png'),
  join(process.cwd(), 'dist', 'reports', 'assets', 'talentflow-logo.png'),
  join(process.cwd(), 'src', 'reports', 'assets', 'talentflow-logo.png'),
];
const REPORT_FONT_REGULAR_CANDIDATES = [
  join(process.cwd(), 'dist', 'src', 'reports', 'assets', 'NotoSans-Regular.ttf'),
  join(process.cwd(), 'dist', 'reports', 'assets', 'NotoSans-Regular.ttf'),
  join(process.cwd(), 'src', 'reports', 'assets', 'NotoSans-Regular.ttf'),
];
const REPORT_FONT_BOLD_CANDIDATES = [
  join(process.cwd(), 'dist', 'src', 'reports', 'assets', 'NotoSans-Bold.ttf'),
  join(process.cwd(), 'dist', 'reports', 'assets', 'NotoSans-Bold.ttf'),
  join(process.cwd(), 'src', 'reports', 'assets', 'NotoSans-Bold.ttf'),
];

@Injectable()
export class ReportsService {
  constructor(private readonly historyService: HistoryService) {}

  async buildHistoryPdf(userId: string, historyId: string) {
    const entry = await this.historyService.getHistoryEntry(userId, historyId);
    const pdf = await PDFDocument.create();
    pdf.registerFontkit(fontkit);
    const { regular, bold } = await this.loadReportFonts(pdf);
    const logo = await this.tryLoadLogo(pdf);
    const pages: PDFPage[] = [];
    const firstPage = pdf.addPage([PAGE_WIDTH, PAGE_HEIGHT]);
    pages.push(firstPage);

    const state: ReportState = {
      pdf,
      pages,
      page: firstPage,
      cursorY: 784,
    };

    const cvAnalysis = this.asObject(entry.cvAnalysis);
    const assistant = this.asObject(entry.assistantStructured);
    const atsLite = this.asObject(cvAnalysis?.atsLite);
    const jobs = Array.isArray(entry.jobsSnapshot) ? entry.jobsSnapshot : [];
    const scores = {
      global: this.toInt(atsLite?.overallScore ?? atsLite?.overall_score),
      structure: this.toInt(atsLite?.structureScore ?? atsLite?.structure_score),
      alignment: this.toInt(atsLite?.alignmentScore ?? atsLite?.alignment_score),
      evidence: this.toInt(atsLite?.evidenceScore ?? atsLite?.evidence_score),
    };
    const candidateProfile = this.extractCandidateProfile(cvAnalysis, entry.fileName);
    const reportTitle = entry.fileName || 'Rapport TalentFlow';
    const reportRef = historyId.slice(0, 8).toUpperCase();

    this.drawHeader(state, bold, regular, reportTitle, reportRef, logo);
    this.drawHero(state, bold, regular, {
      mode: String(assistant?.mode || 'match'),
      summary:
        String(assistant?.profileSummary || atsLite?.summary || '').trim() ||
        'Diagnostic candidature généré depuis votre dernière analyse.',
      score: scores.global,
      createdAt: this.formatDate(entry.createdAt),
    });

    this.drawScoreBand(state, bold, regular, scores);
    this.drawProfileCard(state, bold, regular, candidateProfile);
    this.drawScoreLegend(state, bold, regular, scores);

    this.drawSectionTitle(state, bold, 'Lecture du profil');
    this.drawParagraph(
      state,
      regular,
      this.composeProfileSummary(cvAnalysis, assistant, atsLite),
    );

    this.drawTwoColumnBullets(state, bold, regular, {
      leftTitle: 'Forces visibles',
      leftItems: this.toStrings(assistant?.strengths).length
        ? this.toStrings(assistant?.strengths)
        : this.toStrings(atsLite?.matchedKeywords ?? atsLite?.matched_keywords),
      rightTitle: 'Points à renforcer',
      rightItems: this.toStrings(assistant?.gaps).length
        ? this.toStrings(assistant?.gaps)
        : this.toStrings(atsLite?.missingKeywords ?? atsLite?.missing_keywords),
    });

    this.drawTwoColumnBullets(state, bold, regular, {
      leftTitle: 'Actions immédiates',
      leftItems: this.toStrings(assistant?.actions),
      rightTitle: 'Plan 7 jours',
      rightItems: this.buildSevenDayPlan(assistant, atsLite),
    });

    this.drawSectionTitle(state, bold, 'Top opportunités retenues');
    if (!jobs.length || String(assistant?.mode || '') === 'no_match') {
      this.drawCallout(
        state,
        bold,
        regular,
        'Aucune offre crédible à pousser',
        String(
          assistant?.reasonIfNoMatch ||
            "Le moteur n'a pas retenu d'offre suffisamment solide pour cette analyse.",
        ),
      );
    } else {
      for (const job of jobs.slice(0, 3)) {
        this.drawJobCard(state, bold, regular, job, assistant);
      }
    }

    this.drawFooter(pages, regular, reportRef);
    const bytes = await pdf.save();
    const fileName = this.sanitizeFileName(`talentflow-rapport-${historyId}.pdf`);
    return { bytes: Buffer.from(bytes), fileName };
  }

  private drawHeader(
    state: ReportState,
    bold: PDFFont,
    regular: PDFFont,
    fileName: string,
    reportRef: string,
    logo: PDFImage | null,
  ) {
    const { page } = state;
    page.drawRectangle({
      x: 28,
      y: 772,
      width: 539,
      height: 50,
      color: rgb(0.07, 0.13, 0.17),
    });

    if (logo) {
      page.drawImage(logo, {
        x: 42,
        y: 784,
        width: 24,
        height: 24,
      });
    }

    this.drawTextSafe(page, 'TalentFlow', {
      x: logo ? 76 : 44,
      y: 795,
      font: bold,
      size: 21,
      color: rgb(0.96, 0.94, 0.91),
    });
    this.drawTextSafe(page, 'Rapport candidature premium', {
      x: logo ? 182 : 150,
      y: 798,
      font: regular,
      size: 11,
      color: rgb(0.86, 0.91, 0.92),
    });
    this.drawTextSafe(page, `Ref. ${reportRef}`, {
      x: 464,
      y: 794,
      font: bold,
      size: 9.5,
      color: rgb(0.94, 0.78, 0.5),
    });
    this.drawTextSafe(page, fileName, {
      x: 44,
      y: 758,
      font: regular,
      size: 9,
      color: rgb(0.35, 0.42, 0.46),
    });
    state.cursorY = 736;
  }

  private drawHero(
    state: ReportState,
    bold: PDFFont,
    regular: PDFFont,
    data: { mode: string; summary: string; score: number; createdAt: string },
  ) {
    this.ensureSpace(state, 124);
    const y = state.cursorY;

    state.page.drawRectangle({
      x: PAGE_LEFT,
      y: y - 102,
      width: CONTENT_WIDTH,
      height: 102,
      color: rgb(0.95, 0.93, 0.89),
      borderColor: rgb(0.82, 0.78, 0.72),
      borderWidth: 1,
    });

    this.drawTextSafe(
      state.page,
      data.mode === 'no_match' ? 'Diagnostic candidature' : 'Offres crédibles identifiées',
      {
        x: 48,
        y: y - 26,
        font: bold,
        size: 20,
        color: rgb(0.07, 0.13, 0.17),
      },
    );

    this.drawWrappedText(state.page, data.summary, {
      x: 48,
      y: y - 50,
      width: 350,
      font: regular,
      size: 10.5,
      color: rgb(0.17, 0.22, 0.27),
      lineHeight: 14,
    });

    state.page.drawRectangle({
      x: 430,
      y: y - 86,
      width: 110,
      height: 64,
      color: rgb(0.06, 0.46, 0.43),
    });
    this.drawTextSafe(state.page, `${data.score}/100`, {
      x: 447,
      y: y - 53,
      font: bold,
      size: 22,
      color: rgb(1, 1, 1),
    });
    this.drawTextSafe(state.page, 'ATS-lite', {
      x: 455,
      y: y - 72,
      font: regular,
      size: 10,
      color: rgb(0.89, 0.97, 0.96),
    });
    this.drawTextSafe(state.page, data.createdAt, {
      x: 48,
      y: y - 90,
      font: regular,
      size: 9,
      color: rgb(0.4, 0.45, 0.49),
    });

    state.cursorY = y - 122;
  }

  private drawScoreBand(
    state: ReportState,
    bold: PDFFont,
    regular: PDFFont,
    scores: { global: number; structure: number; alignment: number; evidence: number },
  ) {
    this.ensureSpace(state, 92);
    const cards = [
      { label: 'Global', score: scores.global, color: rgb(0.06, 0.46, 0.43) },
      { label: 'Structure', score: scores.structure, color: rgb(0.77, 0.6, 0.35) },
      { label: 'Alignement', score: scores.alignment, color: rgb(0.85, 0.42, 0.26) },
      { label: 'Preuves', score: scores.evidence, color: rgb(0.11, 0.51, 0.28) },
    ];
    const width = 124;
    const gap = 10;
    const y = state.cursorY;

    cards.forEach((card, index) => {
      const x = PAGE_LEFT + index * (width + gap);
      state.page.drawRectangle({
        x,
        y: y - 78,
        width,
        height: 78,
        color: rgb(1, 1, 1),
        borderColor: rgb(0.86, 0.83, 0.78),
        borderWidth: 1,
      });
      this.drawTextSafe(state.page, card.label, {
        x: x + 14,
        y: y - 20,
        font: regular,
        size: 9.5,
        color: rgb(0.33, 0.38, 0.42),
      });
      this.drawTextSafe(state.page, `${card.score}`, {
        x: x + 14,
        y: y - 47,
        font: bold,
        size: 22,
        color: card.color,
      });
      this.drawTextSafe(state.page, '/100', {
        x: x + 52,
        y: y - 41,
        font: regular,
        size: 10,
        color: rgb(0.38, 0.42, 0.46),
      });
      this.drawBar(state.page, x + 14, y - 64, width - 28, 7, card.score, card.color);
    });

    state.cursorY = y - 94;
  }

  private drawProfileCard(
    state: ReportState,
    bold: PDFFont,
    regular: PDFFont,
    profile: { name: string; phone: string },
  ) {
    this.ensureSpace(state, 72);
    const y = state.cursorY;

    state.page.drawRectangle({
      x: PAGE_LEFT,
      y: y - 62,
      width: CONTENT_WIDTH,
      height: 62,
      color: rgb(0.98, 0.98, 0.98),
      borderColor: rgb(0.86, 0.83, 0.78),
      borderWidth: 1,
    });

    this.drawTextSafe(state.page, 'Profil candidat', {
      x: 46,
      y: y - 20,
      font: bold,
      size: 11.5,
      color: rgb(0.07, 0.13, 0.17),
    });
    this.drawTextSafe(state.page, `Nom: ${profile.name}`, {
      x: 46,
      y: y - 38,
      font: regular,
      size: 10,
      color: rgb(0.18, 0.23, 0.27),
    });
    this.drawTextSafe(state.page, `Téléphone: ${profile.phone}`, {
      x: 290,
      y: y - 38,
      font: regular,
      size: 10,
      color: rgb(0.18, 0.23, 0.27),
    });

    state.cursorY = y - 74;
  }

  private drawScoreLegend(
    state: ReportState,
    bold: PDFFont,
    regular: PDFFont,
    scores: { global: number; structure: number; alignment: number; evidence: number },
  ) {
    this.ensureSpace(state, 114);
    const y = state.cursorY;

    state.page.drawRectangle({
      x: PAGE_LEFT,
      y: y - 102,
      width: CONTENT_WIDTH,
      height: 102,
      color: rgb(0.95, 0.97, 0.99),
      borderColor: rgb(0.78, 0.84, 0.90),
      borderWidth: 1,
    });

    this.drawTextSafe(state.page, 'Comment lire les scores', {
      x: 46,
      y: y - 20,
      font: bold,
      size: 11.5,
      color: rgb(0.07, 0.13, 0.17),
    });

    const explanation = [
      `Score global (${scores.global}/100): vision d’ensemble de la préparation candidature.`,
      `Structure (${scores.structure}/100): clarté du CV, sections et lisibilité.`,
      `Alignement (${scores.alignment}/100): cohérence entre ton profil et les offres ciblées.`,
      `Preuves (${scores.evidence}/100): résultats concrets, chiffres et impact démontré.`,
    ].join(' ');

    this.drawWrappedText(state.page, explanation, {
      x: 46,
      y: y - 40,
      width: 500,
      font: regular,
      size: 9.6,
      color: rgb(0.18, 0.23, 0.27),
      lineHeight: 13,
    });

    state.cursorY = y - 114;
  }

  private drawSectionTitle(state: ReportState, bold: PDFFont, title: string) {
    this.ensureSpace(state, 30);
    this.drawTextSafe(state.page, title, {
      x: 36,
      y: state.cursorY,
      font: bold,
      size: 15,
      color: rgb(0.07, 0.13, 0.17),
    });
    state.cursorY -= 22;
  }

  private drawParagraph(state: ReportState, regular: PDFFont, text: string) {
    this.ensureSpace(state, 64);
    const height = this.drawWrappedText(state.page, text, {
      x: 36,
      y: state.cursorY,
      width: 520,
      font: regular,
      size: 10.5,
      color: rgb(0.18, 0.23, 0.27),
      lineHeight: 14,
    });
    state.cursorY -= height + 10;
  }

  private drawTwoColumnBullets(
    state: ReportState,
    bold: PDFFont,
    regular: PDFFont,
    data: { leftTitle: string; leftItems: string[]; rightTitle: string; rightItems: string[] },
  ) {
    const leftHeight = this.measureBulletList(regular, 233, data.leftItems);
    const rightHeight = this.measureBulletList(regular, 233, data.rightItems);
    const boxHeight = Math.max(102, 42 + Math.max(leftHeight, rightHeight));
    this.ensureSpace(state, boxHeight + 18);

    const leftX = 32;
    const rightX = 302;
    [leftX, rightX].forEach((x) => {
      state.page.drawRectangle({
        x,
        y: state.cursorY - boxHeight,
        width: 261,
        height: boxHeight,
        color: rgb(1, 1, 1),
        borderColor: rgb(0.86, 0.83, 0.78),
        borderWidth: 1,
      });
    });

    this.drawTextSafe(state.page, data.leftTitle, {
      x: leftX + 14,
      y: state.cursorY - 18,
      font: bold,
      size: 11,
      color: rgb(0.07, 0.13, 0.17),
    });
    this.drawTextSafe(state.page, data.rightTitle, {
      x: rightX + 14,
      y: state.cursorY - 18,
      font: bold,
      size: 11,
      color: rgb(0.07, 0.13, 0.17),
    });

    this.drawBullets(state.page, regular, leftX + 14, state.cursorY - 38, 233, data.leftItems);
    this.drawBullets(state.page, regular, rightX + 14, state.cursorY - 38, 233, data.rightItems);
    state.cursorY -= boxHeight + 14;
  }

  private drawCallout(
    state: ReportState,
    bold: PDFFont,
    regular: PDFFont,
    title: string,
    message: string,
  ) {
    this.ensureSpace(state, 90);
    const y = state.cursorY;

    state.page.drawRectangle({
      x: PAGE_LEFT,
      y: y - 82,
      width: CONTENT_WIDTH,
      height: 82,
      color: rgb(0.93, 0.96, 0.98),
      borderColor: rgb(0.72, 0.82, 0.88),
      borderWidth: 1,
    });

    this.drawTextSafe(state.page, title, {
      x: 48,
      y: y - 26,
      font: bold,
      size: 12,
      color: rgb(0.07, 0.13, 0.17),
    });
    this.drawWrappedText(state.page, message, {
      x: 48,
      y: y - 44,
      width: 490,
      font: regular,
      size: 10,
      color: rgb(0.18, 0.23, 0.27),
      lineHeight: 13,
    });

    state.cursorY = y - 96;
  }

  private drawJobCard(
    state: ReportState,
    bold: PDFFont,
    regular: PDFFont,
    job: any,
    assistant: Record<string, any> | null,
  ) {
    this.ensureSpace(state, 122);
    const y = state.cursorY;
    const title = String(job.title ?? 'Offre');
    const company = String(job.company ?? '').trim();
    const location = String(job.location ?? '').trim();
    const source = String(job.sourceName ?? job.source_name ?? '').trim();
    const url = String(job.sourceUrl ?? job.source_url ?? '').trim();
    const meta = [company, location, source].filter(Boolean).join(' - ');
    const explanation = this.findJobExplanation(assistant, job);
    const score = this.toFloat(job.score);

    state.page.drawRectangle({
      x: PAGE_LEFT,
      y: y - 112,
      width: CONTENT_WIDTH,
      height: 112,
      color: rgb(1, 1, 1),
      borderColor: rgb(0.86, 0.83, 0.78),
      borderWidth: 1,
    });

    this.drawWrappedText(state.page, title, {
      x: 46,
      y: y - 24,
      width: 330,
      font: bold,
      size: 12.5,
      color: rgb(0.07, 0.13, 0.17),
      lineHeight: 14,
    });
    this.drawWrappedText(state.page, meta || 'Offre indexée par TalentFlow', {
      x: 46,
      y: y - 42,
      width: 330,
      font: regular,
      size: 9.5,
      color: rgb(0.36, 0.41, 0.45),
      lineHeight: 11,
    });
    this.drawWrappedText(state.page, explanation, {
      x: 46,
      y: y - 58,
      width: 330,
      font: regular,
      size: 9.5,
      color: rgb(0.16, 0.21, 0.25),
      lineHeight: 12,
    });
    this.drawTextSafe(state.page, `${score.toFixed(2)}`, {
      x: 430,
      y: y - 30,
      font: bold,
      size: 18,
      color: rgb(0.06, 0.46, 0.43),
    });
    this.drawTextSafe(state.page, 'Score moteur', {
      x: 430,
      y: y - 46,
      font: regular,
      size: 9,
      color: rgb(0.36, 0.41, 0.45),
    });
    this.drawWrappedText(state.page, url || 'Lien source indisponible', {
      x: 430,
      y: y - 64,
      width: 105,
      font: regular,
      size: 8.5,
      color: rgb(0.2, 0.42, 0.6),
      lineHeight: 11,
    });

    state.cursorY = y - 124;
  }

  private drawFooter(pages: PDFPage[], regular: PDFFont, reportRef: string) {
    const total = pages.length;
    pages.forEach((page, index) => {
      this.drawTextSafe(
        page,
        `TalentFlow - Rapport candidature - Ref. ${reportRef} - Page ${index + 1}/${total}`,
        {
          x: 36,
          y: 18,
          font: regular,
          size: 8.5,
          color: rgb(0.43, 0.47, 0.51),
        },
      );
    });
  }

  private ensureSpace(state: ReportState, requiredHeight: number) {
    if (state.cursorY - requiredHeight > 46) {
      return;
    }
    state.page = state.pdf.addPage([PAGE_WIDTH, PAGE_HEIGHT]);
    state.pages.push(state.page);
    state.cursorY = 790;
  }

  private drawWrappedText(
    page: PDFPage,
    text: string,
    options: {
      x: number;
      y: number;
      width: number;
      font: PDFFont;
      size: number;
      color: ReturnType<typeof rgb>;
      lineHeight: number;
    },
  ) {
    const lines = this.wrapText(text, options.font, options.size, options.width);
    if (!lines.length) return 0;

    lines.forEach((line, index) => {
      this.drawTextSafe(page, line, {
        x: options.x,
        y: options.y - index * options.lineHeight,
        font: options.font,
        size: options.size,
        color: options.color,
      });
    });

    return lines.length * options.lineHeight;
  }

  private drawBullets(
    page: PDFPage,
    regular: PDFFont,
    x: number,
    y: number,
    width: number,
    items: string[],
  ) {
    const safeItems = items.length ? items.slice(0, 4) : ['Aucun point prioritaire remonté.'];
    let cursorY = y;

    safeItems.forEach((item) => {
      const lines = this.wrapText(item, regular, 9.5, width - 12);
      page.drawCircle({
        x,
        y: cursorY + 4,
        size: 2.8,
        color: rgb(0.06, 0.46, 0.43),
      });
      lines.forEach((line, lineIndex) => {
        this.drawTextSafe(page, line, {
          x: x + 10,
          y: cursorY - lineIndex * 12,
          font: regular,
          size: 9.5,
          color: rgb(0.18, 0.23, 0.27),
        });
      });
      cursorY -= Math.max(18, lines.length * 12 + 4);
    });
  }

  private drawBar(
    page: PDFPage,
    x: number,
    y: number,
    width: number,
    height: number,
    score: number,
    color: ReturnType<typeof rgb>,
  ) {
    page.drawRectangle({
      x,
      y,
      width,
      height,
      color: rgb(0.92, 0.92, 0.9),
    });
    page.drawRectangle({
      x,
      y,
      width: Math.max(0, Math.min(width, (width * score) / 100)),
      height,
      color,
    });
  }

  private drawTextSafe(
    page: PDFPage,
    text: string,
    options: { x: number; y: number; font: PDFFont; size: number; color: ReturnType<typeof rgb> },
  ) {
    const safe = this.normalizeText(text);
    if (!safe) return;
    page.drawText(safe, options);
  }

  private composeProfileSummary(
    cvAnalysis: Record<string, any> | null,
    assistant: Record<string, any> | null,
    atsLite: Record<string, any> | null,
  ) {
    const skills = this.toStrings(cvAnalysis?.skills).slice(0, 8).join(', ');
    const years = cvAnalysis?.experienceYears ?? cvAnalysis?.experience_years;
    const education = cvAnalysis?.educationLevel ?? cvAnalysis?.education_level;
    const interests = this.toStrings(
      cvAnalysis?.interests ??
        cvAnalysis?.centresInteret ??
        cvAnalysis?.centres_d_interet ??
        cvAnalysis?.hobbies,
    )
      .slice(0, 4)
      .join(', ');
    const summary =
      String(assistant?.profileSummary || atsLite?.summary || '').trim() ||
      'Profil synthétisé à partir du CV importé et des signaux de matching.';

    return `${summary} Compétences visibles: ${skills || 'non précisées'}. Expérience estimée: ${years ?? 'n/a'} an(s). Niveau détecté: ${education ?? 'n/a'}. Centres d'intérêt: ${interests || 'non renseignés'}.`;
  }

  private findJobExplanation(assistant: Record<string, any> | null, job: any) {
    const items = Array.isArray(assistant?.recommendedJobs)
      ? assistant?.recommendedJobs
      : Array.isArray(assistant?.recommended_jobs)
        ? assistant?.recommended_jobs
        : [];
    const currentId = String(job.id ?? '');
    const currentUrl = String(job.sourceUrl ?? job.source_url ?? '');
    const match = items.find((item: any) => {
      const jobId = String(item?.jobId ?? item?.job_id ?? '');
      const url = String(item?.url ?? '');
      return (jobId && jobId === currentId) || (url && url === currentUrl);
    });

    return String(
      match?.why ||
        job.summary ||
        'Cette offre a été retenue car elle reste alignée avec votre profil et vos compétences visibles.',
    ).trim();
  }

  private formatDate(value: unknown) {
    const parsed = value instanceof Date ? value : new Date(String(value ?? ''));
    if (Number.isNaN(parsed.getTime())) {
      return 'Rapport généré par TalentFlow';
    }

    const day = `${parsed.getDate()}`.padStart(2, '0');
    const month = `${parsed.getMonth() + 1}`.padStart(2, '0');
    const year = parsed.getFullYear();
    const hour = `${parsed.getHours()}`.padStart(2, '0');
    const minute = `${parsed.getMinutes()}`.padStart(2, '0');
    return `Analyse du ${day}/${month}/${year} à ${hour}:${minute}`;
  }

  private sanitizeFileName(value: string) {
    return value.replace(/[^a-zA-Z0-9._-]+/g, '-');
  }

  private async loadReportFonts(pdf: PDFDocument): Promise<{ regular: PDFFont; bold: PDFFont }> {
    const regularFont = await this.tryLoadFont(pdf, REPORT_FONT_REGULAR_CANDIDATES);
    const boldFont = await this.tryLoadFont(pdf, REPORT_FONT_BOLD_CANDIDATES);
    if (regularFont && boldFont) {
      return { regular: regularFont, bold: boldFont };
    }

    return {
      regular: await pdf.embedFont(StandardFonts.Helvetica),
      bold: await pdf.embedFont(StandardFonts.HelveticaBold),
    };
  }

  private async tryLoadFont(pdf: PDFDocument, candidates: string[]): Promise<PDFFont | null> {
    for (const assetPath of candidates) {
      try {
        const bytes = await readFile(assetPath);
        return await pdf.embedFont(bytes, { subset: true });
      } catch {
        continue;
      }
    }
    return null;
  }

  private extractCandidateProfile(cvAnalysis: Record<string, any> | null, fallbackName: string | null) {
    const rawPreview = String(cvAnalysis?.rawTextPreview ?? cvAnalysis?.raw_text_preview ?? '').trim();
    const explicitName = String(
      cvAnalysis?.name ??
        cvAnalysis?.fullName ??
        cvAnalysis?.candidateName ??
        cvAnalysis?.candidate_name ??
        '',
    ).trim();
    const candidateName =
      explicitName ||
      this.extractLikelyName(rawPreview) ||
      String(fallbackName || '').replace(/\.[a-z0-9]+$/i, '').trim() ||
      'Non renseigné';

    const phoneMatch = rawPreview.match(/(?:\+?\d[\d\s().-]{7,}\d)/);
    const candidatePhone = phoneMatch ? phoneMatch[0].trim() : 'Non renseigné';

    return {
      name: candidateName,
      phone: candidatePhone,
    };
  }

  private extractLikelyName(text: string): string {
    if (!text) return '';
    const firstLine = String(text.split(/\r?\n/)[0] ?? '').trim();
    if (!firstLine) return '';
    const cleaned = firstLine.replace(/[^\p{L}\s'-]/gu, ' ').replace(/\s+/g, ' ').trim();
    if (!cleaned) return '';
    const tokens = cleaned.split(' ').filter(Boolean);
    if (tokens.length < 2 || tokens.length > 4) return '';
    const isLikelyName = tokens.every((token) => token.length >= 2 && token.length <= 24);
    return isLikelyName ? cleaned : '';
  }

  private buildSevenDayPlan(
    assistant: Record<string, any> | null,
    atsLite: Record<string, any> | null,
  ): string[] {
    const missing = this.toStrings(assistant?.gaps).concat(
      this.toStrings(atsLite?.missingKeywords ?? atsLite?.missing_keywords),
    );
    const actions = this.toStrings(assistant?.actions);
    const playbooks = this.toObjects(assistant?.offerPlaybooks ?? assistant?.offer_playbooks);
    const primaryPlaybook = playbooks[0] ?? {};
    const rewrite = this.asObject(primaryPlaybook.rewrite);
    const targetTitle = String(rewrite?.targetTitle ?? rewrite?.target_title ?? '').trim();
    const targetSummary = String(rewrite?.targetSummary ?? rewrite?.target_summary ?? '').trim();
    const experienceBullets = this.toStrings(
      rewrite?.experienceBullets ?? rewrite?.experience_bullets,
    );
    const evidence = this.toStrings(primaryPlaybook.evidence);

    const overall = this.toInt(atsLite?.overallScore ?? atsLite?.overall_score);
    const targetScore = Math.min(95, Math.max(overall + 12, 72));
    const scoreDelta = Math.max(6, targetScore - overall);
    const dailyDelta = Math.max(1, Math.round(scoreDelta / 7));
    const focusA = missing[0] || 'positionnement du profil';
    const focusB = missing[1] || 'preuves d’impact';
    const summaryLine =
      targetSummary.length > 8
        ? targetSummary
        : 'Résumé orienté rôle: spécialité, niveau, valeur métier en 3 lignes.';

    const finalTargetTitle = targetTitle.length > 0 ? targetTitle : 'Poste visé';
    const firstExperienceAction =
      experienceBullets.length > 0
        ? experienceBullets[0]
        : `ajoute une mission chiffrée sur ${focusA}.`;
    const secondExperienceAction =
      experienceBullets.length > 1
        ? experienceBullets[1]
        : `ajoute une 2e preuve mesurable pour ${focusB}.`;

    const plan: string[] = [
      `Jour 1: Section Titre/En-tête -> remplace le titre actuel par "${finalTargetTitle}". Livrable: titre aligné sur l'offre cible.`,
      `Jour 2: Section Résumé -> réécris 3 lignes: ${summaryLine} Livrable: résumé clair orienté métier.`,
      `Jour 3: Section Expériences -> ${firstExperienceAction} Livrable: 1 expérience avec résultat chiffré.`,
      `Jour 4: Section Expériences -> ${secondExperienceAction} Livrable: 2e preuve d'impact vérifiable.`,
      `Jour 5: Section Compétences -> aligne les mots-clés manquants (${focusA}) avec les offres cibles. Livrable: section compétences nettoyée.`,
      "Jour 6: Sections Langues/Certifications/Centres d'intérêt -> ajoute uniquement les éléments utiles au poste visé (niveau, preuve, contexte).",
      `Jour 7: Contrôle final -> relance l’analyse TalentFlow, vise +${dailyDelta * 7} points (de ${overall} à ${targetScore}) et corrige les derniers écarts.`,
    ];

    if (actions.length > 0) {
      plan[4] = `Jour 5: ${actions[0]}`;
    }
    if (evidence.length > 0) {
      plan[5] = `Jour 6: Utilise ces preuves dans ton CV et ton pitch: ${evidence.slice(0, 2).join(' ; ')}.`;
    }
    return plan;
  }

  private toStrings(value: any) {
    if (!Array.isArray(value)) return [];
    return value
      .map((item) => String(item ?? '').trim())
      .filter((item) => item.length > 0);
  }

  private toObjects(value: any): Record<string, any>[] {
    if (!Array.isArray(value)) return [];
    return value
      .filter((item) => item && typeof item === 'object' && !Array.isArray(item))
      .map((item) => item as Record<string, any>);
  }

  private toInt(value: any) {
    const parsed = Number(value ?? 0);
    if (!Number.isFinite(parsed)) return 0;
    return Math.max(0, Math.min(100, Math.round(parsed)));
  }

  private toFloat(value: any) {
    const parsed = Number(value ?? 0);
    if (!Number.isFinite(parsed)) return 0;
    return parsed;
  }

  private asObject(value: any): Record<string, any> | null {
    return value && typeof value === 'object' && !Array.isArray(value) ? value : null;
  }

  private async tryLoadLogo(pdf: PDFDocument): Promise<PDFImage | null> {
    for (const assetPath of REPORT_LOGO_CANDIDATES) {
      try {
        const bytes = await readFile(assetPath);
        return await pdf.embedPng(bytes);
      } catch {
        continue;
      }
    }
    return null;
  }

  private wrapText(text: string, font: PDFFont, size: number, width: number) {
    const safe = this.normalizeText(text);
    if (!safe) return [];

    const words = safe.split(' ');
    const lines: string[] = [];
    let current = '';

    for (const word of words) {
      const next = current ? `${current} ${word}` : word;
      if (font.widthOfTextAtSize(next, size) <= width) {
        current = next;
        continue;
      }

      if (current) {
        lines.push(current);
      }

      if (font.widthOfTextAtSize(word, size) <= width) {
        current = word;
        continue;
      }

      const chunks = this.breakLongWord(word, font, size, width);
      lines.push(...chunks.slice(0, -1));
      current = chunks[chunks.length - 1] || '';
    }

    if (current) {
      lines.push(current);
    }

    return lines;
  }

  private breakLongWord(word: string, font: PDFFont, size: number, width: number) {
    const chunks: string[] = [];
    let current = '';

    for (const char of word) {
      const next = `${current}${char}`;
      if (!current || font.widthOfTextAtSize(next, size) <= width) {
        current = next;
        continue;
      }
      chunks.push(current);
      current = char;
    }

    if (current) {
      chunks.push(current);
    }

    return chunks;
  }

  private measureBulletList(font: PDFFont, width: number, items: string[]) {
    const safeItems = items.length ? items.slice(0, 4) : ['Aucun point prioritaire remonté.'];
    return safeItems.reduce((height, item) => {
      const lines = this.wrapText(item, font, 9.5, width - 12);
      return height + Math.max(18, lines.length * 12 + 4);
    }, 0);
  }

  private normalizeText(value: string) {
    let text = String(value ?? '').replace(/\s+/g, ' ').trim();
    if (!text) return '';

    for (let i = 0; i < 2; i += 1) {
      if (!/[Ãâ€]/.test(text) && !text.includes('\uFFFD')) {
        break;
      }
      try {
        text = Buffer.from(text, 'latin1').toString('utf8');
      } catch {
        break;
      }
    }

    return text
      .replace(/\uFFFD/g, '')
      .replace(/[•·]/g, ' - ')
      .replace(/[“”]/g, '"')
      .replace(/[‘’]/g, "'")
      .replace(/[–—]/g, '-')
      .replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, '')
      .replace(/\s+/g, ' ')
      .trim();
  }
}

type ReportState = {
  pdf: PDFDocument;
  pages: PDFPage[];
  page: PDFPage;
  cursorY: number;
};
