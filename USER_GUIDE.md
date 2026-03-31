# IaCraft v2.0 — User Guide

## Craft Cloud Infrastructure from Natural Language

---

## Table of Contents

1. [Overview](#1-overview)
2. [Quick Start](#2-quick-start)
3. [Installation](#3-installation)
4. [Dashboard Guide](#4-dashboard-guide)
5. [LLM Providers Setup](#5-llm-providers-setup)
6. [Generating Infrastructure](#6-generating-infrastructure)
7. [Understanding the Output](#7-understanding-the-output)
8. [Code Simulator](#8-code-simulator)
9. [Multi-Cloud Comparison](#9-multi-cloud-comparison)
10. [Deployment Guide Generation](#10-deployment-guide-generation)
11. [CLI Reference](#11-cli-reference)
12. [Settings & API Keys](#12-settings--api-keys)
13. [Architecture](#13-architecture)
14. [Troubleshooting](#14-troubleshooting)

---

## 1. Overview

IaCraft converts plain English descriptions of cloud infrastructure into production-ready Infrastructure as Code (IaC). It runs a 12-step AI pipeline that generates:

- Terraform / Pulumi / CDK / Bicep code
- Architecture diagrams (Mermaid)
- Security controls & compliance mapping
- Cost estimates
- Deployment guides
- Auto-validated and auto-fixed code

### Supported Clouds
- AWS
- Azure
- GCP

### Supported IaC Tools
- Terraform (default)
- Pulumi
- AWS CloudFormation
- AWS CDK
- Azure Bicep

### Supported LLM Providers (11)
| Provider | Cost | Speed | Best For |
|----------|------|-------|----------|
| Groq | FREE | ~42s | Daily use |
| Gemini | FREE | ~3 min | Backup |
| Together AI | $25 free | ~1 min | High quality |
| Mistral | Free tier | ~1 min | Code |
| DeepSeek | ~$0.001 | ~1 min | Cheapest paid |
| Cohere | Free trial | ~2 min | General |
| OpenAI | ~$0.03 | ~1 min | Best quality |
| Claude | ~$0.15 | ~30s | Best quality |
| AWS Bedrock | ~$0.002 | ~1 min | Enterprise |
| Azure OpenAI | ~$0.03 | ~1 min | Enterprise |
| Ollama | FREE | Varies | Self-hosted |

---

## 2. Quick Start

### Fastest setup (2 minutes):

```bash
# 1. Clone and install
cd IaCraft
pip install -r requirements.txt

# 2. Get a free Groq API key
# Visit: https://console.groq.com/keys
# Copy the key (starts with gsk_)

# 3. Create .env file
echo "GROQ_API_KEY=gsk_your-key-here" > .env

# 4. Launch dashboard
python run_dashboard.py

# 5. Open browser
# http://localhost:15000
# Login: admin / admin123
```

### Generate your first infrastructure:

1. Open http://localhost:15000
2. Login with `admin` / `admin123`
3. Select **Groq** as provider
4. Type: `Create an EC2 instance with application load balancer`
5. Click **Generate IaC**
6. Wait ~42 seconds
7. Browse all tabs: Architecture, IaC Code, Diagram, Security, Cost, etc.

---

## 3. Installation

### Prerequisites
- Python 3.9+
- pip

### Install dependencies

```bash
pip install -r requirements.txt
```

### Required packages
| Package | Purpose |
|---------|---------|
| anthropic | Claude API |
| openai | OpenAI + Azure OpenAI + DeepSeek + Together |
| google-genai | Google Gemini API |
| groq | Groq API |
| mistralai | Mistral API |
| cohere | Cohere API |
| boto3 | AWS Bedrock |
| fastapi | Web dashboard |
| uvicorn | Web server |
| click | CLI |
| rich | CLI formatting |
| httpx | HTTP client (Ollama) |
| checkov | Security scanning |

### Optional: Install as CLI tool

```bash
pip install -e .
iacraft --version
```

### Optional: Install Terraform (for code simulator)

```bash
# Windows
winget install HashiCorp.Terraform

# Mac
brew install terraform

# Linux
sudo apt install terraform
```

---

## 4. Dashboard Guide

### Starting the dashboard

```bash
python run_dashboard.py
# Opens on http://localhost:15000
```

Or via CLI:

```bash
python main.py dashboard
```

### Login

| Username | Password | Description |
|----------|----------|-------------|
| admin | admin123 | Full access |
| guest | guest | Guest access |

Change admin password in `.env`:
```
ADMIN_PASSWORD=your-secure-password
```

### Dashboard Layout

```
+-------------------+----------------------------------------+
|                   |  [Message Input]                       |
|  LLM Provider     |  [Presets: 3-Tier | K8s | Serverless] |
|  - Provider       |  [Generate IaC]  [Download ZIP]        |
|  - Model          |  [Progress Bar]                        |
|  - API Key        |                                        |
|                   |  [Tabs]                                |
|  Infrastructure   |  Pipeline Logs | Architecture | IaC    |
|  - Cloud          |  Diagram | Security | Compliance       |
|  - IaC Tool       |  Cost | Validation | Simulator         |
|  - Region         |  Deployment Guide | Compare Clouds     |
|                   |                                        |
|  Documentation    |  [Tab Content Area]                    |
|  - Guide Level    |                                        |
+-------------------+----------------------------------------+
```

### Theme Toggle
Click **"Light"/"Dark"** button in the header to switch themes.

### Settings (API Keys)
Click **"Settings"** button in the header to manage all API keys.

---

## 5. LLM Providers Setup

### Groq (Recommended — FREE)

1. Visit https://console.groq.com/keys
2. Sign up (free, no credit card)
3. Create API key
4. In dashboard: Settings → Groq → paste key → Save

Or in `.env`:
```
GROQ_API_KEY=gsk_your-key-here
```

### Google Gemini (FREE)

1. Visit https://aistudio.google.com/apikey
2. Click "Create API Key"
3. In dashboard: Settings → Gemini → paste key → Save

### Ollama (Self-hosted, FREE)

```bash
# Install
curl -fsSL https://ollama.com/install.sh | sh

# Start
ollama serve

# Pull a model
ollama pull qwen2.5-coder:7b
```

For remote Ollama:
```bash
# On the server
OLLAMA_HOST=0.0.0.0 ollama serve

# In IaCraft dashboard
# Set Ollama URL to: http://server-ip:11434
```

### Other Providers

Each provider has a "Get key" link in Settings. Paste the key and click Save — it's stored in your local `.env` file.

---

## 6. Generating Infrastructure

### Step 1: Write your requirement

Use plain English. Examples:

| Input | What it generates |
|-------|------------------|
| "EC2 instance with ALB" | VPC, subnets, EC2, ALB, security groups |
| "3-tier web app with PostgreSQL and Redis" | VPC, ALB, ASG, RDS, ElastiCache, CloudFront |
| "Kubernetes cluster with CI/CD" | EKS/AKS/GKE, node groups, CodePipeline/Azure DevOps |
| "Serverless API with DynamoDB" | Lambda, API Gateway, DynamoDB, IAM |
| "Data pipeline with S3, Glue, Redshift" | S3, Glue jobs, Redshift cluster, IAM |

### Step 2: Configure options

- **Provider**: Which LLM to use (Groq recommended)
- **Model**: Which model (Llama 3.3 70B recommended)
- **Cloud**: AWS / Azure / GCP
- **IaC Tool**: Terraform / Pulumi / CDK / Bicep
- **Region**: Auto-detected or manual
- **Guide Level**: Quick / Standard / Enterprise / Compliance

### Step 3: Click "Generate IaC"

The 12-step pipeline runs:

| Step | Name | Time (Groq) |
|------|------|------------|
| 1 | Requirement Analysis | ~1s |
| 2-3 | Architecture Design | ~1s |
| 4 | Cloud Service Mapping | ~1s |
| 5 | IaC Code Generation | ~6s |
| 6 | Architecture Diagram | ~1s |
| 7 | Security Controls | ~3s |
| 8 | Compliance Mapping | ~2s |
| 9 | Cost Estimation | ~2s |
| 10 | Validation Plan | ~2s |
| 11 | Auto-Fix Loop | ~20s |
| 12 | Deployment Guide | ~10s |
| **Total** | | **~42s** |

### Step 4: Review outputs

Browse the tabs to see all generated artifacts.

---

## 7. Understanding the Output

### Tab: Pipeline Logs
Real-time progress of each step.

### Tab: Architecture
- `architecture.json` — cloud-agnostic architecture definition
- `cloud-mapping.json` — mapping to real cloud services

### Tab: IaC Code
All generated Terraform files with copy buttons:
- `providers.tf` — provider configuration
- `variables.tf` — input variables
- `networking.tf` — VPC, subnets, security groups
- `compute.tf` — EC2, ASG, launch templates
- `database.tf` — RDS, DynamoDB
- `storage.tf` — S3, EBS
- `security.tf` — IAM roles, KMS
- `monitoring.tf` — CloudWatch
- `outputs.tf` — output values
- `terraform.tfvars` — variable values

### Tab: Diagram
Mermaid architecture diagram — visual representation of your infrastructure.

### Tab: Security
Security controls covering:
- IAM & access control
- Network security
- Encryption (at rest + in transit)
- Secrets management
- Logging & auditing

### Tab: Compliance
Mapping to compliance frameworks:
- SOC2 Trust Service Criteria
- ISO 27001 Annex A
- CIS Benchmarks

### Tab: Cost
Monthly cost estimate with:
- Service-by-service breakdown
- Annual projection
- Optimization recommendations

### Tab: Validation
How to validate the code:
- `terraform validate` commands
- Checkov/tfsec scan commands
- Pre-deployment checklist

### Tab: Deployment Guide
Professional deployment document (2-20+ pages based on selected level).

### Download ZIP
Click "Download ZIP" to get all files in one archive.

### Output Directory Structure
```
output/
├── terraform/          # IaC files
├── architecture/       # JSON, diagrams, reports
├── validation/         # Validation plans
├── docs/              # Deployment guide
└── REPORT.md          # Combined report
```

---

## 8. Code Simulator

The simulator validates generated Terraform code and auto-fixes issues.

### How to use:
1. Generate IaC first
2. Click **"Simulator"** tab
3. Click **"Run Simulator"**

### What it does:
```
Round 1: Validate
├── terraform fmt     → auto-fix formatting
├── terraform init    → download providers
├── terraform validate → check syntax/references
└── checkov scan      → security checks (20+ CKV rules)

Errors found? → Send to LLM for auto-fix

Round 2: Re-validate
├── terraform fmt     ✓
├── terraform init    ✓
├── terraform validate ✓
└── checkov scan      → fewer errors

... up to 5 rounds
```

### Requirements:
- Terraform CLI installed
- Checkov installed (`pip install checkov`)

---

## 9. Multi-Cloud Comparison

Compare infrastructure across AWS, Azure, and GCP side-by-side.

### How to use:
1. Type your requirement
2. Click **"Compare Clouds"** tab
3. Click **"Compare All Clouds"**

### What you get:
- Three pipelines run (one per cloud)
- Side-by-side service comparison
- Cost comparison
- Recommendation for which cloud is best

---

## 10. Deployment Guide Generation

### Documentation Levels:

| Level | Pages | Sections | Audience |
|-------|-------|----------|----------|
| **Quick Start** | 2-3 | Summary, Prerequisites, Deploy | Developer |
| **Standard** | 8-10 | + Architecture, Resources, Security, Cost | Team |
| **Enterprise** | 20+ | + DR, Troubleshooting, Rollback, Operations | CTO/CISO |
| **Compliance** | 15+ | + SOC2/ISO27001/CIS control mapping | Auditors |

### Sections included:

1. Executive Summary
2. Architecture Overview (with diagram)
3. Prerequisites (install commands)
4. Resource Inventory (every resource listed)
5. Step-by-Step Deployment
6. Post-Deployment Validation
7. Security Configuration
8. Monitoring & Alerting
9. Cost Analysis
10. Backup & Disaster Recovery
11. Troubleshooting Guide
12. Rollback Procedure
13. Maintenance & Operations
14. Appendix
15. Compliance Controls Mapping (compliance level only)

---

## 11. CLI Reference

### Commands

```bash
# Generate IaC
iacraft generate "Your requirement here"
iacraft generate --provider groq --cloud aws "EC2 with ALB"
iacraft generate --cloud azure --iac pulumi "Web app with SQL"
iacraft generate --simulate "EC2 with ALB"  # Generate + validate

# Run code simulator
iacraft simulate
iacraft simulate -o output

# Quick analysis (Step 1 only)
iacraft analyze "ML platform with GPU"

# Show providers
iacraft providers

# Launch dashboard
iacraft dashboard
iacraft dashboard --port 8080
```

### Options

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--provider` | `-p` | LLM provider | groq |
| `--cloud` | `-c` | Cloud (aws/azure/gcp) | aws |
| `--iac` | `-i` | IaC tool | terraform |
| `--region` | `-r` | Cloud region | ap-south-1 |
| `--output` | `-o` | Output directory | output/ |
| `--model` | `-m` | Model name | auto |
| `--simulate` | | Run simulator after | false |
| `--ollama-url` | | Ollama server URL | localhost:11434 |

---

## 12. Settings & API Keys

### Dashboard Settings
Click **"Settings"** in the header to manage API keys for all 11 providers.

### .env File
All keys are stored in `.env` in the project root:

```env
# Free providers (recommended)
GROQ_API_KEY=gsk_...
GEMINI_API_KEY=AIza...

# Self-hosted
OLLAMA_BASE_URL=http://localhost:11434

# Paid providers (optional)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
MISTRAL_API_KEY=...
DEEPSEEK_API_KEY=...
COHERE_API_KEY=...
TOGETHER_API_KEY=...

# Enterprise (optional)
AZURE_OPENAI_ENDPOINT=https://...
AZURE_OPENAI_API_KEY=...
AWS_REGION=us-east-1

# Dashboard
ADMIN_PASSWORD=admin123
```

### Auto-Fallback
If a provider hits rate limits, IaCraft automatically switches to the next available provider:

```
Groq → Gemini → Together → Ollama
```

---

## 13. Architecture

### Project Structure

```
IaCraft/
├── main.py                  # CLI entry point
├── run_dashboard.py         # Dashboard launcher (port 15000)
├── setup.py                 # Package installer
├── requirements.txt         # Dependencies
├── .env                     # API keys (not in git)
├── .env.example             # Template
├── USER_GUIDE.md            # This file
├── README.md                # Quick reference
└── src/
    ├── __init__.py           # Version info
    ├── cli.py                # Click CLI commands
    ├── config.py             # Configuration & constants
    ├── engine.py             # 12-step pipeline orchestrator
    ├── llm_client.py         # 11 LLM provider clients + fallback
    ├── file_writer.py        # Output parser & file writer
    ├── validator.py          # Terraform validator + auto-fix
    ├── multi_cloud.py        # Multi-cloud comparison engine
    ├── doc_generator.py      # Deployment guide generator
    ├── prompts/
    │   └── system_prompts.py # AI prompts for each step
    └── dashboard/
        ├── __init__.py
        ├── app.py            # FastAPI backend
        ├── static/           # Logo SVGs
        └── templates/
            ├── login.html    # Glass-themed login page
            └── dashboard.html # Main dashboard UI
```

### Pipeline Flow

```
User Message
    ↓
Step 1:  Analyze requirements (JSON)
Step 2-3: Abstract architecture (cloud-agnostic JSON)
Step 4:  Map to cloud services (AWS/Azure/GCP)
Step 5:  Generate IaC code (Terraform files)
Step 6:  Create Mermaid diagram
Step 7:  Define security controls
Step 8:  Map compliance frameworks
Step 9:  Estimate costs
Step 10: Create validation plan
Step 11: Auto-fix loop (detect + fix issues)
Step 12: Generate deployment guide
    ↓
Output: Complete IaC project + documentation
```

---

## 14. Troubleshooting

### Dashboard won't start
```bash
# Port in use — run_dashboard.py auto-kills old processes
python run_dashboard.py

# If still failing, kill manually:
# PowerShell (Admin):
Get-Process python* | Stop-Process -Force
```

### Rate limit errors
IaCraft auto-falls back to the next provider. If all providers are rate-limited:
- Wait a few minutes
- Or add another provider's API key in Settings

### Terraform not found
```bash
# Windows
winget install HashiCorp.Terraform

# Mac
brew install terraform

# Verify
terraform --version
```

### Groq daily limit (100K tokens)
Free tier resets daily. Options:
- Wait for reset
- Add Gemini key (free, separate quota)
- Use Ollama (unlimited, self-hosted)

### Generated code has errors
1. Run the **Simulator** tab to auto-fix
2. Use a larger model (Llama 3.3 70B > 8B)
3. Use Enterprise doc level for more detailed code

### Ollama connection refused
```bash
# Make sure Ollama is running
ollama serve

# For remote access
OLLAMA_HOST=0.0.0.0 ollama serve
```

---

> **IaCraft v2.0** — Craft Cloud Infrastructure from Natural Language
> 11 LLM Providers | AWS / Azure / GCP | Enterprise Grade
