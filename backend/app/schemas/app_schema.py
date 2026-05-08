"""Pydantic models for the compiled app schema — the master output of the pipeline."""

from __future__ import annotations

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
# Intent Schema (Stage 1 output)
# ──────────────────────────────────────────────

class IntentSchema(BaseModel):
    """Structured intent extracted from natural language input."""
    app_name: str = Field(..., description="Name of the application")
    app_type: str = Field(
        ...,
        description="Type: crm, ecommerce, saas, dashboard, marketplace, other",
    )
    description: str = Field(..., description="One-paragraph app description")
    core_features: list[str] = Field(default_factory=list, description="Core features")
    entities: list[str] = Field(default_factory=list, description="Domain entities e.g. User, Contact")
    roles: list[str] = Field(default_factory=list, description="User roles e.g. admin, user")
    auth_required: bool = Field(default=True, description="Whether auth is needed")
    payment_required: bool = Field(default=False, description="Whether payments are needed")
    analytics_required: bool = Field(default=False, description="Whether analytics are needed")
    assumptions: list[str] = Field(default_factory=list, description="Inferred assumptions from vague input")
    clarifications_needed: list[str] = Field(
        default_factory=list,
        description="Questions that would improve specificity (empty if fully specified)",
    )


# ──────────────────────────────────────────────
# Architecture Schema (Stage 2 output)
# ──────────────────────────────────────────────

class FieldDefinition(BaseModel):
    """A single field in an entity."""
    name: str
    type: str = Field(..., description="Field type: string, integer, boolean, datetime, text, float, json, uuid")
    required: bool = True
    unique: bool = False
    default: str | None = None
    description: str = ""


class RelationDefinition(BaseModel):
    """A relationship between entities."""
    target_entity: str
    type: str = Field(..., description="one-to-one, one-to-many, many-to-many")
    foreign_key: str = ""
    description: str = ""


class EntityDefinition(BaseModel):
    """Full entity definition with fields and relations."""
    name: str
    fields: list[FieldDefinition] = Field(default_factory=list)
    relations: list[RelationDefinition] = Field(default_factory=list)
    description: str = ""


class ArchitectureSchema(BaseModel):
    """System architecture derived from intent."""
    entities: list[EntityDefinition] = Field(default_factory=list)
    pages: list[str] = Field(default_factory=list)
    api_groups: list[str] = Field(default_factory=list)
    role_permissions: dict[str, list[str]] = Field(
        default_factory=dict,
        description="role -> list of allowed actions",
    )
    business_rules: list[str] = Field(default_factory=list)
    tech_decisions: list[str] = Field(default_factory=list)


# ──────────────────────────────────────────────
# UI Schema (Stage 3a output)
# ──────────────────────────────────────────────

class ComponentSchema(BaseModel):
    """A UI component within a page."""
    name: str
    type: str = Field(..., description="form, table, card, chart, list, modal, nav, sidebar, hero")
    props: dict[str, str] = Field(default_factory=dict)
    data_source: str = Field(default="", description="API endpoint this component consumes")
    description: str = ""


class PageSchema(BaseModel):
    """A single page in the application."""
    name: str
    route: str
    layout: str = "default"
    auth_required: bool = False
    roles_allowed: list[str] = Field(default_factory=list)
    components: list[ComponentSchema] = Field(default_factory=list)
    description: str = ""


class UISchema(BaseModel):
    """Complete UI schema with all pages and their components."""
    pages: list[PageSchema] = Field(default_factory=list)
    theme: str = "default"
    navigation_type: str = Field(default="sidebar", description="sidebar, topnav, both")


# ──────────────────────────────────────────────
# API Schema (Stage 3b output)
# ──────────────────────────────────────────────

class FieldSpec(BaseModel):
    """A field in a request/response body."""
    name: str
    type: str
    required: bool = True
    description: str = ""


class EndpointSchema(BaseModel):
    """A single API endpoint."""
    method: str = Field(..., description="GET, POST, PUT, PATCH, DELETE")
    path: str = Field(..., description="API path e.g. /api/contacts")
    group: str = Field(default="", description="API group this belongs to")
    description: str = ""
    auth_required: bool = True
    roles_allowed: list[str] = Field(default_factory=list)
    request_body: list[FieldSpec] = Field(default_factory=list)
    response_body: list[FieldSpec] = Field(default_factory=list)
    query_params: list[FieldSpec] = Field(default_factory=list)


class APISchema(BaseModel):
    """Complete API schema with all endpoints."""
    base_path: str = "/api"
    endpoints: list[EndpointSchema] = Field(default_factory=list)


# ──────────────────────────────────────────────
# Database Schema (Stage 3c output)
# ──────────────────────────────────────────────

class ColumnSchema(BaseModel):
    """A single column in a database table."""
    name: str
    type: str = Field(..., description="String, Integer, Boolean, DateTime, Text, Float, JSON, UUID")
    primary_key: bool = False
    nullable: bool = True
    unique: bool = False
    default: str | None = None
    description: str = ""


class IndexSchema(BaseModel):
    """A database index."""
    name: str
    columns: list[str]
    unique: bool = False


class ForeignKeySchema(BaseModel):
    """A foreign key constraint."""
    column: str
    references_table: str
    references_column: str
    on_delete: str = "CASCADE"


class TableSchema(BaseModel):
    """A single database table."""
    name: str
    columns: list[ColumnSchema] = Field(default_factory=list)
    indexes: list[IndexSchema] = Field(default_factory=list)
    foreign_keys: list[ForeignKeySchema] = Field(default_factory=list)
    description: str = ""


class DatabaseSchema(BaseModel):
    """Complete database schema with all tables."""
    tables: list[TableSchema] = Field(default_factory=list)


# ──────────────────────────────────────────────
# Auth Schema (Stage 3d output)
# ──────────────────────────────────────────────

class JWTConfig(BaseModel):
    """JWT configuration."""
    secret_env_var: str = "JWT_SECRET"
    algorithm: str = "HS256"
    access_token_expiry_minutes: int = 60
    refresh_token_expiry_days: int = 7


class PermissionRule(BaseModel):
    """A single permission rule."""
    action: str
    resource: str
    conditions: list[str] = Field(default_factory=list)


class AuthSchema(BaseModel):
    """Complete auth schema."""
    strategy: str = Field(default="jwt", description="jwt, session, oauth, api_key")
    roles: list[str] = Field(default_factory=list)
    permissions: dict[str, list[PermissionRule]] = Field(
        default_factory=dict,
        description="role -> list of permission rules",
    )
    jwt_config: JWTConfig = Field(default_factory=JWTConfig)
    oauth_providers: list[str] = Field(default_factory=list)
    mfa_enabled: bool = False


# ──────────────────────────────────────────────
# Meta & Generation Info
# ──────────────────────────────────────────────

class MetaSchema(BaseModel):
    """Application metadata."""
    app_name: str
    version: str = "1.0.0"
    description: str = ""
    generated_at: str = ""
    generator_version: str = "1.0.0"


class StageTimingInfo(BaseModel):
    """Timing and token info for a single pipeline stage."""
    stage_name: str
    duration_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    model_used: str = ""
    retries: int = 0
    cost_usd: float = 0.0


class GenerationMeta(BaseModel):
    """Metadata about the generation process."""
    total_duration_ms: int = 0
    total_cost_usd: float = 0.0
    stages: list[StageTimingInfo] = Field(default_factory=list)
    fast_mode: bool = False
    errors_found: int = 0
    errors_repaired: int = 0
    errors_unresolved: int = 0


# ──────────────────────────────────────────────
# Master Output Schema
# ──────────────────────────────────────────────

class CompletedAppSchema(BaseModel):
    """The complete compiled app schema — the master output of the pipeline."""
    meta: MetaSchema
    intent: IntentSchema
    architecture: ArchitectureSchema
    ui: UISchema
    api: APISchema
    database: DatabaseSchema
    auth: AuthSchema
    generation_meta: GenerationMeta
