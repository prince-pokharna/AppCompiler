/** TypeScript types matching backend Pydantic models. */

// ── Intent ──
export interface IntentSchema {
  app_name: string;
  app_type: "crm" | "ecommerce" | "saas" | "dashboard" | "marketplace" | "other";
  description: string;
  core_features: string[];
  entities: string[];
  roles: string[];
  auth_required: boolean;
  payment_required: boolean;
  analytics_required: boolean;
  assumptions: string[];
  clarifications_needed: string[];
}

// ── Architecture ──
export interface FieldDefinition {
  name: string;
  type: string;
  required: boolean;
  unique: boolean;
  default: string | null;
  description: string;
}

export interface RelationDefinition {
  target_entity: string;
  type: "one-to-one" | "one-to-many" | "many-to-many";
  foreign_key: string;
  description: string;
}

export interface EntityDefinition {
  name: string;
  fields: FieldDefinition[];
  relations: RelationDefinition[];
  description: string;
}

export interface ArchitectureSchema {
  entities: EntityDefinition[];
  pages: string[];
  api_groups: string[];
  role_permissions: Record<string, string[]>;
  business_rules: string[];
  tech_decisions: string[];
}

// ── UI ──
export interface ComponentSchema {
  name: string;
  type: string;
  props: Record<string, string>;
  data_source: string;
  description: string;
}

export interface PageSchema {
  name: string;
  route: string;
  layout: string;
  auth_required: boolean;
  roles_allowed: string[];
  components: ComponentSchema[];
  description: string;
}

export interface UISchema {
  pages: PageSchema[];
  theme: string;
  navigation_type: "sidebar" | "topnav" | "both";
}

// ── API ──
export interface FieldSpec {
  name: string;
  type: string;
  required: boolean;
  description: string;
}

export interface EndpointSchema {
  method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  path: string;
  group: string;
  description: string;
  auth_required: boolean;
  roles_allowed: string[];
  request_body: FieldSpec[];
  response_body: FieldSpec[];
  query_params: FieldSpec[];
}

export interface APISchema {
  base_path: string;
  endpoints: EndpointSchema[];
}

// ── Database ──
export interface ColumnSchema {
  name: string;
  type: string;
  primary_key: boolean;
  nullable: boolean;
  unique: boolean;
  default: string | null;
  description: string;
}

export interface IndexSchema {
  name: string;
  columns: string[];
  unique: boolean;
}

export interface ForeignKeySchema {
  column: string;
  references_table: string;
  references_column: string;
  on_delete: string;
}

export interface TableSchema {
  name: string;
  columns: ColumnSchema[];
  indexes: IndexSchema[];
  foreign_keys: ForeignKeySchema[];
  description: string;
}

export interface DatabaseSchema {
  tables: TableSchema[];
}

// ── Auth ──
export interface PermissionRule {
  action: string;
  resource: string;
  conditions: string[];
}

export interface JWTConfig {
  secret_env_var: string;
  algorithm: string;
  access_token_expiry_minutes: number;
  refresh_token_expiry_days: number;
}

export interface AuthSchema {
  strategy: "jwt" | "session" | "oauth" | "api_key";
  roles: string[];
  permissions: Record<string, PermissionRule[]>;
  jwt_config: JWTConfig;
  oauth_providers: string[];
  mfa_enabled: boolean;
}

// ── Generation Meta ──
export interface StageTimingInfo {
  stage_name: string;
  duration_ms: number;
  input_tokens: number;
  output_tokens: number;
  model_used: string;
  retries: number;
  cost_usd: number;
}

export interface GenerationMeta {
  total_duration_ms: number;
  total_cost_usd: number;
  stages: StageTimingInfo[];
  fast_mode: boolean;
  errors_found: number;
  errors_repaired: number;
  errors_unresolved: number;
}

// ── Master Schema ──
export interface MetaSchema {
  app_name: string;
  version: string;
  description: string;
  generated_at: string;
  generator_version: string;
}

export interface CompletedAppSchema {
  meta: MetaSchema;
  intent: IntentSchema;
  architecture: ArchitectureSchema;
  ui: UISchema;
  api: APISchema;
  database: DatabaseSchema;
  auth: AuthSchema;
  generation_meta: GenerationMeta;
}

// ── Pipeline ──
export type JobStatus = "queued" | "running" | "completed" | "failed";
export type PipelineStage = "intent" | "design" | "schemas" | "validation" | "refinement" | "codegen";

export interface ValidationError {
  error_type: string;
  layer: string;
  path: string;
  message: string;
  severity: string;
  auto_repairable: boolean;
}

export interface RepairAction {
  error_type: string;
  layer: string;
  description: string;
  method: string;
  success: boolean;
  duration_ms: number;
}

export interface ValidationReport {
  errors_found: ValidationError[];
  repairs_made: RepairAction[];
  unresolved_issues: ValidationError[];
  total_errors: number;
  total_repaired: number;
  total_unresolved: number;
  validation_time_ms: number;
  repair_time_ms: number;
}

export interface GeneratedFile {
  path: string;
  content: string;
  language: string;
}

export interface ExecutionReport {
  compilation_success: boolean;
  type_errors: string[];
  schema_errors: string[];
  runtime_errors: string[];
  checks_skipped: string[];
  duration_ms: number;
}

export interface CodeGenerationResult {
  generated_files: GeneratedFile[];
  execution_report: ExecutionReport;
  total_files: number;
  total_lines: number;
}

// ── SSE Events ──
export interface SSEEventData {
  stage?: string;
  message?: string;
  duration_ms?: number;
  layer?: string;
  description?: string;
  skipped?: boolean;
  errors_found?: number;
  errors_repaired?: number;
  errors_unresolved?: number;
  total_duration_ms?: number;
  total_cost_usd?: number;
  app_name?: string;
  files_generated?: number;
  compilation_success?: boolean;
  [key: string]: unknown;
}

export interface SSEEvent {
  event: "stage_start" | "stage_complete" | "repair" | "validation" | "done" | "error";
  data: SSEEventData;
}

// ── API Responses ──
export interface GenerateResponse {
  job_id: string;
  status: JobStatus;
}

export interface StatusResponse {
  job_id: string;
  status: JobStatus;
  current_stage: string | null;
  progress_pct: number;
  error: string | null;
}

export interface PromptResult {
  prompt_id: string;
  prompt_text: string;
  success: boolean;
  stage_times: Record<string, number>;
  total_latency_ms: number;
  retry_counts: Record<string, number>;
  repair_counts: number;
  errors_found: number;
  errors_resolved: number;
  token_usage: Record<string, Record<string, number>>;
  estimated_cost_usd: number;
  failure_type: string | null;
  assumptions_made: string[];
  error_message: string | null;
}

export interface EvaluationSummary {
  total_prompts: number;
  success_count: number;
  failure_count: number;
  success_rate_pct: number;
  avg_latency_ms: number;
  avg_retries: number;
  avg_repairs: number;
  total_cost_usd: number;
  failure_types: Record<string, number>;
}
