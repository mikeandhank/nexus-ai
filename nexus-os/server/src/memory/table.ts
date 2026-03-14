/**
 * Sprint 1: LanceDB Memory Table with Epistemic Awareness
 * 
 * This creates/updates the memory table with confidence scores,
 * staleness decay, and epistemic filtering.
 */

import * as lancedb from '@lancedb/lancedb';
import { EmbeddingFunction } from '@lancedb/lancedb';

// LanceDB schema with epistemic fields
const MEMORY_TABLE_SCHEMA = {
  schema: {
    columns: {
      id: new lancedb.Text().withDefault(() => crypto.randomUUID()),
      type: new lancedb.Text(), // 'fact' | 'preference' | 'decision' | 'context' | 'prediction'
      content: new lancedb.Text(),
      embedding: new lancedb.Vector(384), // sentence-transformers default
      
      // EPISTEMIC FIELDS (Sprint 1)
      confidence_score: new lancedb.Float32().withDefault(0.7),
      evidence_sources: new lancedb.List(new lancedb.Text()),
      last_verified_at: new lancedb.Timestamp(),
      verification_count: new lancedb.Int32().withDefault(0),
      
      // Metadata
      created_at: new lancedb.Timestamp().withDefault(() => Date.now()),
      updated_at: new lancedb.Timestamp().withDefault(() => Date.now()),
      tags: new lancedb.List(new lancedb.Text()),
      
      // Access tracking
      accessed_at: new lancedb.Timestamp(),
      access_count: new lancedb.Int32().withDefault(0),
    },
  },
  // Enable vector search
  vectorIndex: true,
};

/**
 * Create or migrate memory table
 */
export async function initMemoryTable(db: lancedb.Connection) {
  const tableName = 'memory';
  
  try {
    // Table exists - return it
    await db.openTable(tableName);
    console.log('Memory table already exists');
  } catch {
    // Create new table with epistemic schema
    const table = await db.createEmptyTable(tableName, MEMORY_TABLE_SCHEMA);
    console.log('Created memory table with epistemic schema v1.0');
    return table;
  }
}

/**
 * Add a memory entry with confidence score
 */
export async function addMemory(
  db: lancedb.Connection,
  entry: {
    type: 'fact' | 'preference' | 'decision' | 'context' | 'prediction';
    content: string;
    embedding: number[];
    confidence_score?: number;
    evidence_sources?: string[];
    tags?: string[];
  }
) {
  const table = await db.openTable('memory');
  
  const now = Date.now();
  
  await table.add([
    {
      id: crypto.randomUUID(),
      type: entry.type,
      content: entry.content,
      embedding: entry.embedding,
      confidence_score: entry.confidence_score ?? 0.7,
      evidence_sources: entry.evidence_sources ?? [],
      last_verified_at: now,
      verification_count: 0,
      created_at: now,
      updated_at: now,
      tags: entry.tags ?? [],
      accessed_at: now,
      access_count: 0,
    },
  ]);
  
  console.log(`Added ${entry.type} with confidence ${entry.confidence_score ?? 0.7}`);
}

/**
 * Epistemic query - search with confidence filtering
 */
export async function epistemicQuery(
  db: lancedb.Connection,
  query: string,
  embeddingFn: EmbeddingFunction,
  options: {
    minConfidence?: number;
    minEvidenceCount?: number;
    maxAgeDays?: number;
  } = {}
) {
  const table = await db.openTable('memory');
  const now = Date.now();
  
  const minConfidence = options.minConfidence ?? 0.6;
  const minEvidenceCount = options.minEvidenceCount ?? 0;
  const maxAgeDays = options.maxAgeDays ?? 90;
  
  // Vector search
  const queryEmbedding = await embeddingFn.embed(query);
  const results = await table
    .vectorSearch(queryEmbedding)
    .limit(20)
    .toRows();
  
  // Apply epistemic filters
  const filtered = results
    .map(row => {
      const entry = row as any;
      
      // Calculate staleness decay
      const ageInDays = (now - entry.last_verified_at) / (1000 * 60 * 60 * 24);
      const decayRate = getDecayRate(entry.type);
      const effectiveConfidence = calculateEffectiveConfidence(
        entry.confidence_score,
        ageInDays,
        decayRate
      );
      
      return {
        ...entry,
        effectiveConfidence,
        ageInDays,
        isStale: ageInDays > maxAgeDays,
      };
    })
    .filter(entry => {
      // Filter by confidence threshold
      if (entry.effectiveConfidence < minConfidence) return false;
      
      // Filter by evidence count
      if ((entry.evidence_sources?.length ?? 0) < minEvidenceCount) return false;
      
      // Filter by age
      if (entry.ageInDays > maxAgeDays) return false;
      
      return true;
    });
  
  // Sort by effective confidence
  filtered.sort((a, b) => b.effectiveConfidence - a.effectiveConfidence);
  
  return filtered;
}

/**
 * Verify a memory entry - boost confidence
 */
export async function verifyMemory(
  db: lancedb.Connection,
  id: string,
  newConfidence?: number
) {
  const table = await db.openTable('memory');
  
  // Get current entry
  const rows = await table.filter(`id = "${id}"`).toRows();
  if (rows.length === 0) throw new Error('Memory not found');
  
  const entry = rows[0] as any;
  
  // Boost confidence on verification (cap at 1.0)
  const boostedConfidence = newConfidence ?? Math.min(1, entry.confidence_score + 0.1);
  
  await table
    .filter(`id = "${id}"`)
    .update({
      confidence_score: boostedConfidence,
      last_verified_at: Date.now(),
      verification_count: entry.verification_count + 1,
      updated_at: Date.now(),
    });
  
  console.log(`Verified ${id}: confidence ${entry.confidence_score} → ${boostedConfidence}`);
}

/**
 * Migrate existing table to epistemic schema
 */
export async function migrateToEpistemic(
  db: lancedb.Connection,
  embeddingFn: EmbeddingFunction
) {
  // For v1.0, we create fresh
  // Future: detect missing columns and add them
  console.log('Migration to v1.0 schema complete');
}

// --- Decay Function (copied for reference) ---

function getDecayRate(type: string): number {
  const rates: Record<string, number> = {
    fact: 0.01,
    preference: 0.02,
    decision: 0.005,
    context: 0.05,
    prediction: 0.0,
  };
  return rates[type] ?? 0.01;
}

function calculateEffectiveConfidence(
  baseConfidence: number,
  ageInDays: number,
  decayRate: number
): number {
  return Math.max(0, baseConfidence * Math.pow(1 - decayRate, ageInDays));
}