export const CV_JOB_STAGES = {
  QUEUED: 'QUEUED',
  EXTRACT_TEXT: 'EXTRACT_TEXT',
  OCR_IF_NEEDED: 'OCR_IF_NEEDED',
  ANALYZE_PROFILE: 'ANALYZE_PROFILE',
  SEARCH_MATCHING: 'SEARCH_MATCHING',
  LLM_SYNTHESIS: 'LLM_SYNTHESIS',
  SAVE_HISTORY: 'SAVE_HISTORY',
  COMPLETED: 'COMPLETED',
  FAILED: 'FAILED',
} as const;

const LABELS: Record<string, string> = {
  QUEUED: 'En file d’attente',
  EXTRACT_TEXT: 'Extraction du texte CV',
  OCR_IF_NEEDED: 'OCR si nécessaire',
  ANALYZE_PROFILE: 'Analyse du profil',
  SEARCH_MATCHING: 'Recherche des offres',
  LLM_SYNTHESIS: 'Synthèse finale',
  SAVE_HISTORY: 'Sauvegarde de l’historique',
  COMPLETED: 'Terminé',
  FAILED: 'Échec',
};

const ETA: Record<string, string> = {
  QUEUED: 'Démarrage imminent',
  EXTRACT_TEXT: '~5-15s',
  OCR_IF_NEEDED: '~10-35s',
  ANALYZE_PROFILE: '~2-6s',
  SEARCH_MATCHING: '~2-8s',
  LLM_SYNTHESIS: '~4-14s',
  SAVE_HISTORY: 'Finalisation',
  COMPLETED: 'Résultat prêt',
  FAILED: 'Action requise',
};

export function stageLabel(stage: string): string {
  return LABELS[stage] ?? stage;
}

export function etaHint(stage: string): string {
  return ETA[stage] ?? 'En cours';
}
