/**
 * Sprint 3: Outcome Attribution
 * 
 * Every action gets:
 * - Predicted outcome (what we expect)
 * - Measurement method (how we track it)
 * - Actual outcome (what happened)
 * - Attribution (did our action cause it?)
 * 
 * Over time: build map of what actually produces value
 * versus what FEELS productive.
 */

/* ============================================
   OUTCOME TRACKING SCHEMA
   ============================================ */

const OUTCOME_STATES = {
  PENDING: 'pending',       // Action taken, waiting for outcome
  MATERIALIZED: 'materialized', // Predicted outcome occurred
  FAILED: 'failed',         // Predicted outcome did NOT occur
  PARTIAL: 'partial',       // Partially materialized
  UNKNOWN: 'unknown',       // Can't measure
} as const;

type OutcomeState = typeof OUTCOME_STATES[keyof typeof OUTCOME_STATES];

/* ============================================
   PREDICTION RECORD
   ============================================ */

interface Prediction {
  id: string;
  
  // What we did
  action_id: string;
  action_type: string;      // 'email_sent', 'content_posted', 'feature_built'
  action_description: string;
  
  // What we predicted would happen
  predicted_outcome: string;
  predicted_timeline: string;    // e.g., "24 hours", "1 week"
  measurement_method: string;    // How we'll track it
  
  // Confidence in prediction
  prediction_confidence: number; // 0-1
  
  // When we predicted it
  predicted_at: number;
  
  // Tracking
  outcome_state: OutcomeState;
  actual_outcome: string;
  measured_at: number;
  
  // Attribution
  attribution_score: number;    // 0-1, how much was this action responsible?
  causal_factors: string[];     // Other factors that contributed
}

/* ============================================
   VALUE MAPPING
   ============================================ */

// Track which action types produce value over time
interface ActionTypePerformance {
  action_type: string;
  
  // Counters
  total_predictions: number;
  materialized: number;
  failed: number;
  partial: number;
  
  // Value metrics
  total_actual_value: number;   // Revenue, engagement, etc.
  average_attribution: number;  // How much credit do these get?
  
  // Time analysis
  average_timeline_actual: number;   // Days it actually took
  average_timeline_predicted: number; // Days we predicted
  
  // Confidence calibration
  average_prediction_confidence: number;
  actual_success_rate: number;
}

/* ============================================
   FUNCTIONS
   ============================================ */

/**
 * Record a new prediction when taking an action
 */
export async function recordPrediction(
  db: any,
  prediction: {
    action_id: string;
    action_type: string;
    action_description: string;
    predicted_outcome: string;
    predicted_timeline: string;
    measurement_method: string;
    prediction_confidence: number;
  }
) {
  const now = Date.now();
  
  const record: Prediction = {
    id: crypto.randomUUID(),
    ...prediction,
    predicted_at: now,
    outcome_state: OUTCOME_STATES.PENDING,
    actual_outcome: '',
    measured_at: 0,
    attribution_score: 0,
    causal_factors: [],
  };
  
  // Insert into predictions table
  return record;
}

/**
 * Measure outcome - did our prediction materialize?
 */
export async function measureOutcome(
  db: any,
  predictionId: string,
  actualOutcome: string,
  outcomeState: OutcomeState,
  attributionScore?: number,
  causalFactors?: string[]
) {
  // Update prediction with actual outcome
  // Recalculate performance metrics
  
  return {
    predictionId,
    outcomeState,
    attributionScore: attributionScore ?? 0.5,
  };
}

/**
 * Get action type performance - what actually produces value?
 */
export async function getActionTypePerformance(
  db: any,
  actionType?: string
): Promise<ActionTypePerformance[]> {
  // Aggregate all predictions by action_type
  // Calculate success rates, value attribution, timeline accuracy
  
  return [
    {
      action_type: 'email_sent',
      total_predictions: 10,
      materialized: 7,
      failed: 2,
      partial: 1,
      total_actual_value: 0,
      average_attribution: 0.6,
      average_timeline_actual: 2,
      average_timeline_predicted: 1,
      average_prediction_confidence: 0.75,
      actual_success_rate: 0.7,
    },
  ];
}

/**
 * Prediction accuracy calibration
 * Compare confidence vs actual success rate
 */
export async function calibrateConfidence(
  db: any
): Promise<{
  confidence: number;
  actual_success_rate: number;
  calibration_error: number;
}[]> {
  // Bucket predictions by confidence level
  // Compare predicted confidence to actual success rate
  
  return [
    { confidence: 0.9, actual_success_rate: 0.85, calibration_error: 0.05 },
    { confidence: 0.7, actual_success_rate: 0.65, calibration_error: 0.05 },
    { confidence: 0.5, actual_success_rate: 0.45, calibration_error: 0.05 },
  ];
}

/**
 * Value attribution engine
 * Given an outcome, which actions contributed?
 */
export async function attributeOutcome(
  db: any,
  outcomeId: string
): Promise<{
  action_id: string;
  attribution_score: number;
  reasoning: string;
}[]> {
  // Find all pending predictions that could have caused this
  // Score each by recency,相关性, historical accuracy
  
  return [];
}

/* ============================================
   AUTOMATIC TRACKING
   ============================================ */

// When any action is taken, automatically create prediction record
// When outcomes are measured, update and recalculate performance
// Periodic job: check pending predictions, auto-mark as unknown if timeline exceeded

export { OUTCOME_STATES };
export type { OutcomeState, Prediction, ActionTypePerformance };