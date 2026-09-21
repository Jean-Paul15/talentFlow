import { appendFile, mkdir } from 'node:fs/promises';
import { dirname } from 'node:path';
import {
  applyCvRlReward,
  logCvRlDecision,
  selectCvRlPolicy,
} from './cv-rl-agent';

export type CvDocumentKind = 'cv' | 'non_cv' | 'ambiguous';

export interface CvDocumentAssessment {
  documentKind: CvDocumentKind;
  cvConfidence: number;
  userMessage: string;
  policyArm?: string;
  policyDecisionId?: string;
  signalSummary: {
    contactSignals: number;
    sectionSignals: number;
    chronologySignals: number;
    experienceSignals: number;
    roleSignals: number;
    educationSignals: number;
    candidateHintSignals: number;
    skillSignals: number;
    negativeSignals: number;
    academicProgramSignals: number;
    jobPostingSignals: number;
  };
}

const SECTION_MARKERS = [
  'curriculum vitae',
  'curriculum',
  'profil',
  'profile',
  'resume',
  'summary',
  'objective',
  'experience',
  'professional experience',
  'work history',
  'employment history',
  'formation',
  'education',
  'academic background',
  'etudes',
  'skills',
  'technical skills',
  'competences',
  'competencies',
  'projects',
  'project experience',
  'projets',
  'certifications',
  'languages',
  'langues',
  'references',
  'habilidades',
  'experiencia',
  'educacion',
];

const EXPERIENCE_MARKERS = [
  'work experience',
  'professional experience',
  'employment history',
  'career history',
  'career summary',
  'experience professionnelle',
  'responsibilities',
  'missions',
  'achievements',
  'employment',
  'employer',
  'organization',
  'organisation',
  'company',
  'entreprise',
  'poste',
  'position',
  'stage',
  'internship',
  'freelance',
  'consulting',
  'alternance',
  'cdd',
  'cdi',
  'present',
  'current',
];

const ROLE_MARKERS = [
  'manager',
  'assistant',
  'consultant',
  'engineer',
  'ingenieur',
  'developer',
  'developpeur',
  'analyst',
  'analyste',
  'teacher',
  'enseignant',
  'accountant',
  'comptable',
  'sales',
  'commercial',
  'nurse',
  'designer',
  'technician',
  'technicien',
  'coordinator',
  'supervisor',
  'specialist',
  'officer',
];

const EDUCATION_MARKERS = [
  'master',
  'licence',
  'bachelor',
  'doctorat',
  'phd',
  'bts',
  'dut',
  'bac+',
  'ingenieur',
  'university',
  'universite',
  'faculty',
  'institute',
  'college',
  'degree',
  'diploma',
  'diplome',
  'certificate',
  'certificat',
  'school',
  'ecole',
  'lycee',
  'high school',
];

const SKILL_MARKERS = [
  'excel',
  'word',
  'powerpoint',
  'python',
  'dart',
  'java',
  'javascript',
  'node',
  'node.js',
  'typescript',
  'react',
  'flutter',
  'sql',
  'mysql',
  'postgresql',
  'mongodb',
  'git',
  'html',
  'css',
  'php',
  'docker',
  'linux',
  'communication',
  'leadership',
  'gestion',
  'analyse',
  'salesforce',
  'accounting',
];

const COVER_LETTER_MARKERS = [
  'madame',
  'monsieur',
  'cordialement',
  'objet',
  'je souhaite',
  'je vous adresse',
  'veuillez agreer',
];

const NEGATIVE_MARKERS = [
  'lorem ipsum',
  'chapitre',
  'cours',
  'exercice',
  'facture',
  'invoice',
  'conditions generales',
  'politique de confidentialite',
  'privacy policy',
  'cookies',
  'newsletter',
  'article de blog',
  'blog article',
  'communique de presse',
  'press release',
  'formation certifiante',
  'cliquez pour lire',
  'click to read',
  'urgent offre de formation',
  'terms of service',
];

const ACADEMIC_PROGRAM_MARKERS = [
  'semestre',
  'ue',
  'ecue',
  'credits',
  'credit',
  'maquette pedagogique',
  'volume horaire',
  'cours magistral',
  'travaux diriges',
  'travaux pratiques',
  'syllabus',
  'prerequis',
  'pre requis',
  'objectif pedagogique',
  'objectifs pedagogiques',
  'modalites d evaluation',
  'evaluation continue',
  'programme de cours',
  'filiere',
];

const JOB_POSTING_MARKERS = [
  'offre d emploi',
  'nous recrutons',
  'profil recherche',
  'postulez',
  'merci d envoyer votre cv',
  'mission principale',
  'candidature a envoyer',
];

const CITY_MARKERS = [
  'lome',
  'abidjan',
  'accra',
  'cotonou',
  'dakar',
  'lagos',
  'paris',
  'remote',
  'hybride',
  'hybrid',
];

const CANDIDATE_HINT_MARKERS = [
  'candidature',
  'application',
  'open to',
  'open to opportunities',
  'available for',
  'available',
  'disponible',
  'a la recherche',
  'looking for',
  'seeking',
  'profil',
  'profile',
  'about me',
  'based in',
];

function foldText(text: string): string {
  return String(text || '')
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .trim();
}

function countMarkers(haystack: string, markers: readonly string[]): number {
  const hasMarker = (marker: string): boolean => {
    const foldedMarker = foldText(marker);
    if (!foldedMarker) return false;
    if (foldedMarker.includes(' ')) {
      return haystack.includes(foldedMarker);
    }
    const escaped = foldedMarker.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return new RegExp(`\\b${escaped}\\b`, 'u').test(haystack);
  };

  let matches = 0;
  for (const marker of markers) {
    if (hasMarker(marker)) {
      matches += 1;
    }
  }
  return matches;
}

function uniqueYearMatches(text: string): number {
  const years = new Set(
    (text.match(/\b(19\d{2}|20\d{2})\b/g) || []).map((value) => value.trim()),
  );
  return years.size;
}

function weirdRatio(text: string): number {
  if (!text) return 1;
  const weird = (text.match(/[^\p{L}\p{N}\s.,;:!?'"()%\-\/@+#]/gu) || []).length;
  return weird / Math.max(text.length, 1);
}

function clamp(value: number, min = 0, max = 1): number {
  return Math.max(min, Math.min(max, value));
}

function messageFor(kind: CvDocumentKind): string {
  if (kind === 'cv') {
    return 'CV import\u00e9. Le document semble exploitable pour l\u2019analyse.';
  }
  if (kind === 'ambiguous') {
    return 'Le document a \u00e9t\u00e9 lu, mais sa structure reste atypique. Une v\u00e9rification plus stricte sera appliqu\u00e9e avant le diagnostic.';
  }
  return 'Ce fichier ne ressemble pas \u00e0 un CV exploitable. Importe un CV avec au moins ton profil, tes exp\u00e9riences ou tes comp\u00e9tences.';
}

export function assessCvText(rawText: string): CvDocumentAssessment {
  const original = String(rawText || '').replace(/\u0000/g, ' ').trim();
  const normalized = foldText(original);
  const words = original.split(/\s+/).filter(Boolean).length;
  const lines = original.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  const bullets = (original.match(/^[\s\-•*]/gm) || []).length;

  const contactSignals =
    (/\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b/i.test(original) ? 1 : 0) +
    (/(?:\+?\d[\d\s().-]{7,}\d)/.test(original) ? 1 : 0) +
    (/(linkedin|github|portfolio|behance|website)/i.test(original) ? 1 : 0) +
    (countMarkers(normalized, CITY_MARKERS) > 0 ? 1 : 0);
  const sectionSignals = countMarkers(normalized, SECTION_MARKERS);
  let chronologySignals = Math.min(4, uniqueYearMatches(original));
  if (/\b\d{1,2}\s*(?:ans|years?)\b/i.test(normalized)) {
    chronologySignals = Math.max(chronologySignals, 1);
  }
  const experienceSignals = countMarkers(normalized, EXPERIENCE_MARKERS);
  const roleSignals = countMarkers(normalized, ROLE_MARKERS);
  const educationSignals = countMarkers(normalized, EDUCATION_MARKERS);
  const candidateHintSignals = countMarkers(normalized, CANDIDATE_HINT_MARKERS);
  const skillSignals = countMarkers(normalized, SKILL_MARKERS);
  const coverLetterSignals = countMarkers(normalized, COVER_LETTER_MARKERS);
  const negativeSignals = countMarkers(normalized, NEGATIVE_MARKERS);
  const academicProgramSignals = countMarkers(normalized, ACADEMIC_PROGRAM_MARKERS);
  const jobPostingSignals = countMarkers(normalized, JOB_POSTING_MARKERS);

  let score = 0.05;
  score += Math.min(0.22, contactSignals * 0.07);
  score += Math.min(0.24, sectionSignals * 0.05);
  score += Math.min(0.18, chronologySignals * 0.04);
  score += Math.min(0.16, experienceSignals * 0.04);
  score += Math.min(0.12, educationSignals * 0.04);
  score += Math.min(0.08, roleSignals * 0.03);
  score += Math.min(0.06, skillSignals * 0.01);

  if (words >= 180) {
    score += 0.08;
  } else if (words >= 90) {
    score += 0.05;
  } else if (words >= 45) {
    score += 0.02;
  } else {
    score -= 0.14;
  }

  if (lines.length >= 6 || bullets >= 3) {
    score += 0.05;
  }

  if (weirdRatio(original) > 0.06) {
    score -= 0.12;
  }

  score -= Math.min(0.40, negativeSignals * 0.12);
  score -= Math.min(0.42, academicProgramSignals * 0.08);
  score -= Math.min(0.35, jobPostingSignals * 0.10);

  if (
    academicProgramSignals >= 3 &&
    experienceSignals === 0 &&
    candidateHintSignals === 0 &&
    roleSignals === 0
  ) {
    score -= 0.30;
  }

  if (
    jobPostingSignals >= 2 &&
    candidateHintSignals === 0 &&
    contactSignals <= 1
  ) {
    score -= 0.30;
  }

  if (
    negativeSignals === 0 &&
    words >= 20 &&
    contactSignals >= 2 &&
    (roleSignals >= 1 || skillSignals >= 2)
  ) {
    score = Math.max(score, 0.45);
  }

  if (
    negativeSignals === 0 &&
    words >= 20 &&
    sectionSignals >= 1 &&
    contactSignals >= 1
  ) {
    score = Math.max(score, 0.44);
  }

  if (
    negativeSignals === 0 &&
    words >= 20 &&
    candidateHintSignals >= 1 &&
    (contactSignals >= 1 || roleSignals >= 1)
  ) {
    score = Math.max(score, 0.43);
  }

  if (
    negativeSignals === 0 &&
    words >= 12 &&
    contactSignals >= 1 &&
    skillSignals >= 3
  ) {
    score = Math.max(score, 0.43);
  }

  if (
    negativeSignals === 0 &&
    words >= 12 &&
    roleSignals >= 1 &&
    candidateHintSignals >= 1
  ) {
    score = Math.max(score, 0.42);
  }

  if (
    negativeSignals === 0 &&
    words >= 10 &&
    contactSignals >= 1 &&
    (sectionSignals >= 1 || candidateHintSignals >= 1)
  ) {
    score = Math.max(score, 0.42);
  }

  if (
    negativeSignals === 0 &&
    words >= 8 &&
    roleSignals >= 1 &&
    chronologySignals >= 1 &&
    candidateHintSignals >= 1
  ) {
    score = Math.max(score, 0.42);
  }

  // Compact resumes (student/junior profiles) should still pass as CV when
  // they keep core CV structure and concrete skills.
  if (
    negativeSignals === 0 &&
    words >= 20 &&
    sectionSignals >= 2 &&
    contactSignals >= 1 &&
    (skillSignals >= 2 || educationSignals >= 1) &&
    (educationSignals >= 1 || experienceSignals >= 1 || roleSignals >= 1)
  ) {
    score = Math.max(score, 0.63);
  }

  // Keep short cover letters in the ambiguous lane instead of hard rejection.
  if (
    negativeSignals === 0 &&
    words >= 30 &&
    words <= 180 &&
    candidateHintSignals >= 1 &&
    (contactSignals >= 1 || roleSignals >= 1) &&
    sectionSignals === 0 &&
    chronologySignals <= 1
  ) {
    score = Math.max(score, 0.46);
  }

  // Keep short motivation letters (often role-focused but without CV sections)
  // in ambiguous instead of hard rejection.
  if (
    negativeSignals === 0 &&
    words >= 24 &&
    words <= 220 &&
    candidateHintSignals >= 1 &&
    roleSignals >= 1 &&
    sectionSignals <= 1 &&
    chronologySignals <= 1
  ) {
    score = Math.max(score, 0.44);
  }

  if (
    negativeSignals === 0 &&
    words >= 20 &&
    words <= 240 &&
    coverLetterSignals >= 2 &&
    roleSignals >= 1 &&
    sectionSignals <= 1 &&
    chronologySignals <= 1
  ) {
    score = Math.max(score, 0.45);
  }

  if (
    negativeSignals === 0 &&
    words >= 20 &&
    words <= 240 &&
    coverLetterSignals >= 2 &&
    candidateHintSignals >= 1 &&
    chronologySignals <= 1
  ) {
    score = Math.max(score, 0.44);
  }

  if (
    contactSignals === 0 &&
    sectionSignals < 2 &&
    chronologySignals === 0 &&
    experienceSignals === 0
  ) {
    score -= 0.20;
  }

  let cvConfidence = Number(clamp(score).toFixed(3));
  const policy = selectCvRlPolicy();
  let documentKind: CvDocumentKind = 'ambiguous';
  if (cvConfidence >= policy.cvThreshold) {
    documentKind = 'cv';
  } else if (cvConfidence < policy.nonCvThreshold) {
    documentKind = 'non_cv';
  }

  if (
    documentKind === 'cv' &&
    cvConfidence < 0.80 &&
    contactSignals === 0 &&
    candidateHintSignals === 0 &&
    experienceSignals === 0
  ) {
    documentKind = 'ambiguous';
    cvConfidence = Number(Math.min(cvConfidence, 0.61).toFixed(3));
  }

  if (
    documentKind === 'cv' &&
    ((academicProgramSignals >= 3 && experienceSignals === 0) ||
      (jobPostingSignals >= 2 && candidateHintSignals === 0))
  ) {
    documentKind = 'non_cv';
    cvConfidence = Number(Math.min(cvConfidence, 0.39).toFixed(3));
  }

  const reward = (() => {
    if (documentKind === 'cv') {
      if (sectionSignals >= 2 && (chronologySignals >= 1 || experienceSignals >= 1)) return 0.92;
      return 0.70;
    }
    if (documentKind === 'non_cv') {
      if (negativeSignals >= 1 && sectionSignals === 0) return 0.88;
      return 0.60;
    }
    return 0.65;
  })();
  applyCvRlReward(policy.arm, reward);

  const assessment: CvDocumentAssessment = {
    documentKind,
    cvConfidence,
    userMessage: messageFor(documentKind),
    policyArm: policy.arm,
    policyDecisionId: policy.decisionId,
    signalSummary: {
      contactSignals,
      sectionSignals,
      chronologySignals,
      experienceSignals,
      roleSignals,
      educationSignals,
      candidateHintSignals,
      skillSignals,
      negativeSignals,
      academicProgramSignals,
      jobPostingSignals,
    },
  };
  logCvRlDecision({
    decision: policy,
    cvConfidence: assessment.cvConfidence,
    documentKind: assessment.documentKind,
    signalSummary: assessment.signalSummary,
  });
  return assessment;
}

export async function captureCvAssessmentSample(
  rawText: string,
  assessment: CvDocumentAssessment,
): Promise<void> {
  const enabled = String(process.env.CV_DOCUMENT_CAPTURE_ENABLED || '').trim().toLowerCase();
  const outputPath = String(process.env.CV_DOCUMENT_CAPTURE_PATH || '').trim();
  if (!outputPath || (enabled !== 'true' && enabled !== '1' && enabled !== 'yes')) {
    return;
  }

  try {
    await mkdir(dirname(outputPath), { recursive: true });
    const preview = rawText.replace(/\s+/g, ' ').slice(0, 320);
    const record = JSON.stringify({
      timestamp: new Date().toISOString(),
      documentKind: assessment.documentKind,
      cvConfidence: assessment.cvConfidence,
      signalSummary: assessment.signalSummary,
      preview,
    });
    await appendFile(outputPath, `${record}\n`, 'utf8');
  } catch {
    // Best effort only.
  }
}
