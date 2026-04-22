export type TaskStatus =
  | 'QUEUED'
  | 'EXECUTING'
  | 'REVIEWING'
  | 'FINALISING'
  | 'COMPLETED'
  | 'FAILED'
  | 'ESCALATED'

// API returns these field names — matches backend TaskResponse exactly
export interface ExecutorOutput {
  model: string
  confidence: number
  recommendation: string
  reasoning?: string
  flags?: string[]
  output?: Record<string, unknown>
}

export interface ReviewResult {
  reviewer_id?: string
  model: string
  verdict: string
  commitment_hash?: string
  commitment_verified: boolean
  notes?: string
  confidence?: number
}

export interface ReviewBlock {
  consensus?: string
  reviewers?: ReviewResult[]
  completed_at?: string
}

export interface VertexProof {
  event_hash: string
  round: number
  finalised_at: string
  node_id?: string
}

export interface Task {
  task_id: string
  task_type: string
  status: TaskStatus
  created_at: string
  updated_at?: string
  workflow_id?: string
  report_available: boolean
  // API uses these field names
  executor?: ExecutorOutput | null
  review?: ReviewBlock | null
  vertex?: VertexProof | null
  error_message?: string
}

export interface TaskListResponse {
  tasks: Task[]
  total: number
  page: number
  page_size: number
}

export interface SubmitTaskBody {
  task_type: string
  document: string
  review_criteria: string[]
}

export interface EuAiActArticle {
  article: string
  title: string
  status: string
  findings: string[]
  recommendations: string[]
}

export interface PoCReport {
  task_id: string
  generated_at: string
  plain_english_summary: string
  overall_recommendation: string
  confidence_score: number
  eu_ai_act_compliance: EuAiActArticle[]
  reviewer_consensus?: string
  vertex_proof_hash?: string
}

export interface EuAiActExport {
  task_id: string
  export_format: string
  generated_at: string
  articles: EuAiActArticle[]
}


export interface SignedReportSignature {
  algorithm: string
  signing_key_id: string
  signed_at: string
  signature_hex: string
}

export interface SignedReportEnvelope {
  payload: Record<string, unknown>
  signature: SignedReportSignature
  persisted?: boolean
}
