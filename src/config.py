"""Dynamic configuration for IaCraft. All values configurable via environment variables."""

import os
from dataclasses import dataclass, field
from typing import Optional


def _env(key: str, default: str = "") -> str:
    """Get environment variable with default."""
    return os.getenv(key, default)


def _env_int(key: str, default: int = 0) -> int:
    """Get environment variable as int."""
    return int(os.getenv(key, str(default)))


def _env_float(key: str, default: float = 0.0) -> float:
    """Get environment variable as float."""
    return float(os.getenv(key, str(default)))


def _env_list(key: str, default: str = "") -> list:
    """Get environment variable as comma-separated list."""
    val = os.getenv(key, default)
    return [x.strip() for x in val.split(",") if x.strip()] if val else []


def _env_bool(key: str, default: bool = False) -> bool:
    """Get environment variable as boolean."""
    return os.getenv(key, str(default)).lower() in ("true", "1", "yes")


# =============================================================================
# Application Settings
# =============================================================================
APP_NAME = _env("APP_NAME", "IaCraft")
APP_VERSION = _env("APP_VERSION", "3.0.0")

# Dashboard
DASHBOARD_HOST = _env("DASHBOARD_HOST", "0.0.0.0")
DASHBOARD_PORT = _env_int("DASHBOARD_PORT", 15000)

# Auth
ADMIN_PASSWORD = _env("ADMIN_PASSWORD", "")  # No default — must be set
GUEST_PASSWORD = _env("GUEST_PASSWORD", "guest")
SESSION_MAX_AGE_DAYS = _env_int("SESSION_MAX_AGE_DAYS", 30)

# CORS
CORS_ORIGINS = _env_list("CORS_ORIGINS", "http://localhost:3000,http://localhost:15000,http://127.0.0.1:3000")

# Output
DEFAULT_OUTPUT_DIR = _env("OUTPUT_DIR", "output")

# =============================================================================
# Cloud Providers
# =============================================================================
SUPPORTED_CLOUDS = _env_list("SUPPORTED_CLOUDS", "aws,azure,gcp") or ["aws", "azure", "gcp"]
SUPPORTED_IAC_TOOLS = _env_list("SUPPORTED_IAC_TOOLS", "terraform,pulumi,cloudformation,cdk,bicep") or ["terraform", "pulumi", "cloudformation", "cdk", "bicep"]

DEFAULT_REGIONS = {
    "aws": _env("DEFAULT_REGION_AWS", "ap-south-1"),
    "azure": _env("DEFAULT_REGION_AZURE", "centralindia"),
    "gcp": _env("DEFAULT_REGION_GCP", "asia-south1"),
}

DEFAULT_COMPLIANCE = _env_list("DEFAULT_COMPLIANCE", "SOC2,ISO27001,CIS") or ["SOC2", "ISO27001", "CIS"]

# =============================================================================
# LLM Providers
# =============================================================================
SUPPORTED_PROVIDERS = _env_list("SUPPORTED_PROVIDERS",
    "groq,gemini,openai,claude,bedrock,azure_openai,mistral,deepseek,cohere,together,ollama"
) or ["groq", "gemini", "openai", "claude", "bedrock", "azure_openai", "mistral", "deepseek", "cohere", "together", "ollama"]

DEFAULT_MODELS = {
    "groq": _env("DEFAULT_MODEL_GROQ", "llama-3.3-70b-versatile"),
    "gemini": _env("DEFAULT_MODEL_GEMINI", "gemini-2.0-flash"),
    "openai": _env("DEFAULT_MODEL_OPENAI", "gpt-4o-mini"),
    "claude": _env("DEFAULT_MODEL_CLAUDE", "claude-sonnet-4-6-20250514"),
    "bedrock": _env("DEFAULT_MODEL_BEDROCK", "us.anthropic.claude-3-5-haiku-20241022-v1:0"),
    "azure_openai": _env("DEFAULT_MODEL_AZURE", "gpt-4o-mini"),
    "mistral": _env("DEFAULT_MODEL_MISTRAL", "mistral-large-latest"),
    "deepseek": _env("DEFAULT_MODEL_DEEPSEEK", "deepseek-coder"),
    "cohere": _env("DEFAULT_MODEL_COHERE", "command-r-plus"),
    "together": _env("DEFAULT_MODEL_TOGETHER", "Qwen/Qwen2.5-Coder-32B-Instruct"),
    "ollama": _env("DEFAULT_MODEL_OLLAMA", "qwen2.5-coder:7b"),
}

DEFAULT_PROVIDER = _env("DEFAULT_PROVIDER", "groq")
DEFAULT_OLLAMA_URL = _env("OLLAMA_BASE_URL", "http://localhost:11434")

# =============================================================================
# LLM Settings
# =============================================================================
LLM_TEMPERATURE = _env_float("LLM_TEMPERATURE", 0.2)
LLM_MAX_TOKENS = _env_int("LLM_MAX_TOKENS", 8192)
LLM_MAX_TOKENS_ANALYSIS = _env_int("LLM_MAX_TOKENS_ANALYSIS", 4096)
DEFAULT_CONTEXT_SIZE = _env_int("DEFAULT_CONTEXT_SIZE", 4096)

# Ollama timeouts
OLLAMA_CONNECT_TIMEOUT = _env_float("OLLAMA_CONNECT_TIMEOUT", 10.0)
OLLAMA_READ_TIMEOUT = _env_float("OLLAMA_READ_TIMEOUT", 1800.0)
OLLAMA_HEALTH_TIMEOUT = _env_float("OLLAMA_HEALTH_TIMEOUT", 5.0)

# =============================================================================
# Validator Settings
# =============================================================================
VALIDATOR_MAX_ROUNDS = _env_int("VALIDATOR_MAX_ROUNDS", 5)
TERRAFORM_CMD_TIMEOUT = _env_int("TERRAFORM_CMD_TIMEOUT", 120)
CHECKOV_CMD_TIMEOUT = _env_int("CHECKOV_CMD_TIMEOUT", 120)

# =============================================================================
# Documentation Settings
# =============================================================================
DOC_MAX_TOKENS_QUICK = _env_int("DOC_MAX_TOKENS_QUICK", 1024)
DOC_MAX_TOKENS_STANDARD = _env_int("DOC_MAX_TOKENS_STANDARD", 2048)
DOC_MAX_TOKENS_ENTERPRISE = _env_int("DOC_MAX_TOKENS_ENTERPRISE", 3072)
DOC_MAX_TOKENS_COMPLIANCE = _env_int("DOC_MAX_TOKENS_COMPLIANCE", 3072)

# =============================================================================
# Service abstraction categories
# =============================================================================
SERVICE_CATEGORIES = [
    "compute", "storage", "database", "networking", "security",
    "monitoring", "messaging", "devops", "analytics", "ai_ml",
]

# =============================================================================
# Cloud service mapping reference
# =============================================================================
CLOUD_SERVICE_MAP = {
    "aws": {
        "compute_vm": "EC2", "compute_autoscaling": "EC2 Auto Scaling",
        "compute_containers": "ECS / EKS", "compute_serverless": "Lambda",
        "storage_object": "S3", "storage_block": "EBS", "storage_file": "EFS", "storage_archive": "S3 Glacier",
        "database_sql": "RDS", "database_nosql": "DynamoDB", "database_cache": "ElastiCache", "database_warehouse": "Redshift",
        "networking_vpc": "VPC", "networking_subnets": "Subnets", "networking_load_balancer": "ALB / NLB",
        "networking_dns": "Route 53", "networking_cdn": "CloudFront",
        "security_iam": "IAM", "security_secrets": "Secrets Manager", "security_encryption": "KMS",
        "security_waf": "WAF", "security_firewall": "Security Groups / NACLs",
        "monitoring_logs": "CloudWatch Logs", "monitoring_metrics": "CloudWatch Metrics",
        "monitoring_tracing": "X-Ray", "monitoring_alerts": "CloudWatch Alarms / SNS",
        "messaging_queue": "SQS", "messaging_pubsub": "SNS", "messaging_streaming": "Kinesis",
        "devops_ci_cd": "CodePipeline / CodeBuild", "devops_registry": "ECR", "devops_deployment": "CodeDeploy",
        "analytics_etl": "Glue", "analytics_query": "Athena", "analytics_processing": "EMR",
        "ai_ml_training": "SageMaker", "ai_ml_inference": "SageMaker Endpoints",
    },
    "azure": {
        "compute_vm": "Virtual Machines", "compute_autoscaling": "VM Scale Sets",
        "compute_containers": "AKS", "compute_serverless": "Azure Functions",
        "storage_object": "Blob Storage", "storage_block": "Managed Disks", "storage_file": "Azure Files", "storage_archive": "Archive Storage",
        "database_sql": "Azure SQL Database", "database_nosql": "Cosmos DB", "database_cache": "Azure Cache for Redis", "database_warehouse": "Synapse Analytics",
        "networking_vpc": "VNet", "networking_subnets": "Subnets", "networking_load_balancer": "Azure Load Balancer / App Gateway",
        "networking_dns": "Azure DNS", "networking_cdn": "Azure CDN",
        "security_iam": "Azure AD / RBAC", "security_secrets": "Key Vault", "security_encryption": "Key Vault Keys",
        "security_waf": "Azure WAF", "security_firewall": "NSG / Azure Firewall",
        "monitoring_logs": "Azure Monitor Logs", "monitoring_metrics": "Azure Monitor Metrics",
        "monitoring_tracing": "Application Insights", "monitoring_alerts": "Azure Alerts",
        "messaging_queue": "Azure Queue Storage", "messaging_pubsub": "Event Grid", "messaging_streaming": "Event Hubs",
        "devops_ci_cd": "Azure DevOps Pipelines", "devops_registry": "ACR", "devops_deployment": "Azure DevOps Release",
        "analytics_etl": "Data Factory", "analytics_query": "Data Explorer", "analytics_processing": "HDInsight",
        "ai_ml_training": "Azure ML", "ai_ml_inference": "Azure ML Endpoints",
    },
    "gcp": {
        "compute_vm": "Compute Engine", "compute_autoscaling": "Managed Instance Groups",
        "compute_containers": "GKE", "compute_serverless": "Cloud Functions / Cloud Run",
        "storage_object": "Cloud Storage", "storage_block": "Persistent Disk", "storage_file": "Filestore", "storage_archive": "Archive Storage Class",
        "database_sql": "Cloud SQL", "database_nosql": "Firestore / Bigtable", "database_cache": "Memorystore", "database_warehouse": "BigQuery",
        "networking_vpc": "VPC", "networking_subnets": "Subnets", "networking_load_balancer": "Cloud Load Balancing",
        "networking_dns": "Cloud DNS", "networking_cdn": "Cloud CDN",
        "security_iam": "IAM", "security_secrets": "Secret Manager", "security_encryption": "Cloud KMS",
        "security_waf": "Cloud Armor", "security_firewall": "Firewall Rules",
        "monitoring_logs": "Cloud Logging", "monitoring_metrics": "Cloud Monitoring",
        "monitoring_tracing": "Cloud Trace", "monitoring_alerts": "Alerting Policies",
        "messaging_queue": "Cloud Tasks", "messaging_pubsub": "Pub/Sub", "messaging_streaming": "Dataflow",
        "devops_ci_cd": "Cloud Build", "devops_registry": "Artifact Registry", "devops_deployment": "Cloud Deploy",
        "analytics_etl": "Dataflow", "analytics_query": "BigQuery", "analytics_processing": "Dataproc",
        "ai_ml_training": "Vertex AI", "ai_ml_inference": "Vertex AI Endpoints",
    },
}

IAC_EXTENSIONS = {
    "terraform": ".tf", "pulumi": ".py", "cloudformation": ".yaml", "cdk": ".ts", "bicep": ".bicep",
}


# =============================================================================
# Pipeline Configuration
# =============================================================================
@dataclass
class PipelineConfig:
    """Configuration for a single pipeline run. All defaults from env vars."""

    user_message: str
    cloud: str = "aws"
    iac_tool: str = "terraform"
    region: Optional[str] = None
    compliance: list = field(default_factory=lambda: DEFAULT_COMPLIANCE.copy())
    output_dir: str = field(default_factory=lambda: DEFAULT_OUTPUT_DIR)
    provider: str = field(default_factory=lambda: DEFAULT_PROVIDER)
    model: Optional[str] = None
    ollama_url: Optional[str] = None
    doc_level: str = "standard"

    def __post_init__(self):
        self.cloud = self.cloud.lower()
        self.iac_tool = self.iac_tool.lower()
        self.provider = self.provider.lower()

        if self.cloud not in SUPPORTED_CLOUDS:
            raise ValueError(f"Unsupported cloud: {self.cloud}. Use: {SUPPORTED_CLOUDS}")
        if self.iac_tool not in SUPPORTED_IAC_TOOLS:
            raise ValueError(f"Unsupported IaC tool: {self.iac_tool}. Use: {SUPPORTED_IAC_TOOLS}")
        if self.provider not in SUPPORTED_PROVIDERS:
            raise ValueError(f"Unsupported provider: {self.provider}. Use: {SUPPORTED_PROVIDERS}")
        if self.region is None:
            self.region = DEFAULT_REGIONS.get(self.cloud, "us-east-1")
        if self.model is None:
            self.model = DEFAULT_MODELS.get(self.provider)
        if self.ollama_url is None:
            self.ollama_url = DEFAULT_OLLAMA_URL
