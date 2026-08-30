export type FailureReason = 
  | 'UPI_TIMEOUT'
  | 'BANK_DECLINED'
  | 'INSUFFICIENT_FUNDS'
  | 'NETWORK_ERROR'
  | 'PAYMENT_METHOD_ERROR'
  | 'UNKNOWN';

export type PaymentMethod = 'UPI' | 'CARD' | 'NETBANKING' | 'WALLET';

export type TransactionStatus = 
  | 'FAILED'
  | 'RECOVERY_PENDING'
  | 'APPROVAL_REQUIRED'
  | 'RECOVERED'
  | 'STOPPED'
  | 'PERMANENTLY_FAILED';

export type RecoveryActionType = 
  | 'RETRY_PAYMENT'
  | 'PAYMENT_LINK'
  | 'ALTERNATIVE_PAYMENT_METHOD'
  | 'REMINDER'
  | 'HUMAN_ESCALATION'
  | 'STOP';

export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH';

export interface Customer {
  id: string;
  name: string;
  email: string;
  phone: string;
  lifetime_value: number;
  successful_payments_count: number;
  failed_payments_count: number;
  risk_score: number;
  created_at: string;
}

export interface AIAgentAnalysis {
  diagnosis: string;
  recovery_probability: number;
  recommended_action: RecoveryActionType;
  risk_level: RiskLevel;
  reason: string;
  requires_human_approval: boolean;
  model_used?: string;
  fallback_used?: boolean;
}

export interface PolicyDecision {
  allowed: boolean;
  action: RecoveryActionType;
  requires_human_approval: boolean;
  reasons: string[];
  rules_evaluated: {
    rule_id: string;
    description: string;
    passed: boolean;
    reason?: string;
  }[];
}

export interface RecoveryExecutionResult {
  execution_id: string;
  transaction_id: string;
  action_type: RecoveryActionType;
  status: 'SUCCESS' | 'FAILED' | 'PENDING_APPROVAL' | 'REJECTED' | 'SKIPPED';
  recovered_amount: number;
  razorpay_order_id?: string;
  razorpay_payment_link?: string;
  mode: 'TEST_MODE' | 'SIMULATION_MODE';
  executed_at: string;
  message: string;
}

export interface AuditEvent {
  id: string;
  timestamp: string;
  transaction_id?: string;
  event_type: 
    | 'PAYMENT_FAILED_DETECTED'
    | 'AI_ANALYSIS_COMPLETED'
    | 'POLICY_EVALUATED'
    | 'HUMAN_APPROVAL_REQUESTED'
    | 'HUMAN_APPROVED'
    | 'HUMAN_REJECTED'
    | 'RECOVERY_ACTION_TRIGGERED'
    | 'PAYMENT_RECOVERED'
    | 'PAYMENT_RECOVERY_FAILED'
    | 'RECOVERY_STOPPED'
    | 'SIMULATION_BATCH_EXECUTED';
  actor: 'SYSTEM' | 'AI_AGENT' | 'POLICY_ENGINE' | 'HUMAN_OPERATOR' | 'RAZORPAY_GATEWAY';
  decision?: string;
  details: Record<string, any>;
}

export interface Transaction {
  id: string;
  customer_id: string;
  customer_name?: string;
  customer_email?: string;
  amount: number;
  currency: string;
  status: TransactionStatus;
  payment_method: PaymentMethod;
  failure_reason: FailureReason;
  error_code?: string;
  customer_lifetime_value?: number;
  previous_successful_payments?: number;
  previous_failed_payments?: number;
  previous_recovery_attempts?: number;
  retry_count: number;
  max_retries: number;
  created_at: string;
  updated_at: string;
  last_recovery_attempt_at?: string;
  razorpay_order_id?: string;
  razorpay_payment_id?: string;
  razorpay_payment_link?: string;
  ai_analysis?: AIAgentAnalysis;
  policy_decision?: PolicyDecision;
  recovery_result?: RecoveryExecutionResult;
  customer?: Customer;
  recovery_actions?: any[];
  audit_events?: AuditEvent[];
}

export interface DashboardMetrics {
  revenue_at_risk: number;
  revenue_recovered: number;
  recovery_rate: number;
  total_failed_count: number;
  recovery_attempts_count: number;
  successful_recoveries_count: number;
  pending_approvals_count: number;
  stopped_cases_count: number;
  total_transactions_count: number;
  average_recovery_amount: number;
  human_escalation_rate: number;
  failure_reasons_breakdown: { reason: FailureReason; count: number; amount: number }[];
  recovery_actions_breakdown: { action: RecoveryActionType; count: number }[];
  recovery_outcomes_breakdown?: { outcome: string; count: number }[];
  recovery_trend: { date: string; at_risk: number; recovered: number; recovery_rate?: number }[];
}

export interface SystemStatus {
  status: string;
  service: string;
  version: string;
  timestamp: string;
  mode: string;
  integrations: {
    razorpay: {
      configured: boolean;
      mode: 'TEST_MODE' | 'SIMULATION_MODE';
      key_id_masked: string;
    };
    ai_engine: {
      configured: boolean;
      provider: string;
      mode: string;
    };
    database: {
      status: string;
      engine: string;
    };
  };
}

export interface ApprovalItem {
  id: string;
  transaction_id: string;
  transaction: Transaction;
  ai_analysis: AIAgentAnalysis;
  policy_decision: PolicyDecision;
  created_at: string;
}

export interface DemoScenarioResult {
  scenario_id: string;
  title: string;
  transaction: Transaction;
  ai_analysis: AIAgentAnalysis;
  policy_decision: PolicyDecision;
  recovery_result: RecoveryExecutionResult;
  audit_timeline: AuditEvent[];
  mode: 'TEST_MODE' | 'SIMULATION_MODE';
}
