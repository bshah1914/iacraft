"""System prompts for each step of the 11-step pipeline."""

MASTER_SYSTEM_PROMPT = """You are a Principal Cloud Architect, DevSecOps Engineer, and FinOps expert.
You produce enterprise-grade, deployment-ready cloud infrastructure solutions.
You MUST follow all instructions strictly and produce structured, complete outputs.
Never use placeholders like "example-id" or incomplete resources."""


def get_step1_prompt(cloud: str, region: str, iac_tool: str) -> str:
    """Step 1: Requirement Analysis."""
    return f"""You are analyzing a cloud infrastructure requirement.

Target cloud: {cloud.upper()}
Target region: {region}
IaC tool: {iac_tool}

Analyze the user's message and extract:
1. Application type (web app, SaaS, microservices, AI, data pipeline, etc.)
2. Scale (users/day, traffic level)
3. Availability requirement (single region / multi-AZ / multi-region)
4. Performance needs
5. Budget hints
6. Compliance needs

If information is missing, assume:
- Production-grade architecture
- High availability (multi-AZ)
- Moderate scale (10k-100k users/day)

Output STRICT JSON:
{{
    "app_type": "...",
    "scale": "...",
    "users_per_day": "...",
    "availability": "multi-az|multi-region|single-region",
    "performance": "...",
    "budget": "...",
    "compliance": ["SOC2", "ISO27001", "CIS"],
    "components": ["list of required components"],
    "summary": "one paragraph summary"
}}"""


def get_step2_3_prompt(cloud: str, region: str, analysis_json: str) -> str:
    """Step 2-3: Service Abstraction + Cloud-Agnostic JSON."""
    return f"""Based on this requirement analysis:
{analysis_json}

Create a cloud-agnostic architecture using ONLY these abstract categories:
- compute: (vm, autoscaling, containers, serverless)
- storage: (object, block, file, archive)
- database: (sql, nosql, cache, warehouse)
- networking: (vpc, subnets, load_balancer, dns, cdn)
- security: (iam, roles, secrets, encryption, waf)
- monitoring: (logs, metrics, tracing, alerts)
- messaging: (queue, pubsub, streaming)
- devops: (ci_cd, registry, deployment)
- analytics: (etl, query, processing)
- ai_ml: (training, inference)

Output STRICT JSON (no explanation inside JSON):
{{
    "cloud": "{cloud}",
    "region": "{region}",
    "compliance": ["SOC2", "ISO27001", "CIS"],
    "architecture": {{
        "compute": {{
            "type": "...",
            "description": "...",
            "specs": {{}}
        }},
        "database": {{
            "type": "...",
            "description": "...",
            "specs": {{}}
        }},
        "storage": {{
            "type": "...",
            "description": "...",
            "specs": {{}}
        }},
        "networking": {{
            "type": "...",
            "description": "...",
            "specs": {{}}
        }},
        "security": {{
            "type": "...",
            "description": "...",
            "specs": {{}}
        }},
        "monitoring": {{
            "type": "...",
            "description": "...",
            "specs": {{}}
        }},
        "scaling": {{
            "type": "...",
            "description": "..."
        }},
        "availability": "multi-az"
    }}
}}

Only include categories that are needed. Be specific in specs (instance sizes, storage amounts, etc.)."""


def get_step4_prompt(cloud: str, architecture_json: str, service_map: str, compact: bool = False) -> str:
    """Step 4: Cloud-Specific Mapping."""
    if compact:
        # For small models: skip the huge service_map, the model already knows cloud services
        return f"""Map this architecture to real {cloud.upper()} services.

Architecture:
{architecture_json}

Output STRICT JSON:
{{"cloud":"{cloud}","mappings":[{{"category":"compute","abstract":"type","service":"name","config":"details"}}]}}

Use real {cloud.upper()} service names. Keep config values short."""
    else:
        return f"""Map this cloud-agnostic architecture to real {cloud.upper()} services.

Architecture:
{architecture_json}

Available service mappings for {cloud.upper()}:
{service_map}

Output a STRICT JSON mapping:
{{
    "cloud": "{cloud}",
    "mappings": [
        {{
            "category": "compute",
            "abstract": "autoscaling",
            "service": "actual service name",
            "config": "specific configuration details"
        }}
    ]
}}

Include ALL services needed. Be specific with configurations (instance types, sizes, tiers)."""


def get_step5_prompt(cloud: str, region: str, iac_tool: str, mapping_json: str, architecture_json: str, compact: bool = False) -> str:
    """Step 5: IaC Code Generation.

    Args:
        compact: If True, generate fewer files with combined resources (for small models).
    """
    if compact:
        # Compact mode for small models (3B and below) — fewer files, shorter prompt
        tool_instructions = {
            "terraform": """Generate Terraform code in these files:
- main.tf: Provider config + ALL core resources (VPC, subnets, security groups, compute, database, storage)
- variables.tf: Input variables with defaults
- outputs.tf: Key outputs (endpoints, IDs)

Keep code concise. Use proper resource references.""",
            "pulumi": "Generate Pulumi Python code in __main__.py with all resources.",
            "cloudformation": "Generate CloudFormation YAML template with all resources.",
            "cdk": "Generate AWS CDK TypeScript code with all constructs.",
            "bicep": "Generate Azure Bicep with all resources.",
        }
    else:
        tool_instructions = {
            "terraform": """Generate COMPLETE Terraform code split into these files:
- providers.tf: Provider configuration with required_providers block
- variables.tf: All input variables with descriptions, types, and defaults
- networking.tf: VPC/VNet, subnets (public/private), internet gateway, NAT gateway, route tables, security groups
- compute.tf: Compute resources (EC2/ECS/Lambda etc.), auto-scaling, launch templates
- database.tf: Database resources with subnet groups, parameter groups
- storage.tf: Storage resources (S3/Blob etc.) with proper policies
- security.tf: IAM roles, policies, KMS keys, secrets
- monitoring.tf: CloudWatch/Monitor resources, log groups, alarms, dashboards
- outputs.tf: All important outputs (endpoints, IDs, ARNs)
- terraform.tfvars: Default variable values

IMPORTANT RULES:
- Use proper resource naming with variables
- Include all required arguments for each resource
- Use data sources where appropriate (e.g., data "aws_availability_zones")
- Add tags using map format: tags = { Name = "x", Environment = "prod" }
- Do NOT use deprecated list-of-maps tags format on aws_autoscaling_group
- Use locals for computed values
- Reference resources by their terraform IDs, not hardcoded values
- Include proper depends_on where needed
- NO placeholders or example IDs
- For aws_autoscaling_policy use: autoscaling_group_name, NOT resource_id or scalable_dimension
- For aws_launch_template add: metadata_options { http_tokens = "required" }
- For aws_db_instance use: allocated_storage (NOT storage_size)
- For aws_db_instance add: storage_encrypted = true, multi_az = true, copy_tags_to_snapshot = true
- For aws_cloudwatch_log_group add: retention_in_days = 365
- For aws_security_group add: description field
- For aws_s3_bucket add: aws_s3_bucket_public_access_block resource
- Every output must reference a resource that exists in the code
- For required_providers use version = "~> 5.0" (not old pinned versions)
- For required_version use ">= 1.5.0" (not exact version pins)""",
            "pulumi": "Generate complete Pulumi Python code in __main__.py with all resources.",
            "cloudformation": "Generate complete CloudFormation YAML template with all resources.",
            "cdk": "Generate complete AWS CDK TypeScript code with all constructs.",
            "bicep": "Generate complete Azure Bicep modules with all resources.",
        }

    return f"""Generate deployment-ready {iac_tool} code for {cloud.upper()} in region {region}.

Architecture mapping:
{mapping_json}

Full architecture:
{architecture_json}

{tool_instructions.get(iac_tool, tool_instructions['terraform'])}

Output each file in this format:
### FILE: <filename>
```
<complete file content>
```

Generate ALL files. Every resource must be complete with all required arguments."""


def get_step6_prompt(architecture_json: str, mapping_json: str) -> str:
    """Step 6: Mermaid Architecture Diagram."""
    return f"""Create a Mermaid architecture diagram for this infrastructure.

Architecture:
{architecture_json}

STRICT MERMAID SYNTAX RULES:
- Start with: graph TD
- Node IDs must be simple alphanumeric: A, B, ALB, EC2, VPC (NO spaces, NO special chars)
- Node labels use square brackets: ALB[Application Load Balancer]
- Arrows use: A --> B or A -->|label| B
- Subgraphs: subgraph Name ... end
- NO parentheses () in node IDs or labels
- NO slashes / in node IDs
- NO quotes in node labels
- Keep it simple: max 15 nodes

EXAMPLE of valid syntax:
```mermaid
graph TD
    User[User] --> ALB[Load Balancer]
    subgraph VPC
        ALB --> EC2[EC2 Instance]
        EC2 --> RDS[Database]
    end
```

Output ONLY valid Mermaid code:
```mermaid
graph TD
...
```"""


def get_step7_prompt(cloud: str, architecture_json: str) -> str:
    """Step 7: Security Controls."""
    return f"""Define comprehensive security controls for this {cloud.upper()} architecture.

Architecture:
{architecture_json}

You MUST include controls for:
1. IAM & Access Control - least privilege, MFA, role-based access
2. Network Security - private subnets, security groups, NACLs, no public DB
3. Encryption - at rest (KMS/Key Vault) and in transit (TLS/SSL)
4. Secrets Management - no hardcoded secrets, use secrets manager
5. Logging & Auditing - CloudTrail/Activity Log, access logs
6. Data Protection - backup, versioning, lifecycle policies
7. Application Security - WAF, DDoS protection, input validation
8. Incident Response - alerting, automated remediation

Output as structured markdown with specific {cloud.upper()} service references for each control.
Format each control as:
### Control Name
- **Requirement**: What needs to be secured
- **Implementation**: Specific {cloud.upper()} service/config
- **Verification**: How to verify it's working"""


def get_step8_prompt(cloud: str, security_controls: str) -> str:
    """Step 8: Compliance Mapping."""
    return f"""Map this {cloud.upper()} architecture's security controls to compliance frameworks.

Security Controls:
{security_controls}

Create a compliance mapping table for:
- SOC2 (Trust Service Criteria)
- ISO 27001 (Annex A Controls)
- CIS Benchmarks ({cloud.upper()})

Output as a markdown table:
| Control Area | SOC2 | ISO 27001 | CIS Benchmark | Implementation |
|---|---|---|---|---|

Cover ALL these areas:
1. Access Control
2. Encryption (at rest)
3. Encryption (in transit)
4. Network Security
5. Logging & Monitoring
6. Data Protection
7. Incident Response
8. Change Management
9. Vulnerability Management
10. Secrets Management"""


def get_step9_prompt(cloud: str, region: str, mapping_json: str) -> str:
    """Step 9: Cost Estimation."""
    return f"""Estimate monthly costs for this {cloud.upper()} architecture in {region}.

Service mapping:
{mapping_json}

Provide:
1. Service-by-service monthly cost breakdown in USD
2. Total monthly estimate
3. Total annual estimate
4. Assumptions (usage patterns, data transfer, storage growth)
5. Cost optimization recommendations

Output as a markdown table:
| Service | Configuration | Monthly Cost (USD) | Notes |
|---|---|---|---|

Then add:
- **Total Monthly**: $X
- **Total Annual**: $X
- **Assumptions**: list
- **Optimization Tips**: list

Be realistic with pricing. Use current {cloud.upper()} pricing for {region}."""


def get_step10_prompt(iac_tool: str, file_list: str) -> str:
    """Step 10: Validation Plan."""
    return f"""Create a validation plan for this {iac_tool} infrastructure code.

Files generated:
{file_list}

Include:
1. **Syntax Validation**
   - {iac_tool} specific validation commands
   - Expected output

2. **Security Scanning**
   - Checkov commands and expected checks
   - tfsec commands and expected checks
   - Common findings to watch for

3. **Plan Review**
   - What to look for in the plan output
   - Resource count expectations
   - Potential issues

4. **Pre-Deployment Checklist**
   - [ ] All variables have values
   - [ ] State backend configured
   - [ ] Credentials configured
   - [ ] Network CIDR ranges don't conflict
   - [ ] DNS/domain names are correct
   - [ ] Tags are consistent
   - [ ] Encryption enabled everywhere

5. **Post-Deployment Validation**
   - Connectivity tests
   - Security group verification
   - Endpoint accessibility

Output as structured markdown with commands and checklists."""


def get_step11_prompt(iac_tool: str, all_code: str) -> str:
    """Step 11: Auto-Fix Loop."""
    return f"""Review this {iac_tool} code for issues and provide fixes.

Code to review:
{all_code}

Perform these checks:
1. **Misconfigurations** - Wrong resource arguments, missing required fields
2. **Missing Dependencies** - Resources that reference undefined resources
3. **Security Risks** - Public access, missing encryption, overly permissive IAM
4. **Best Practice Violations** - Missing tags, no lifecycle policies, no backups
5. **Syntax Errors** - Invalid HCL/YAML/code syntax
6. **Hardcoded Values** - Values that should be variables

For each issue found:
### Issue N: [Title]
- **Severity**: Critical / High / Medium / Low
- **File**: filename
- **Problem**: description
- **Fix**:
```
corrected code snippet
```

Then output the COMPLETE corrected version of any file that needed changes.
Format as:
### CORRECTED FILE: <filename>
```
<complete corrected file content>
```

If no issues found, confirm the code passes all checks."""
