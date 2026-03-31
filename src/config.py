"""Configuration and constants for message-to-iaac."""

import os
from dataclasses import dataclass, field
from typing import Optional


# Supported cloud providers
SUPPORTED_CLOUDS = ["aws", "azure", "gcp"]

# Supported IaC tools
SUPPORTED_IAC_TOOLS = ["terraform", "pulumi", "cloudformation", "cdk", "bicep"]

# Default regions per cloud
DEFAULT_REGIONS = {
    "aws": "ap-south-1",
    "azure": "centralindia",
    "gcp": "asia-south1",
}

# Service abstraction categories
SERVICE_CATEGORIES = [
    "compute",
    "storage",
    "database",
    "networking",
    "security",
    "monitoring",
    "messaging",
    "devops",
    "analytics",
    "ai_ml",
]

# Cloud service mapping reference
CLOUD_SERVICE_MAP = {
    "aws": {
        "compute_vm": "EC2",
        "compute_autoscaling": "EC2 Auto Scaling",
        "compute_containers": "ECS / EKS",
        "compute_serverless": "Lambda",
        "storage_object": "S3",
        "storage_block": "EBS",
        "storage_file": "EFS",
        "storage_archive": "S3 Glacier",
        "database_sql": "RDS",
        "database_nosql": "DynamoDB",
        "database_cache": "ElastiCache",
        "database_warehouse": "Redshift",
        "networking_vpc": "VPC",
        "networking_subnets": "Subnets",
        "networking_load_balancer": "ALB / NLB",
        "networking_dns": "Route 53",
        "networking_cdn": "CloudFront",
        "security_iam": "IAM",
        "security_secrets": "Secrets Manager",
        "security_encryption": "KMS",
        "security_waf": "WAF",
        "security_firewall": "Security Groups / NACLs",
        "monitoring_logs": "CloudWatch Logs",
        "monitoring_metrics": "CloudWatch Metrics",
        "monitoring_tracing": "X-Ray",
        "monitoring_alerts": "CloudWatch Alarms / SNS",
        "messaging_queue": "SQS",
        "messaging_pubsub": "SNS",
        "messaging_streaming": "Kinesis",
        "devops_ci_cd": "CodePipeline / CodeBuild",
        "devops_registry": "ECR",
        "devops_deployment": "CodeDeploy",
        "analytics_etl": "Glue",
        "analytics_query": "Athena",
        "analytics_processing": "EMR",
        "ai_ml_training": "SageMaker",
        "ai_ml_inference": "SageMaker Endpoints",
    },
    "azure": {
        "compute_vm": "Virtual Machines",
        "compute_autoscaling": "VM Scale Sets",
        "compute_containers": "AKS",
        "compute_serverless": "Azure Functions",
        "storage_object": "Blob Storage",
        "storage_block": "Managed Disks",
        "storage_file": "Azure Files",
        "storage_archive": "Archive Storage",
        "database_sql": "Azure SQL Database",
        "database_nosql": "Cosmos DB",
        "database_cache": "Azure Cache for Redis",
        "database_warehouse": "Synapse Analytics",
        "networking_vpc": "VNet",
        "networking_subnets": "Subnets",
        "networking_load_balancer": "Azure Load Balancer / App Gateway",
        "networking_dns": "Azure DNS",
        "networking_cdn": "Azure CDN",
        "security_iam": "Azure AD / RBAC",
        "security_secrets": "Key Vault",
        "security_encryption": "Key Vault Keys",
        "security_waf": "Azure WAF",
        "security_firewall": "NSG / Azure Firewall",
        "monitoring_logs": "Azure Monitor Logs",
        "monitoring_metrics": "Azure Monitor Metrics",
        "monitoring_tracing": "Application Insights",
        "monitoring_alerts": "Azure Alerts",
        "messaging_queue": "Azure Queue Storage",
        "messaging_pubsub": "Event Grid",
        "messaging_streaming": "Event Hubs",
        "devops_ci_cd": "Azure DevOps Pipelines",
        "devops_registry": "ACR",
        "devops_deployment": "Azure DevOps Release",
        "analytics_etl": "Data Factory",
        "analytics_query": "Data Explorer",
        "analytics_processing": "HDInsight",
        "ai_ml_training": "Azure ML",
        "ai_ml_inference": "Azure ML Endpoints",
    },
    "gcp": {
        "compute_vm": "Compute Engine",
        "compute_autoscaling": "Managed Instance Groups",
        "compute_containers": "GKE",
        "compute_serverless": "Cloud Functions / Cloud Run",
        "storage_object": "Cloud Storage",
        "storage_block": "Persistent Disk",
        "storage_file": "Filestore",
        "storage_archive": "Archive Storage Class",
        "database_sql": "Cloud SQL",
        "database_nosql": "Firestore / Bigtable",
        "database_cache": "Memorystore",
        "database_warehouse": "BigQuery",
        "networking_vpc": "VPC",
        "networking_subnets": "Subnets",
        "networking_load_balancer": "Cloud Load Balancing",
        "networking_dns": "Cloud DNS",
        "networking_cdn": "Cloud CDN",
        "security_iam": "IAM",
        "security_secrets": "Secret Manager",
        "security_encryption": "Cloud KMS",
        "security_waf": "Cloud Armor",
        "security_firewall": "Firewall Rules",
        "monitoring_logs": "Cloud Logging",
        "monitoring_metrics": "Cloud Monitoring",
        "monitoring_tracing": "Cloud Trace",
        "monitoring_alerts": "Alerting Policies",
        "messaging_queue": "Cloud Tasks",
        "messaging_pubsub": "Pub/Sub",
        "messaging_streaming": "Dataflow",
        "devops_ci_cd": "Cloud Build",
        "devops_registry": "Artifact Registry",
        "devops_deployment": "Cloud Deploy",
        "analytics_etl": "Dataflow",
        "analytics_query": "BigQuery",
        "analytics_processing": "Dataproc",
        "ai_ml_training": "Vertex AI",
        "ai_ml_inference": "Vertex AI Endpoints",
    },
}

# Supported LLM providers
SUPPORTED_PROVIDERS = [
    "groq", "gemini", "openai", "claude", "bedrock",
    "azure_openai", "mistral", "deepseek", "cohere", "together", "ollama",
]

# Default models per provider
DEFAULT_MODELS = {
    "groq": "llama-3.3-70b-versatile",
    "gemini": "gemini-2.0-flash",
    "openai": "gpt-4o-mini",
    "claude": "claude-sonnet-4-6-20250514",
    "bedrock": "us.anthropic.claude-3-5-haiku-20241022-v1:0",
    "azure_openai": "gpt-4o-mini",
    "mistral": "mistral-large-latest",
    "deepseek": "deepseek-coder",
    "cohere": "command-r-plus",
    "together": "Qwen/Qwen2.5-Coder-32B-Instruct",
    "ollama": "qwen2.5-coder:7b",
}

# Default Ollama URL
DEFAULT_OLLAMA_URL = "http://localhost:11434"

# IaC file extensions
IAC_EXTENSIONS = {
    "terraform": ".tf",
    "pulumi": ".py",
    "cloudformation": ".yaml",
    "cdk": ".ts",
    "bicep": ".bicep",
}


@dataclass
class PipelineConfig:
    """Configuration for a single pipeline run."""

    user_message: str
    cloud: str = "aws"
    iac_tool: str = "terraform"
    region: Optional[str] = None
    compliance: list = field(default_factory=lambda: ["SOC2", "ISO27001", "CIS"])
    output_dir: str = "output"
    provider: str = "claude"
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
            self.region = DEFAULT_REGIONS[self.cloud]
        if self.model is None:
            self.model = DEFAULT_MODELS[self.provider]
        if self.ollama_url is None:
            self.ollama_url = os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_URL)
