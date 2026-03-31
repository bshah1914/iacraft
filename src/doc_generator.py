"""Enterprise Deployment Guide Generator.

Auto-generates a comprehensive, professional deployment document
after the pipeline completes. Includes architecture overview,
prerequisites, step-by-step deployment, security checklist,
monitoring setup, troubleshooting, and cleanup.
"""

import os
import json
from datetime import datetime
from typing import Dict, Optional, Callable

from .llm_client import LLMClient
from .prompts.system_prompts import MASTER_SYSTEM_PROMPT


DOC_LEVELS = {
    "quick": {
        "name": "Quick Start",
        "description": "Basic deployment steps — 2-3 pages",
        "sections": [1, 3, 5],  # Summary, Prerequisites, Deploy
        "max_tokens": 1024,
    },
    "standard": {
        "name": "Standard",
        "description": "Complete guide with security and monitoring — 8-10 pages",
        "sections": [1, 2, 3, 4, 5, 6, 7, 8, 9],
        "max_tokens": 2048,
    },
    "enterprise": {
        "name": "Enterprise",
        "description": "Full enterprise guide with DR, troubleshooting, runbooks — 20+ pages",
        "sections": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14],
        "max_tokens": 3072,
    },
    "compliance": {
        "name": "Compliance & Audit",
        "description": "Compliance-focused with SOC2/ISO27001/HIPAA controls — 15+ pages",
        "sections": [1, 2, 3, 4, 5, 7, 8, 9, 15],  # 15 = compliance deep-dive
        "max_tokens": 3072,
    },
}

DOC_SYSTEM_PROMPTS = {
    "quick": """You are a DevOps engineer writing a quick-start deployment guide.
Be concise and direct. Only include essential commands and steps.
Skip explanations — just actionable steps with code blocks.""",

    "standard": """You are a Senior Cloud Solutions Architect writing deployment documentation.
Write in a professional, clear tone. Use proper technical terminology.
Structure with headings, numbered steps, tables, and code blocks.
Every instruction must be actionable and copy-pasteable.""",

    "enterprise": """You are a Principal Cloud Architect writing enterprise deployment documentation
for a Fortune 500 company. This document will be reviewed by CTO, CISO, and compliance teams.
Write in formal, precise language. Include:
- Risk assessments for each section
- Approval checkpoints
- Change management references
- SLA/SLO definitions
- RACI matrix references
Every instruction must be actionable, auditable, and include rollback steps.""",

    "compliance": """You are a Cloud Security Architect writing compliance-focused deployment documentation.
Map every control to SOC2 Trust Service Criteria, ISO 27001 Annex A, and CIS Benchmarks.
Include evidence collection instructions for each control.
Reference specific control IDs (CC6.1, A.12.4, CIS 2.1.1, etc.).
Format for audit readiness — every section must be verifiable.""",
}


def generate_deployment_guide(
    results: Dict,
    config,
    output_dir: str = "output",
    llm: Optional[LLMClient] = None,
    on_status: Optional[Callable] = None,
    doc_level: str = "standard",
) -> str:
    """Generate a deployment guide at the specified documentation level.

    doc_level: quick | standard | enterprise | compliance
    Returns the full markdown document.
    """
    status = on_status or (lambda msg: print(f"  [Doc] {msg}"))

    level_config = DOC_LEVELS.get(doc_level, DOC_LEVELS["standard"])
    system_prompt = DOC_SYSTEM_PROMPTS.get(doc_level, DOC_SYSTEM_PROMPTS["standard"])
    active_sections = level_config["sections"]
    max_tok = level_config["max_tokens"]

    status(f"Generating {level_config['name']} guide ({level_config['description']})...")

    if not llm:
        llm = LLMClient(
            provider=config.provider,
            model=config.model,
            ollama_url=config.ollama_url,
        )

    analysis = results.get("analysis", {})
    architecture = results.get("architecture", {})
    mapping = results.get("mapping", {})
    iac_files = results.get("iac_files", [])
    security = results.get("security", "")
    cost = results.get("cost", "")
    diagram = results.get("diagram", "")

    services = [m.get("service", "") for m in mapping.get("mappings", [])]
    cloud = config.cloud.upper()
    region = config.region
    iac_tool = config.iac_tool
    app_type = analysis.get("app_type", "cloud application")
    availability = analysis.get("availability", "multi-az")
    summary = analysis.get("summary", "")

    # Build the guide section by section using LLM
    sections = []

    # =================== COVER PAGE ===================
    now = datetime.now().strftime("%B %d, %Y")
    cover = f"""# Deployment Guide
## {app_type.title()} on {cloud}

| | |
|---|---|
| **Document Type** | {level_config['name']} Deployment Guide |
| **Documentation Level** | {doc_level.upper()} — {level_config['description']} |
| **Cloud Provider** | {cloud} |
| **Region** | {region} |
| **IaC Tool** | {iac_tool.title()} |
| **Availability** | {availability} |
| **Generated** | {now} |
| **Generator** | IaCraft v2.0 |
| **Classification** | Internal — Technical |

---
"""
    sections.append(cover)

    # =================== TABLE OF CONTENTS ===================
    toc = """## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architecture Overview](#2-architecture-overview)
3. [Prerequisites](#3-prerequisites)
4. [Resource Inventory](#4-resource-inventory)
5. [Deployment Instructions](#5-deployment-instructions)
6. [Post-Deployment Validation](#6-post-deployment-validation)
7. [Security Configuration](#7-security-configuration)
8. [Monitoring & Alerting](#8-monitoring--alerting)
9. [Cost Analysis](#9-cost-analysis)
10. [Backup & Disaster Recovery](#10-backup--disaster-recovery)
11. [Troubleshooting Guide](#11-troubleshooting-guide)
12. [Rollback Procedure](#12-rollback-procedure)
13. [Maintenance & Operations](#13-maintenance--operations)
14. [Appendix](#14-appendix)

---
"""
    sections.append(toc)

    # Section definitions: (num, name, prompt_builder)
    file_names = [os.path.basename(str(f)) for f in iac_files]
    svc_list = ', '.join(services)

    section_defs = {
        1: ("Executive Summary", f"Write Section 1: Executive Summary.\nApp: {app_type}\nCloud: {cloud} in {region}\nSummary: {summary}\nServices: {svc_list}\nAvailability: {availability}\n\nInclude: project overview, business objectives, technical scope, key decisions, expected outcomes.\nFormat: ## 1. Executive Summary"),

        2: ("Architecture Overview", f"Write Section 2: Architecture Overview.\nArchitecture: {json.dumps(architecture, indent=2)[:1500]}\nServices: {svc_list}\nCloud: {cloud}\n\nInclude: high-level description, component table (| Component | Service | Purpose | Tier |), data flow, network topology.\nFormat: ## 2. Architecture Overview"),

        3: ("Prerequisites", f"Write Section 3: Prerequisites for {iac_tool} on {cloud}.\nInclude: required software with install commands (Linux/Mac/Windows), {cloud} account + IAM permissions, CLI auth commands, state backend setup.\nFormat: ## 3. Prerequisites"),

        4: ("Resource Inventory", f"Write Section 4: Resource Inventory.\nServices: {json.dumps(mapping.get('mappings', []), indent=2)[:1500]}\nCloud: {cloud}\n\nCreate table: | # | Resource Type | Name | Configuration | Purpose | Cost |\nGroup by: Compute, Network, Database, Security, Monitoring.\nFormat: ## 4. Resource Inventory"),

        5: ("Deployment Instructions", f"Write Section 5: Step-by-Step Deployment.\nIaC: {iac_tool}, Cloud: {cloud}, Region: {region}, Files: {', '.join(file_names)}\n\nInclude: 5.1 Setup, 5.2 Configure variables, 5.3 terraform init, 5.4 terraform plan, 5.5 terraform apply, 5.6 Verify.\nEvery command copy-pasteable.\nFormat: ## 5. Deployment Instructions"),

        6: ("Post-Deployment Validation", f"Write Section 6: Post-Deployment Validation for {cloud}.\nServices: {svc_list}\n\nInclude: connectivity tests, health checks, security group verification, DNS, load balancer, database, monitoring.\nFormat as checklist with commands.\nFormat: ## 6. Post-Deployment Validation"),

        7: ("Security Configuration", f"Write Section 7: Security Configuration.\nControls: {security[:2000]}\n\nStructure: 7.1 IAM, 7.2 Network, 7.3 Encryption, 7.4 Secrets, 7.5 Compliance Status.\nEach: what's configured, manual actions, verification command.\nAdd compliance table.\nFormat: ## 7. Security Configuration"),

        8: ("Monitoring & Alerting", f"Write Section 8: Monitoring & Alerting for {cloud}.\nServices: {svc_list}\n\nInclude: 8.1 Log Groups, 8.2 Dashboards, 8.3 Alerts table (| Alert | Condition | Severity | Action |), 8.4 On-Call.\nFormat: ## 8. Monitoring & Alerting"),

        9: ("Cost Analysis", f"Write Section 9: Cost Analysis.\nData: {cost[:1500]}\n\nInclude: 9.1 Monthly breakdown table, 9.2 Annual projection, 9.3 Optimization (reserved, spot, right-sizing), 9.4 Budget alerts setup.\nFormat: ## 9. Cost Analysis"),

        10: ("Backup & DR", f"Write Section 10: Backup & Disaster Recovery for {cloud}.\nServices: {svc_list}\n\nInclude: backup strategy per resource, RTO/RPO targets, DR procedures, failover steps.\nFormat: ## 10. Backup & Disaster Recovery"),

        11: ("Troubleshooting", f"Write Section 11: Troubleshooting Guide for {cloud} {iac_tool}.\n\nInclude table with 8+ issues: | Issue | Symptom | Cause | Resolution |\nCover: auth errors, network issues, resource limits, terraform state, DNS, permissions.\nFormat: ## 11. Troubleshooting Guide"),

        12: ("Rollback Procedure", f"Write Section 12: Rollback Procedure using {iac_tool}.\n\nInclude: step-by-step terraform rollback, state management, data rollback, communication template.\nFormat: ## 12. Rollback Procedure"),

        13: ("Maintenance & Operations", f"Write Section 13: Maintenance & Operations.\n\nInclude: patching schedule, scaling procedures, certificate rotation, key rotation, compliance reviews.\nFormat: ## 13. Maintenance & Operations"),

        14: ("Appendix", f"Write Section 14: Appendix.\n\nInclude: glossary of terms, {cloud} reference links, change log template, contact list template.\nFormat: ## 14. Appendix"),

        15: ("Compliance Deep-Dive", f"Write Section 15: Compliance Controls Mapping.\nSecurity controls: {security[:2000]}\n\nMap EVERY control to:\n- SOC2 Trust Service Criteria (CC6.1, CC7.2, etc.)\n- ISO 27001 Annex A (A.9.1, A.12.4, etc.)\n- CIS {cloud} Benchmarks (specific IDs)\n\nFormat as: | Control | SOC2 | ISO27001 | CIS | Evidence | Status |\nInclude evidence collection instructions.\nFormat: ## 15. Compliance Controls Mapping"),
    }

    # Generate each active section
    for sec_num in sorted(active_sections):
        if sec_num not in section_defs:
            continue
        sec_name, sec_prompt = section_defs[sec_num]
        status(f"Generating {sec_name}...")
        try:
            result = llm.generate(system_prompt, sec_prompt, max_tokens=max_tok)
            # Special handling for architecture diagram
            if sec_num == 2 and diagram:
                mermaid_clean = diagram.strip()
                if '```mermaid' not in mermaid_clean:
                    mermaid_clean = "```mermaid\n" + mermaid_clean + "\n```"
                result += "\n\n### Architecture Diagram\n\n" + mermaid_clean
            sections.append(result + "\n\n---\n\n")
        except Exception as e:
            status(f"  Warning: {sec_name} generation failed: {e}")
            sections.append(f"## {sec_num}. {sec_name}\n\n*Generation failed: {e}*\n\n---\n\n")

    # =================== ASSEMBLE FULL DOCUMENT ===================
    status("Assembling final document...")
    full_doc = "\n\n".join(sections)

    # Add footer
    full_doc += f"""

---

> **Document generated automatically by IaCraft**
> Generated: {now} | Cloud: {cloud} | Region: {region} | IaC: {iac_tool}
> This document should be reviewed by a qualified cloud architect before production deployment.
"""

    # Write to file
    doc_dir = os.path.join(output_dir, "docs")
    os.makedirs(doc_dir, exist_ok=True)

    doc_path = os.path.join(doc_dir, "DEPLOYMENT_GUIDE.md")
    with open(doc_path, "w", encoding="utf-8") as f:
        f.write(full_doc)

    status(f"Deployment guide saved: {doc_path}")
    return full_doc
