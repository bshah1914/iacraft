"""Core 11-step pipeline engine for message-to-iaac."""

import json
import time
import traceback
from typing import Callable, Optional

from .config import PipelineConfig, CLOUD_SERVICE_MAP
from .llm_client import LLMClient, _get_context_size
from .file_writer import FileWriter
from .prompts.system_prompts import (
    MASTER_SYSTEM_PROMPT,
    get_step1_prompt,
    get_step2_3_prompt,
    get_step4_prompt,
    get_step5_prompt,
    get_step6_prompt,
    get_step7_prompt,
    get_step8_prompt,
    get_step9_prompt,
    get_step10_prompt,
    get_step11_prompt,
)


class StepError(Exception):
    """Raised when a pipeline step fails."""
    def __init__(self, step: int, step_name: str, cause: Exception):
        self.step = step
        self.step_name = step_name
        self.cause = cause
        super().__init__(f"Step {step} ({step_name}) failed: {cause}")


class PipelineEngine:
    """Orchestrates the 11-step IaC generation pipeline."""

    def __init__(self, config: PipelineConfig, on_status: Optional[Callable] = None):
        self.config = config
        self.llm = LLMClient(
            provider=config.provider,
            model=config.model,
            ollama_url=config.ollama_url,
        )
        self.writer = FileWriter(config.output_dir)
        self.on_status = on_status or (lambda step, msg: print(f"  [{step}/11] {msg}"))
        self.results = {}
        self.errors = []

        # Set up fallback logging
        self.llm._on_fallback = lambda old, new, reason: self._status(
            0, f"Rate limit on {old} — switching to {new}"
        )

    def _status(self, step: int, message: str):
        """Report pipeline status."""
        self.on_status(step, message)

    def _run_step(self, step_num: int, step_name: str, step_fn, critical: bool = True):
        """Run a pipeline step with error handling.

        Args:
            step_num: Step number (1-11)
            step_name: Human-readable step name
            step_fn: The step function to call
            critical: If True, re-raise errors to stop the pipeline.
                      If False, log and continue.
        """
        try:
            step_fn()
        except Exception as e:
            error_msg = f"Step {step_num} ({step_name}) failed: {e}"
            self.errors.append({"step": step_num, "name": step_name, "error": str(e)})
            self._status(step_num, f"FAILED: {e}")

            if critical:
                raise StepError(step_num, step_name, e) from e

    def run(self) -> dict:
        """Execute the full 11-step pipeline."""
        start_time = time.time()

        self._status(0, f"Starting pipeline: {self.config.cloud.upper()} / {self.config.iac_tool} / {self.config.region}")

        # Steps 1-5 are critical — pipeline can't continue without them
        self._run_step(1, "Requirement Analysis", self._step1_analyze, critical=True)
        self._run_step(2, "Service Abstraction", self._step2_3_abstract, critical=True)
        self._run_step(4, "Cloud Mapping", self._step4_map, critical=True)
        self._run_step(5, "IaC Generation", self._step5_generate_iac, critical=True)

        # Steps 6-11 are non-critical — pipeline continues if they fail
        self._run_step(6, "Architecture Diagram", self._step6_diagram, critical=False)
        self._run_step(7, "Security Controls", self._step7_security, critical=False)
        self._run_step(8, "Compliance Mapping", self._step8_compliance, critical=False)
        self._run_step(9, "Cost Estimation", self._step9_cost, critical=False)
        self._run_step(10, "Validation Plan", self._step10_validate, critical=False)
        self._run_step(11, "Auto-Fix Loop", self._step11_autofix, critical=False)

        # Step 12: Deployment Guide (non-critical)
        self._run_step(12, "Deployment Guide", self._step12_deployment_guide, critical=False)

        # Write combined report (always attempt)
        try:
            self._write_report()
        except Exception as e:
            self.errors.append({"step": 0, "name": "Report Generation", "error": str(e)})

        elapsed = time.time() - start_time

        if self.errors:
            failed = [e["name"] for e in self.errors]
            self._status(11, f"Pipeline done in {elapsed:.1f}s ({len(self.errors)} step(s) had errors: {', '.join(failed)})")
        else:
            self._status(11, f"Pipeline complete in {elapsed:.1f}s")

        self.results["errors"] = self.errors
        return self.results

    def _step1_analyze(self):
        """Step 1: Analyze user requirements."""
        self._status(1, "Analyzing requirements...")

        system = MASTER_SYSTEM_PROMPT
        user = get_step1_prompt(self.config.cloud, self.config.region, self.config.iac_tool)
        user += f"\n\nUser requirement:\n{self.config.user_message}"

        analysis = self.llm.generate_json(system, user)
        self.results["analysis"] = analysis

        self.writer.write_json("requirement-analysis.json", analysis)
        self._status(1, f"Requirement analyzed: {analysis.get('app_type', 'N/A')}")

    def _step2_3_abstract(self):
        """Step 2-3: Create cloud-agnostic architecture."""
        self._status(2, "Building cloud-agnostic architecture...")

        system = MASTER_SYSTEM_PROMPT
        user = get_step2_3_prompt(
            self.config.cloud,
            self.config.region,
            json.dumps(self.results["analysis"], indent=2),
        )

        architecture = self.llm.generate_json(system, user)
        self.results["architecture"] = architecture

        self.writer.write_json("architecture.json", architecture)
        self._status(3, "Cloud-agnostic architecture created")

    def _step4_map(self):
        """Step 4: Map to cloud-specific services."""
        compact = self._is_small_model()
        self._status(4, f"Mapping to {self.config.cloud.upper()} services...")

        service_map = CLOUD_SERVICE_MAP.get(self.config.cloud, {})
        # For small models, use compact JSON (no indent) to save tokens
        arch_json = json.dumps(self.results["architecture"]) if compact else json.dumps(self.results["architecture"], indent=2)
        map_json = json.dumps(service_map) if compact else json.dumps(service_map, indent=2)

        system = MASTER_SYSTEM_PROMPT
        user = get_step4_prompt(
            self.config.cloud,
            arch_json,
            map_json,
            compact=compact,
        )

        mapping = self.llm.generate_json(system, user)
        self.results["mapping"] = mapping

        self.writer.write_json("cloud-mapping.json", mapping)

        mapping_md = f"# Cloud Service Mapping ({self.config.cloud.upper()})\n\n"
        mapping_md += "| Category | Abstract | Cloud Service | Configuration |\n"
        mapping_md += "|---|---|---|---|\n"
        for m in mapping.get("mappings", []):
            mapping_md += f"| {m.get('category', '')} | {m.get('abstract', '')} | {m.get('service', '')} | {m.get('config', '')} |\n"

        self.writer.write_markdown("cloud-mapping.md", mapping_md)
        self._status(4, f"Mapped {len(mapping.get('mappings', []))} services")

    def _is_small_model(self) -> bool:
        """Check if the configured model has a small context window."""
        if self.config.provider == "ollama":
            return _get_context_size(self.config.model) <= 4096
        return False

    def _step5_generate_iac(self):
        """Step 5: Generate Infrastructure as Code."""
        compact = self._is_small_model()
        mode = "compact" if compact else "full"
        self._status(5, f"Generating {self.config.iac_tool} code ({mode} mode)...")

        system = MASTER_SYSTEM_PROMPT
        user = get_step5_prompt(
            self.config.cloud,
            self.config.region,
            self.config.iac_tool,
            json.dumps(self.results["mapping"], indent=2),
            json.dumps(self.results["architecture"], indent=2),
            compact=compact,
        )

        iac_output = self.llm.generate(system, user, max_tokens=8192)
        self.results["iac_raw"] = iac_output

        files = self.writer.parse_and_write_iac_files(iac_output, self.config.iac_tool)
        self.results["iac_files"] = files
        self._status(5, f"Generated {len(files)} IaC files")

    def _step6_diagram(self):
        """Step 6: Generate Mermaid architecture diagram."""
        self._status(6, "Creating architecture diagram...")

        system = MASTER_SYSTEM_PROMPT
        user = get_step6_prompt(
            json.dumps(self.results["architecture"], indent=2),
            json.dumps(self.results["mapping"], indent=2),
        )

        diagram = self.llm.generate(system, user, max_tokens=4096)
        self.results["diagram"] = diagram

        self.writer.write_diagram(diagram)
        self._status(6, "Architecture diagram created")

    def _step7_security(self):
        """Step 7: Define security controls."""
        self._status(7, "Defining security controls...")

        system = MASTER_SYSTEM_PROMPT
        user = get_step7_prompt(
            self.config.cloud,
            json.dumps(self.results["architecture"], indent=2),
        )

        security = self.llm.generate(system, user, max_tokens=4096)
        self.results["security"] = security

        self.writer.write_markdown("security-controls.md", security)
        self._status(7, "Security controls defined")

    def _step8_compliance(self):
        """Step 8: Map to compliance frameworks."""
        self._status(8, "Mapping compliance frameworks...")

        system = MASTER_SYSTEM_PROMPT
        user = get_step8_prompt(self.config.cloud, self.results.get("security", "No security controls available."))

        compliance = self.llm.generate(system, user, max_tokens=4096)
        self.results["compliance"] = compliance

        self.writer.write_markdown("compliance.md", compliance)
        self._status(8, "Compliance mapping complete")

    def _step9_cost(self):
        """Step 9: Estimate costs."""
        self._status(9, "Estimating costs...")

        system = MASTER_SYSTEM_PROMPT
        user = get_step9_prompt(
            self.config.cloud,
            self.config.region,
            json.dumps(self.results.get("mapping", {}), indent=2),
        )

        cost = self.llm.generate(system, user, max_tokens=4096)
        self.results["cost"] = cost

        self.writer.write_markdown("cost-estimate.md", cost)
        self._status(9, "Cost estimation complete")

    def _step10_validate(self):
        """Step 10: Create validation plan."""
        self._status(10, "Creating validation plan...")

        file_list = self.writer.list_iac_files(self.config.iac_tool)
        system = MASTER_SYSTEM_PROMPT
        user = get_step10_prompt(self.config.iac_tool, file_list)

        validation = self.llm.generate(system, user, max_tokens=4096)
        self.results["validation"] = validation

        self.writer.write_markdown("validation-plan.md", validation, subdir="validation")
        self._status(10, "Validation plan created")

    def _step11_autofix(self):
        """Step 11: Auto-fix loop - detect and fix issues."""
        self._status(11, "Running auto-fix analysis...")

        all_code = self.writer.get_all_iac_content(self.config.iac_tool)
        if not all_code:
            self.results["autofix"] = "No IaC files to analyze."
            return

        system = MASTER_SYSTEM_PROMPT
        user = get_step11_prompt(self.config.iac_tool, all_code)

        autofix = self.llm.generate(system, user, max_tokens=8192)
        self.results["autofix"] = autofix

        self.writer.write_markdown("auto-fix-report.md", autofix, subdir="validation")

        corrected = self.writer.parse_corrected_files(autofix, self.config.iac_tool)
        if corrected:
            self._status(11, f"Applied {len(corrected)} corrected files")
        else:
            self._status(11, "No issues found - code passed all checks")

    def _step12_deployment_guide(self):
        """Step 12: Generate enterprise deployment guide."""
        self._status(12, "Generating deployment guide...")
        from .doc_generator import generate_deployment_guide

        def guide_status(msg):
            self._status(12, msg)

        guide = generate_deployment_guide(
            results=self.results,
            config=self.config,
            output_dir=self.config.output_dir,
            llm=self.llm,
            on_status=guide_status,
            doc_level=self.config.doc_level,
        )
        self.results["deployment_guide"] = guide
        self._status(12, "Deployment guide generated")

    def _write_report(self):
        """Write the combined summary report."""
        sections = {}

        analysis = self.results.get("analysis", {})
        sections["Architecture Summary"] = (
            f"**Application Type**: {analysis.get('app_type', 'N/A')}\n"
            f"**Scale**: {analysis.get('scale', 'N/A')}\n"
            f"**Availability**: {analysis.get('availability', 'N/A')}\n"
            f"**Cloud**: {self.config.cloud.upper()}\n"
            f"**Region**: {self.config.region}\n"
            f"**IaC Tool**: {self.config.iac_tool}\n\n"
            f"{analysis.get('summary', '')}"
        )

        sections["Cloud-Agnostic Architecture"] = (
            f"```json\n{json.dumps(self.results.get('architecture', {}), indent=2)}\n```"
        )

        mapping = self.results.get("mapping", {})
        mapping_table = "| Category | Abstract | Service | Config |\n|---|---|---|---|\n"
        for m in mapping.get("mappings", []):
            mapping_table += f"| {m.get('category', '')} | {m.get('abstract', '')} | {m.get('service', '')} | {m.get('config', '')} |\n"
        sections["Cloud Service Mapping"] = mapping_table

        sections["Infrastructure as Code"] = (
            f"Generated {len(self.results.get('iac_files', []))} files:\n"
            + self.writer.list_iac_files(self.config.iac_tool)
        )

        sections["Architecture Diagram"] = self.results.get("diagram", "No diagram generated.")
        sections["Security Controls"] = self.results.get("security", "No security controls defined.")
        sections["Compliance Mapping"] = self.results.get("compliance", "No compliance mapping.")
        sections["Cost Estimation"] = self.results.get("cost", "No cost estimate.")
        sections["Validation Plan"] = self.results.get("validation", "No validation plan.")
        sections["Auto-Fix Report"] = self.results.get("autofix", "No auto-fix analysis.")

        if self.errors:
            error_md = "| Step | Name | Error |\n|---|---|---|\n"
            for e in self.errors:
                error_md += f"| {e['step']} | {e['name']} | {e['error']} |\n"
            sections["Errors"] = error_md

        self.writer.write_summary_report(sections)
