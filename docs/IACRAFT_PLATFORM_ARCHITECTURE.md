# IaCraft Platform — Architecture & Strategy Report

**Version**: 4.0 Planning Document
**Date**: April 2026
**Author**: IaCraft Engineering
**Classification**: Internal — Strategic

---

## 1. Executive Summary

IaCraft started as a natural language to Infrastructure as Code converter. This report outlines the architecture to evolve it into a **full DevOps AI Platform** that handles the complete infrastructure lifecycle:

```
DESIGN → BUILD → VALIDATE → DEPLOY → MONITOR → OPTIMIZE
```

The platform will use AI at every stage — from understanding requirements to self-healing production infrastructure.

---

## 2. Current State (v3.0)

### What IaCraft Does Today

| Capability | Status | Description |
|-----------|--------|-------------|
| NL to IaC | Working | Convert plain English to Terraform/Pulumi/CDK/Bicep |
| Multi-Cloud | Working | AWS, Azure, GCP support |
| 11 LLM Providers | Working | Groq, Gemini, OpenAI, Claude, Bedrock, Azure, Mistral, DeepSeek, Cohere, Together, Ollama |
| Auto-Fallback | Working | Rate limit on one → auto-switch to next |
| Code Validation | Working | terraform fmt + validate + checkov |
| Auto-Fix Loop | Working | Detect errors → LLM fix → re-validate (5 rounds) |
| Multi-Cloud Compare | Working | AWS vs Azure vs GCP side-by-side |
| Deployment Guide | Working | 4 doc levels (Quick/Standard/Enterprise/Compliance) |
| Security Controls | Working | IAM, encryption, compliance mapping |
| Cost Estimation | Working | Monthly breakdown + optimization |
| Web Dashboard | Working | Login, dark/light theme, settings |
| CLI | Working | 5 commands (generate, simulate, analyze, providers, dashboard) |

### Current Architecture

```
User → Dashboard/CLI → AI Engine → Pipeline (12 steps) → Output Files
                          │
                    ┌─────┴──────┐
                    │ LLM Router │
                    │ (11 providers) │
                    └────────────┘
```

### Current Limitations

1. **No actual deployment** — generates code but doesn't deploy it
2. **No monitoring** — no visibility after deployment
3. **No drift detection** — can't detect manual changes
4. **No CI/CD integration** — no pipeline generation
5. **No state management** — no history of past generations
6. **No team collaboration** — single user
7. **Static validation only** — no runtime checks
8. **No cost tracking** — estimates only, no actual spend comparison

---

## 3. Target Architecture (v4.0+)

### Platform Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    IaCraft DevOps Platform                       │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                  Presentation Layer                         │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │ │
│  │  │Web       │  │CLI       │  │API       │  │Slack/    │  │ │
│  │  │Dashboard │  │Terminal  │  │REST      │  │Teams Bot │  │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │ │
│  └────────────────────────┬───────────────────────────────────┘ │
│                           │                                      │
│  ┌────────────────────────▼───────────────────────────────────┐ │
│  │                  Application Layer                          │ │
│  │                                                             │ │
│  │  ┌─────────────────────────────────────────────────────┐   │ │
│  │  │              AI Engine (LLM Router)                  │   │ │
│  │  │  Groq → Bedrock → Gemini → Ollama (auto-fallback)  │   │ │
│  │  └─────────────────────┬───────────────────────────────┘   │ │
│  │                        │                                    │ │
│  │  ┌─────────┬───────────┼───────────┬─────────┬──────────┐ │ │
│  │  │         │           │           │         │          │ │ │
│  │  ▼         ▼           ▼           ▼         ▼          ▼ │ │
│  │ Design   Build      Validate    Deploy    Monitor   Optimize│ │
│  │ Module   Module     Module      Module    Module    Module  │ │
│  │                                                             │ │
│  │  ┌─────────────────────────────────────────────────────┐   │ │
│  │  │           Workflow Engine (State Machine)            │   │ │
│  │  │  Design → Build → Validate → Deploy → Monitor       │   │ │
│  │  └─────────────────────────────────────────────────────┘   │ │
│  │                                                             │ │
│  │  ┌─────────────────────────────────────────────────────┐   │ │
│  │  │              Policy Engine (OPA)                     │   │ │
│  │  │  Security policies, cost budgets, compliance rules   │   │ │
│  │  └─────────────────────────────────────────────────────┘   │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    Data Layer                                │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐  │ │
│  │  │Project   │ │Template  │ │Execution │ │Terraform      │  │ │
│  │  │Database  │ │Library   │ │History   │ │State Store    │  │ │
│  │  │(SQLite/  │ │(Git)     │ │(Logs)    │ │(S3/Blob/GCS) │  │ │
│  │  │Postgres) │ │          │ │          │ │               │  │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └───────────────┘  │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                  Integration Layer                           │ │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌──────────┐ │ │
│  │  │AWS     │ │Azure   │ │GCP     │ │GitHub  │ │Terraform │ │ │
│  │  │APIs    │ │APIs    │ │APIs    │ │GitLab  │ │Cloud     │ │ │
│  │  └────────┘ └────────┘ └────────┘ └────────┘ └──────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Module Specifications

### 4.1 Design Module (Existing — Enhanced)

**Purpose**: Convert natural language to cloud architecture design

**Current Features**:
- Requirement analysis
- Cloud-agnostic architecture JSON
- Cloud service mapping
- Architecture diagram (Mermaid)

**Planned Enhancements**:

| Feature | Description | Priority |
|---------|------------|----------|
| Template Library | Pre-built architectures (3-tier, microservices, serverless, data pipeline) | High |
| Architecture Review | AI reviews design and suggests improvements | High |
| Well-Architected Check | Validate against AWS/Azure/GCP Well-Architected Framework | Medium |
| Multi-Region Design | Auto-design DR and multi-region architectures | Medium |
| Dependency Graph | Visual dependency map between resources | Low |

### 4.2 Build Module (Existing — Enhanced)

**Purpose**: Generate deployment-ready IaC code

**Current Features**:
- Terraform code generation (10 files)
- Support for Pulumi, CDK, Bicep, CloudFormation

**Planned Enhancements**:

| Feature | Description | Priority |
|---------|------------|----------|
| Code Quality Scoring | Rate generated code 0-100 on best practices | High |
| Module-based Generation | Use Terraform modules instead of flat resources | High |
| State Backend Config | Auto-configure S3/Blob/GCS state backend | High |
| Variable Validation | Add validation blocks to all variables | Medium |
| Provider Pinning | Pin provider versions for reproducibility | Medium |
| Workspace Support | Multi-environment (dev/staging/prod) | Medium |

### 4.3 Validate Module (Existing — Enhanced)

**Purpose**: Validate and auto-fix generated code

**Current Features**:
- terraform fmt
- terraform init + validate
- checkov security scanning
- Auto-fix loop (5 rounds)

**Planned Enhancements**:

| Feature | Description | Priority |
|---------|------------|----------|
| tfsec Integration | Additional security scanner | High |
| terrascan Integration | Policy-as-code validation | Medium |
| Cost Policy Check | Reject if estimated cost exceeds budget | High |
| Custom Policy Rules | User-defined OPA policies | Medium |
| Dependency Check | Validate all resource references resolve | High |
| Blast Radius Analysis | Show what `terraform apply` will change | Medium |

### 4.4 Deploy Module (NEW)

**Purpose**: Deploy infrastructure directly from IaCraft

**Features**:

| Feature | Description | Priority |
|---------|------------|----------|
| Plan Preview | Run `terraform plan` and show results in dashboard | Critical |
| Apply with Approval | User reviews plan → clicks Apply → real-time logs | Critical |
| Rollback | One-click `terraform destroy` or state rollback | Critical |
| Environment Management | Dev/Staging/Prod with variable overrides | High |
| Deployment History | Log every plan/apply with timestamps and user | High |
| GitOps Mode | Push to Git → auto-deploy via webhook | Medium |
| Dry Run Mode | Simulate deployment without actually applying | High |
| Approval Workflow | Require 2 approvals for production deployments | Medium |

**Technical Design**:
```
User clicks "Deploy"
  │
  ├── terraform init (background)
  ├── terraform plan -out=tfplan
  │     └── Parse plan JSON → show in dashboard
  │         ├── Resources to ADD (green)
  │         ├── Resources to CHANGE (yellow)
  │         └── Resources to DESTROY (red)
  │
  ├── User reviews → clicks "Apply"
  │     └── terraform apply tfplan
  │         └── Stream output to dashboard in real-time
  │
  └── Save deployment record to database
```

**Security Requirements**:
- AWS/Azure/GCP credentials stored encrypted
- MFA required for production deployments
- Audit log of all deployments
- Role-based access (viewer/deployer/admin)

### 4.5 Monitor Module (NEW)

**Purpose**: Post-deployment health monitoring

**Features**:

| Feature | Description | Priority |
|---------|------------|----------|
| Health Dashboard | Show status of all deployed resources | High |
| CloudWatch Integration | Pull metrics from AWS CloudWatch | High |
| Azure Monitor Integration | Pull metrics from Azure Monitor | Medium |
| GCP Monitoring Integration | Pull metrics from GCP Cloud Monitoring | Medium |
| Custom Alerts | Define alert rules in dashboard | High |
| Slack/Teams Notifications | Send alerts to chat channels | Medium |
| Uptime Monitoring | HTTP health checks for endpoints | High |
| Log Aggregation | Pull and display CloudWatch/Azure logs | Medium |

**Metrics to Track**:
- CPU/Memory utilization
- Network throughput
- Database connections
- Error rates (4xx/5xx)
- Response latency (p50/p95/p99)
- Cost per hour/day
- Resource count vs expected

### 4.6 Optimize Module (NEW)

**Purpose**: AI-powered cost and performance optimization

**Features**:

| Feature | Description | Priority |
|---------|------------|----------|
| Cost Anomaly Detection | Alert when daily cost spikes unexpectedly | High |
| Right-sizing Suggestions | "EC2 t3.large is only using 10% CPU → suggest t3.small" | High |
| Reserved Instance Advisor | "You'd save 40% by switching to 1-year reserved" | Medium |
| Unused Resource Finder | "This EBS volume has been detached for 30 days" | High |
| Security Posture Score | Continuous compliance score (0-100) | Medium |
| Performance Suggestions | "Add read replica to reduce DB latency" | Medium |
| One-Click Optimize | Apply suggested optimizations via Terraform | Low |

### 4.7 CI/CD Generator (NEW)

**Purpose**: Auto-generate deployment pipelines

**Supported Platforms**:

| Platform | Output | Priority |
|----------|--------|----------|
| GitHub Actions | `.github/workflows/deploy.yml` | Critical |
| GitLab CI | `.gitlab-ci.yml` | High |
| Jenkins | `Jenkinsfile` | Medium |
| Azure DevOps | `azure-pipelines.yml` | Medium |
| AWS CodePipeline | CloudFormation template | Low |
| Bitbucket Pipelines | `bitbucket-pipelines.yml` | Low |

**Pipeline Stages Generated**:
```yaml
stages:
  - lint        # terraform fmt -check
  - validate    # terraform validate
  - security    # checkov scan
  - plan        # terraform plan
  - approve     # manual approval gate
  - apply       # terraform apply
  - verify      # post-deploy health checks
  - notify      # Slack/Teams notification
```

### 4.8 Drift Detector (NEW)

**Purpose**: Detect when infrastructure drifts from IaC state

**How It Works**:
```
Every N minutes:
  ├── terraform plan (detect changes)
  ├── If drift detected:
  │   ├── Alert user (dashboard + Slack)
  │   ├── Show diff (what changed, who changed it)
  │   ├── Suggest fix:
  │   │   ├── Option A: Update Terraform to match reality
  │   │   └── Option B: Revert reality to match Terraform
  │   └── Auto-remediate if policy allows
  └── Log drift event to history
```

**Drift Types**:
| Type | Example | Severity |
|------|---------|----------|
| Security | Security group rule added manually | Critical |
| Configuration | Instance type changed | High |
| Tags | Tags modified or removed | Medium |
| Resource Added | New resource created outside Terraform | Medium |
| Resource Deleted | Resource deleted outside Terraform | Critical |

### 4.9 AI Chat (NEW)

**Purpose**: Ask natural language questions about your infrastructure

**Examples**:
```
User: "Is my database encrypted?"
AI: "Yes, RDS instance 'web-app-db' has storage_encrypted=true
     using KMS key arn:aws:kms:ap-south-1:xxx:key/xxx"

User: "What would break if I delete the NAT gateway?"
AI: "Private subnet instances would lose internet access.
     This affects: EC2 instances in the ASG, Lambda functions
     that need external API calls."

User: "How can I reduce my monthly cost by 30%?"
AI: "1. Switch EC2 from t3.large to t3.medium (saves $30/mo)
     2. Use reserved instances for RDS (saves $45/mo)
     3. Enable S3 lifecycle to move old data to Glacier (saves $15/mo)
     Total savings: $90/mo (32% reduction)"
```

---

## 5. Data Architecture

### Database Schema

```sql
-- Projects
CREATE TABLE projects (
    id          UUID PRIMARY KEY,
    name        TEXT NOT NULL,
    cloud       TEXT NOT NULL,  -- aws/azure/gcp
    region      TEXT NOT NULL,
    iac_tool    TEXT DEFAULT 'terraform',
    status      TEXT DEFAULT 'draft',  -- draft/deployed/destroyed
    created_at  TIMESTAMP,
    updated_at  TIMESTAMP
);

-- Generations (each pipeline run)
CREATE TABLE generations (
    id          UUID PRIMARY KEY,
    project_id  UUID REFERENCES projects(id),
    message     TEXT NOT NULL,
    provider    TEXT NOT NULL,
    model       TEXT NOT NULL,
    duration_s  FLOAT,
    status      TEXT,  -- complete/error
    results     JSONB,
    created_at  TIMESTAMP
);

-- Deployments
CREATE TABLE deployments (
    id              UUID PRIMARY KEY,
    project_id      UUID REFERENCES projects(id),
    generation_id   UUID REFERENCES generations(id),
    environment     TEXT DEFAULT 'dev',
    plan_output     TEXT,
    apply_output    TEXT,
    status          TEXT,  -- planned/applying/deployed/failed/destroyed
    deployed_by     TEXT,
    deployed_at     TIMESTAMP,
    destroyed_at    TIMESTAMP
);

-- Drift Events
CREATE TABLE drift_events (
    id          UUID PRIMARY KEY,
    project_id  UUID REFERENCES projects(id),
    drift_type  TEXT,  -- security/config/tags/added/deleted
    resource    TEXT,
    details     JSONB,
    severity    TEXT,  -- critical/high/medium/low
    status      TEXT,  -- detected/resolved/ignored
    detected_at TIMESTAMP
);

-- Cost Tracking
CREATE TABLE cost_records (
    id          UUID PRIMARY KEY,
    project_id  UUID REFERENCES projects(id),
    date        DATE,
    estimated   FLOAT,
    actual      FLOAT,
    breakdown   JSONB,
    created_at  TIMESTAMP
);
```

### File Storage

```
data/
├── projects/
│   └── {project-id}/
│       ├── terraform/          # Generated IaC files
│       ├── architecture/       # Design artifacts
│       ├── docs/              # Deployment guides
│       ├── plans/             # Terraform plan outputs
│       ├── deployments/       # Deployment logs
│       └── drift/             # Drift detection reports
├── templates/                 # Reusable architecture templates
└── policies/                  # OPA policy files
```

---

## 6. Security Architecture

### Authentication & Authorization

```
┌─────────────────────────────────────┐
│           Auth Layer                 │
│                                      │
│  ┌──────────┐    ┌───────────────┐  │
│  │ Local    │    │ SSO           │  │
│  │ (user/   │ OR │ (SAML/OIDC)  │  │
│  │  pass)   │    │ Google/Azure  │  │
│  └──────────┘    └───────────────┘  │
│                                      │
│  ┌──────────────────────────────┐   │
│  │ Role-Based Access Control    │   │
│  │                              │   │
│  │  Viewer:   Read-only         │   │
│  │  Developer: Generate + Plan  │   │
│  │  Deployer:  + Apply (non-prod)│  │
│  │  Admin:     + Apply (prod)   │   │
│  │  Owner:     + Settings       │   │
│  └──────────────────────────────┘   │
└─────────────────────────────────────┘
```

### Secrets Management

| Secret Type | Storage | Encryption |
|------------|---------|------------|
| LLM API Keys | .env file (local) / AWS Secrets Manager (cloud) | AES-256 |
| Cloud Credentials | AWS STS / Azure AD / GCP SA | Provider-managed |
| Database | Local SQLite / RDS (cloud) | At-rest encryption |
| TF State | S3 + DynamoDB lock | SSE-KMS |

### Audit Trail

Every action logged:
```json
{
    "timestamp": "2026-04-03T10:30:00Z",
    "user": "admin",
    "action": "terraform_apply",
    "project": "web-app-prod",
    "environment": "production",
    "resources_changed": 5,
    "ip_address": "10.0.1.50",
    "approval": "approved_by: cto@company.com"
}
```

---

## 7. LLM Strategy

### Provider Selection Matrix

| Use Case | Primary | Fallback | Reason |
|----------|---------|----------|--------|
| IaC Generation | Groq (Llama 3.3 70B) | Bedrock (Claude Haiku) | Fast + accurate |
| Code Review | Groq (Llama 3.3 70B) | Bedrock (Llama 70B) | Best for code |
| Documentation | Groq (Llama 3.3 70B) | Gemini Flash | Good writing |
| AI Chat | Groq (Llama 3.3 70B) | Ollama (trio-llm) | Conversational |
| Security Audit | Bedrock (Claude Haiku) | Groq | Best for analysis |

### Cost Projections

| Usage | Groq (Free) | Bedrock Fallback | Total/Month |
|-------|-------------|------------------|-------------|
| 10 runs/day | $0 | $0 (within Groq limits) | **$0** |
| 50 runs/day | $0 (30 on Groq) | $0.20 (20 on Bedrock) | **$6** |
| 200 runs/day | $0 (30 on Groq) | $1.70 (170 on Bedrock) | **$51** |
| 1000 runs/day (team) | $0 | $10 | **$300** |

### Token Budget per Pipeline Run

| Step | Input Tokens | Output Tokens | Total |
|------|-------------|---------------|-------|
| 1. Analyze | ~500 | ~300 | 800 |
| 2-3. Architecture | ~800 | ~500 | 1,300 |
| 4. Mapping | ~600 | ~400 | 1,000 |
| 5. IaC Generation | ~1,200 | ~3,000 | 4,200 |
| 6. Diagram | ~400 | ~300 | 700 |
| 7. Security | ~500 | ~1,000 | 1,500 |
| 8. Compliance | ~800 | ~800 | 1,600 |
| 9. Cost | ~400 | ~600 | 1,000 |
| 10. Validation | ~300 | ~500 | 800 |
| 11. Auto-Fix | ~2,000 | ~2,000 | 4,000 |
| 12. Guide | ~1,000 | ~3,000 | 4,000 |
| **Total** | **~8,500** | **~12,400** | **~20,900** |

At Groq free tier (100K tokens/day): **~4-5 full pipeline runs/day**
At Bedrock Claude Haiku: **~$0.01 per run**

---

## 8. Roadmap

### Phase 1: Foundation (v3.0) — COMPLETE
- [x] NL to IaC pipeline (12 steps)
- [x] 11 LLM providers with auto-fallback
- [x] Code validation + auto-fix
- [x] Multi-cloud comparison
- [x] Deployment guide (4 levels)
- [x] Modern SaaS dashboard
- [x] Login + auth

### Phase 2: Deploy & CI/CD (v4.0) — Q2 2026
- [ ] Terraform plan preview in dashboard
- [ ] One-click terraform apply
- [ ] Deployment history + rollback
- [ ] GitHub Actions pipeline generator
- [ ] GitLab CI pipeline generator
- [ ] Code quality scoring
- [ ] Project database (SQLite)
- [ ] Template library (5 pre-built architectures)

### Phase 3: Monitor & Detect (v4.1) — Q3 2026
- [ ] Drift detection (hourly terraform plan)
- [ ] Health monitoring dashboard
- [ ] CloudWatch/Azure Monitor integration
- [ ] Slack/Teams alert notifications
- [ ] AI Chat ("ask your infra")
- [ ] Cost tracking (estimated vs actual)

### Phase 4: Optimize & Scale (v5.0) — Q4 2026
- [ ] AI cost optimization suggestions
- [ ] Right-sizing recommendations
- [ ] Unused resource finder
- [ ] Security posture scoring
- [ ] Multi-user + team support
- [ ] SSO integration (SAML/OIDC)
- [ ] API for external integrations
- [ ] Terraform Cloud/Enterprise integration

---

## 9. Competitive Analysis

| Feature | IaCraft | Terraform Cloud | Pulumi Cloud | Env0 | Spacelift |
|---------|---------|----------------|-------------|------|-----------|
| NL to IaC | **Yes** | No | No | No | No |
| Multi-Cloud | **Yes** | Yes | Yes | Yes | Yes |
| AI Code Generation | **Yes** | No | AI Assist | No | No |
| Auto-Validation | **Yes** | Sentinel | CrossGuard | OPA | OPA |
| Auto-Fix | **Yes** | No | No | No | No |
| Multi-Cloud Compare | **Yes** | No | No | No | No |
| Deploy from UI | Planned | Yes | Yes | Yes | Yes |
| Drift Detection | Planned | Yes | Yes | Yes | Yes |
| Cost Estimation | **Yes** | Yes | No | Yes | No |
| AI Chat | Planned | No | No | No | No |
| Self-Hosted | **Yes** | No | No | No | No |
| Free Tier | **Yes (Groq)** | Limited | Limited | Limited | Limited |
| 11 LLM Providers | **Yes** | N/A | 1 | N/A | N/A |

**IaCraft's Unique Differentiator**: The only platform that converts natural language to validated, deployment-ready IaC with AI-powered auto-fix — across 3 clouds, 5 IaC tools, and 11 LLM providers.

---

## 10. Infrastructure Requirements

### Self-Hosted (Current)

| Component | Requirement |
|-----------|-------------|
| CPU | 2+ cores |
| RAM | 4GB minimum |
| Disk | 10GB |
| Python | 3.9+ |
| Terraform | 1.5+ |
| Network | Outbound HTTPS (for LLM APIs) |

### Production Deployment

| Component | Recommended |
|-----------|------------|
| Server | 4 CPU, 8GB RAM |
| Database | PostgreSQL 15+ (or SQLite for single-user) |
| State Store | S3 bucket with versioning |
| Monitoring | CloudWatch / Prometheus + Grafana |
| CI/CD | GitHub Actions |
| SSL | Let's Encrypt / ACM |

### Scaling Strategy

```
Single User    →  SQLite + Local files
Small Team     →  PostgreSQL + S3 state
Enterprise     →  PostgreSQL + S3 + Redis cache + Load balancer
```

---

## 11. Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| LLM generates insecure code | High | Medium | checkov + tfsec validation, policy engine |
| LLM rate limits during deployment | Medium | High | Auto-fallback chain, queue system |
| Terraform state corruption | Critical | Low | State locking, versioned backups |
| Unauthorized deployment | Critical | Low | RBAC, approval workflows, audit log |
| Cloud credential exposure | Critical | Low | Secrets manager, no credentials in code |
| AI hallucination in suggestions | Medium | Medium | Validate all AI output, human review |
| Cost overrun from deployment | High | Medium | Cost policy checks before apply |

---

## 12. Success Metrics

| Metric | Current | Target (v4.0) | Target (v5.0) |
|--------|---------|---------------|---------------|
| Time to generate IaC | 42s | 42s | 30s |
| Code validation pass rate | ~70% | 90% | 95% |
| Deployment success rate | N/A | 85% | 95% |
| Drift detection time | N/A | <1 hour | <15 min |
| Cost estimation accuracy | ~60% | 80% | 90% |
| User satisfaction | N/A | 4/5 | 4.5/5 |
| Monthly active projects | N/A | 50 | 500 |

---

> **IaCraft Platform** — From natural language to self-healing infrastructure.
> This document is a living architecture guide and will be updated as the platform evolves.
