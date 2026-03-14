/**
 * Sprint 1: Epistemic Awareness Schema
 * 
 * Every memory entry has:
 * - confidence_score: 0.0-1.0 (how confident we are this is correct)
 * - created_at: when the fact was first recorded
 * - updated_at: last time this was verified/updated
 * - staleness_decay: automatic calculation of how outdated info is
 */

import { float, int32, string } from 'parquet-wasm'; // or LanceDB schema

// Schema v2.0 - with epistemic awareness
export const MemoryEntrySchema = {
  // Core identity
  id: string,           // UUID
  type: string,         // 'fact' | 'preference' | 'decision' | 'context' | 'prediction'
  
  // Content
  content: string,      // The actual memory
  embedding: number[],  // Vector for semantic search
  
  // EPISTEMIC FIELDS (Sprint 1)
  confidence_score: number,      // 0.0-1.0 (default: 0.7)
  evidence_sources: string[],    // Where did this come from?
  last_verified_at: number,      // Timestamp of last verification
  verification_count: number,    // How many times verified
  
  // Metadata
  created_at: number,
  updated_at: number,
  tags: string[],
  
  // Access tracking
  accessed_at: number,
  access_count: number,
};

/**
 * Staleness Decay Function
 * 
 * Different memory types decay at different rates:
 * - facts: slow decay (1% per day)
 * - preferences: medium decay (2% per day) 
 * - decisions: slow (decisions should persist)
 * - context: fast decay (5% per day - situational)
 * - predictions: tracked separately for outcome attribution
 */

const DECAY_RATES = {
  fact: 0.01,        // 1% per day
  preference: 0.02,  // 2% per day
  decision: 0.005,   // 0.5% per day (decisions persist)
  context: 0.05,     // 5% per day (situational)
  prediction: 0.0,   // No decay - tracked for outcomes
};

const CONFIDENCE_THRESHOLD = 0.6; // Below this, don't act

/**
 * Calculate current confidence with staleness decay
 */
export function calculateEffectiveConfidence(
  entry: MemoryEntry,
  now: number = Date.now()
): number {
  const ageInDays = (now - entry.last_verified_at) / (1000 * 60 * 60 * 24);
  const decayRate = DECAY_RATES[entry.type as keyof typeof DECAY_RATES] || 0.01;
  
  // Compound decay: confidence * (1 - rate)^age
  const effectiveConfidence = entry.confidence_score * Math.pow(1 - decayRate, ageInDays);
  
  return Math.max(0, effectiveConfidence);
}

/**
 * Epistemic check - gates action when confidence is below threshold
 */
export function epistemicCheck(entry: MemoryEntry): {
  canAct: boolean;
  confidence: number;
  warnings: string[];
} {
  const effectiveConfidence = calculateEffectiveConfidence(entry);
  
  const warnings: string[] = [];
  
  if (effectiveConfidence < CONFIDENCE_THRESHOLD) {
    warnings.push(`Confidence ${effectiveConfidence.toFixed(2)} below threshold ${CONFIDENCE_THRESHOLD}`);
  }
  
  if (effectiveConfidence < 0.3) {
    warnings.push('Low confidence - recommend verification before use');
  }
  
  // Check for stale data
  const ageInDays = (Date.now() - entry.last_verified_at) / (1000 * 60 * 60 * 24);
  if (ageInDays > 30) {
    warnings.push('Data is over 30 days old');
  }
  
  return {
    canAct: effectiveConfidence >= CONFIDENCE_THRESHOLD,
    confidence: effectiveConfidence,
    warnings,
  };
}

/**
 * Query memories with epistemic filtering
 */
export async function queryWithEpistemicFilter(
  db: LanceDB,
  query: string,
  minConfidence: number = CONFIDENCE_THRESHOLD
): Promise<MemoryEntry[]> {
  // Semantic search first
  const results = await db.semanticSearch(query, { limit: 10 });
  
  // Then filter by effective confidence
  return results
    .map(entry => ({
      ...entry,
      effectiveConfidence: calculateEffectiveConfidence(entry),
    }))
    .filter(entry => entry.effectiveConfidence >= minConfidence);
}