import { appendFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname } from 'node:path';
import { randomUUID } from 'node:crypto';

export interface CvRlPolicyDecision {
  arm: string;
  cvThreshold: number;
  nonCvThreshold: number;
  decisionId: string;
}

type ArmState = {
  alpha: number;
  beta: number;
  uses: number;
  cvThreshold: number;
  nonCvThreshold: number;
};

type PolicyState = {
  version: number;
  updatedAt: string;
  arms: Record<string, ArmState>;
};

const DEFAULT_ARMS: Record<string, { cvThreshold: number; nonCvThreshold: number }> = {
  strict: { cvThreshold: 0.68, nonCvThreshold: 0.36 },
  balanced: { cvThreshold: 0.62, nonCvThreshold: 0.42 },
  permissive: { cvThreshold: 0.58, nonCvThreshold: 0.46 },
};

function envBool(name: string, defaultValue: boolean): boolean {
  const value = process.env[name];
  if (value == null) return defaultValue;
  return ['1', 'true', 'yes', 'on'].includes(value.trim().toLowerCase());
}

function policyPath(): string {
  return (
    String(process.env.CV_DOCUMENT_RL_POLICY_PATH || '').trim() ||
    '/app/runtime-data/gateway_cv_rl_policy_state.json'
  );
}

function eventsPath(): string {
  return (
    String(process.env.CV_DOCUMENT_RL_EVENTS_PATH || '').trim() ||
    '/app/runtime-data/gateway_cv_rl_policy_events.jsonl'
  );
}

function defaultState(): PolicyState {
  const arms: Record<string, ArmState> = {};
  for (const [name, thresholds] of Object.entries(DEFAULT_ARMS)) {
    arms[name] = {
      alpha: 1,
      beta: 1,
      uses: 0,
      cvThreshold: thresholds.cvThreshold,
      nonCvThreshold: thresholds.nonCvThreshold,
    };
  }
  return {
    version: 1,
    updatedAt: new Date().toISOString(),
    arms,
  };
}

function loadState(): PolicyState {
  const path = policyPath();
  if (!existsSync(path)) return defaultState();
  try {
    const raw = readFileSync(path, 'utf8');
    const parsed = JSON.parse(raw) as PolicyState;
    if (!parsed || typeof parsed !== 'object' || !parsed.arms || typeof parsed.arms !== 'object') {
      return defaultState();
    }
    return parsed;
  } catch {
    return defaultState();
  }
}

function saveState(state: PolicyState): void {
  const path = policyPath();
  mkdirSync(dirname(path), { recursive: true });
  state.updatedAt = new Date().toISOString();
  writeFileSync(path, JSON.stringify(state, null, 2), 'utf8');
}

function chooseArm(state: PolicyState): string {
  const armNames = Object.keys(state.arms);
  if (!armNames.length) return 'balanced';
  const epsilon = Number(process.env.CV_DOCUMENT_RL_EPSILON || '0.00');
  if (epsilon > 0 && Math.random() < epsilon) {
    return armNames[Math.floor(Math.random() * armNames.length)] ?? 'balanced';
  }

  let bestArm = 'balanced';
  let bestScore = Number.NEGATIVE_INFINITY;
  for (const [arm, payload] of Object.entries(state.arms)) {
    const alpha = Number(payload.alpha || 1);
    const beta = Number(payload.beta || 1);
    const score = alpha / Math.max(alpha + beta, 1e-9);
    if (score > bestScore || (Math.abs(score - bestScore) < 1e-9 && arm === 'balanced')) {
      bestScore = score;
      bestArm = arm;
    }
  }
  return bestArm;
}

export function selectCvRlPolicy(): CvRlPolicyDecision {
  if (!envBool('CV_DOCUMENT_RL_ENABLED', true)) {
    const baseline = DEFAULT_ARMS.balanced;
    return {
      arm: 'balanced',
      cvThreshold: baseline.cvThreshold,
      nonCvThreshold: baseline.nonCvThreshold,
      decisionId: `rl-off-${randomUUID().replace(/-/g, '')}`,
    };
  }

  const state = loadState();
  const arm = chooseArm(state);
  const payload = state.arms[arm] ?? {
    alpha: 1,
    beta: 1,
    uses: 0,
    cvThreshold: DEFAULT_ARMS.balanced.cvThreshold,
    nonCvThreshold: DEFAULT_ARMS.balanced.nonCvThreshold,
  };
  payload.uses = Number(payload.uses || 0) + 1;
  state.arms[arm] = payload;
  saveState(state);

  return {
    arm,
    cvThreshold: Number(payload.cvThreshold || DEFAULT_ARMS.balanced.cvThreshold),
    nonCvThreshold: Number(payload.nonCvThreshold || DEFAULT_ARMS.balanced.nonCvThreshold),
    decisionId: randomUUID().replace(/-/g, ''),
  };
}

export function logCvRlDecision(input: {
  decision: CvRlPolicyDecision;
  cvConfidence: number;
  documentKind: string;
  signalSummary: Record<string, number>;
}): void {
  if (!envBool('CV_DOCUMENT_RL_ENABLED', true)) return;
  try {
    const path = eventsPath();
    mkdirSync(dirname(path), { recursive: true });
    appendFileSync(
      path,
      `${JSON.stringify({
        timestamp: new Date().toISOString(),
        decisionId: input.decision.decisionId,
        arm: input.decision.arm,
        cvThreshold: input.decision.cvThreshold,
        nonCvThreshold: input.decision.nonCvThreshold,
        cvConfidence: input.cvConfidence,
        documentKind: input.documentKind,
        signalSummary: input.signalSummary,
      })}\n`,
      'utf8',
    );
  } catch {
    // best effort
  }
}

export function applyCvRlReward(arm: string, reward: number): void {
  if (!envBool('CV_DOCUMENT_RL_ENABLED', true)) return;
  const safeReward = Math.max(0, Math.min(1, Number(reward || 0)));
  const state = loadState();
  const payload = state.arms[arm] ?? {
    alpha: 1,
    beta: 1,
    uses: 0,
    cvThreshold: DEFAULT_ARMS.balanced.cvThreshold,
    nonCvThreshold: DEFAULT_ARMS.balanced.nonCvThreshold,
  };
  payload.alpha = Number(payload.alpha || 1) + safeReward;
  payload.beta = Number(payload.beta || 1) + (1 - safeReward);
  state.arms[arm] = payload;
  saveState(state);
}
