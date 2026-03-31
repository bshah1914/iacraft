# message-to-iaac

Convert natural language into production-ready Infrastructure as Code.

## What It Does

Takes a plain English description of your infrastructure needs and generates:

- **Terraform/Pulumi/CDK/Bicep code** — deployment-ready, no placeholders
- **Architecture diagram** — Mermaid format
- **Security controls** — IAM, encryption, networking, secrets
- **Compliance mapping** — SOC2, ISO27001, CIS benchmarks
- **Cost estimation** — monthly USD breakdown
- **Validation plan** — terraform validate, Checkov, tfsec
- **Auto-fix report** — detects and corrects misconfigurations

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set up an LLM provider

**Option A — Ollama (default, free, local):**

```bash
# Install from https://ollama.com/download
ollama serve
ollama pull qwen2.5-coder:3b    # ~2GB, good quality/size balance
```

**Option B — Claude API:**

```bash
export ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### 3. Run

**Web Dashboard (recommended):**

```bash
python main.py dashboard
# Open http://localhost:8000
```

**CLI:**

```bash
python main.py generate "Deploy a 3-tier web app with PostgreSQL and Redis on AWS"
```

## Web Dashboard

The dashboard provides a full UI for configuring and running the pipeline.

```bash
python main.py dashboard
# or
python main.py dashboard --port 3000
```

### Dashboard Features

- **LLM Provider panel** — switch between Ollama and Claude, select models
- **Ollama status widget** — live connection check, shows installed models as clickable cards
- **Infrastructure settings** — cloud provider, IaC tool, region, output directory
- **Preset templates** — one-click examples (3-tier web, microservices, serverless, etc.)
- **Real-time progress** — live step-by-step pipeline logs via Server-Sent Events
- **Tabbed output** — Architecture, IaC Code, Diagram, Security, Compliance, Cost, Validation
- **Copy to clipboard** — on all generated code blocks

## CLI Usage

### Generate full infrastructure

```bash
# Ollama (default — no API key needed)
python main.py generate "Scalable microservices platform with CI/CD"

# Claude API
python main.py generate --provider claude "Scalable microservices"

# Azure + custom model
python main.py generate --cloud azure --model llama3:8b "Web app with SQL"

# GCP + Pulumi
python main.py generate --cloud gcp --iac pulumi "Data pipeline with BigQuery"

# Custom region and output directory
python main.py generate --region us-east-1 --output my-infra "E-commerce platform"
```

### Quick analysis only

```bash
python main.py analyze "AI inference platform with GPU instances"
```

### Show supported providers

```bash
python main.py providers
```

## CLI Options

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--provider` | `-p` | LLM provider (ollama/claude) | ollama |
| `--cloud` | `-c` | Cloud provider (aws/azure/gcp) | aws |
| `--iac` | `-i` | IaC tool (terraform/pulumi/cloudformation/cdk/bicep) | terraform |
| `--region` | `-r` | Cloud region | ap-south-1 |
| `--output` | `-o` | Output directory | output/ |
| `--model` | `-m` | Model name (auto per provider) | qwen2.5-coder:7b |
| `--ollama-url` | | Ollama server URL | http://localhost:11434 |

## Ollama Models (by size)

| Model | Size | Quality for IaC |
|-------|------|-----------------|
| `qwen2.5-coder:1.5b` | ~1 GB | Basic |
| `qwen2.5-coder:3b` | ~2 GB | Good — recommended for low disk |
| `phi3:mini` | ~2.3 GB | Decent |
| `qwen2.5-coder:7b` | ~4.5 GB | Best |
| `codellama:7b` | ~3.8 GB | Good |
| `deepseek-coder:6.7b` | ~3.8 GB | Good |

## Output Structure

```
output/
├── terraform/              # Generated IaC files
│   ├── providers.tf
│   ├── variables.tf
│   ├── networking.tf
│   ├── compute.tf
│   ├── database.tf
│   ├── storage.tf
│   ├── security.tf
│   ├── monitoring.tf
│   ├── outputs.tf
│   └── terraform.tfvars
├── architecture/           # Design artifacts
│   ├── architecture.json
│   ├── requirement-analysis.json
│   ├── cloud-mapping.json
│   ├── cloud-mapping.md
│   ├── diagram.mmd
│   ├── security-controls.md
│   ├── compliance.md
│   └── cost-estimate.md
├── validation/             # Validation artifacts
│   ├── validation-plan.md
│   └── auto-fix-report.md
└── REPORT.md               # Combined report
```

## The 11-Step Pipeline

| Step | Name | Output | Critical |
|------|------|--------|----------|
| 1 | Requirement Analysis | requirement-analysis.json | Yes |
| 2-3 | Service Abstraction | architecture.json | Yes |
| 4 | Cloud Mapping | cloud-mapping.json | Yes |
| 5 | IaC Generation | terraform/*.tf | Yes |
| 6 | Architecture Diagram | diagram.mmd | No |
| 7 | Security Controls | security-controls.md | No |
| 8 | Compliance Mapping | compliance.md | No |
| 9 | Cost Estimation | cost-estimate.md | No |
| 10 | Validation Plan | validation-plan.md | No |
| 11 | Auto-Fix Loop | auto-fix-report.md | No |

Steps 1-5 are critical — the pipeline stops if they fail. Steps 6-11 are non-critical — errors are logged but the pipeline continues.

## Install as CLI tool

```bash
pip install -e .
```

Then use anywhere:

```bash
message-to-iaac generate "Your infrastructure requirement here"
message-to-iaac dashboard
m2iac generate "Your infrastructure requirement here"
```

## Requirements

- Python 3.9+
- Ollama (for local LLM) or Anthropic API key (for Claude)
