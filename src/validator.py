"""Terraform code validator and auto-fix loop.

Runs: terraform fmt → terraform init → terraform validate → checkov scan
If errors found, sends them to the LLM for auto-fix, then re-validates.
"""

import os
import json
import subprocess
import shutil
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field

from .llm_client import LLMClient
from .file_writer import FileWriter
from .prompts.system_prompts import MASTER_SYSTEM_PROMPT


@dataclass
class ValidationResult:
    """Result of a single validation step."""
    tool: str
    passed: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    raw_output: str = ""


@dataclass
class SimulatorReport:
    """Full report from the validation + auto-fix simulator."""
    rounds: List[Dict] = field(default_factory=list)
    final_passed: bool = False
    total_errors_found: int = 0
    total_errors_fixed: int = 0
    summary: str = ""


def _run_cmd(cmd: List[str], cwd: str, timeout: int = 60) -> tuple:
    """Run a shell command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True,
            timeout=timeout, shell=True,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except FileNotFoundError:
        return -2, "", f"Command not found: {cmd[0]}"


def _find_terraform() -> Optional[str]:
    """Find terraform binary."""
    tf = shutil.which("terraform")
    if tf:
        return tf
    # Check common Windows paths
    for path in [
        os.path.expanduser("~/AppData/Local/Microsoft/WinGet/Links/terraform.exe"),
        os.path.expanduser("~/AppData/Local/Microsoft/WinGet/Packages/Hashicorp.Terraform_Microsoft.Winget.Source_8wekyb3d8bbwe/terraform.exe"),
        "C:/Program Files/Terraform/terraform.exe",
        "C:/HashiCorp/Terraform/terraform.exe",
        os.path.expanduser("~/scoop/shims/terraform.exe"),
    ]:
        if os.path.exists(path):
            return path
    return None


def _find_checkov() -> Optional[str]:
    """Find checkov binary."""
    return shutil.which("checkov")


class TerraformValidator:
    """Validates Terraform code using terraform CLI and checkov."""

    def __init__(self, terraform_dir: str):
        self.terraform_dir = os.path.abspath(terraform_dir)
        self.terraform_bin = _find_terraform()
        self.checkov_bin = _find_checkov()

    def get_available_tools(self) -> Dict[str, bool]:
        """Check which validation tools are available."""
        return {
            "terraform_fmt": self.terraform_bin is not None,
            "terraform_validate": self.terraform_bin is not None,
            "checkov": self.checkov_bin is not None,
        }

    def run_fmt(self) -> ValidationResult:
        """Run terraform fmt -check to detect formatting issues."""
        if not self.terraform_bin:
            return ValidationResult(tool="terraform_fmt", passed=False, errors=["Terraform not installed"])

        code, stdout, stderr = _run_cmd(
            [self.terraform_bin, "fmt", "-check", "-diff", "-recursive"],
            cwd=self.terraform_dir,
        )

        if code == 0:
            return ValidationResult(tool="terraform_fmt", passed=True, raw_output="All files formatted correctly")

        errors = [f"Formatting issues in: {line}" for line in stdout.strip().split("\n") if line.strip()]
        # Auto-fix formatting
        _run_cmd([self.terraform_bin, "fmt", "-recursive"], cwd=self.terraform_dir)

        return ValidationResult(
            tool="terraform_fmt", passed=False,
            errors=errors, raw_output=stdout + stderr,
            warnings=["Auto-fixed formatting issues"],
        )

    def run_init(self) -> ValidationResult:
        """Run terraform init to download providers."""
        if not self.terraform_bin:
            return ValidationResult(tool="terraform_init", passed=False, errors=["Terraform not installed"])

        code, stdout, stderr = _run_cmd(
            [self.terraform_bin, "init", "-backend=false", "-input=false"],
            cwd=self.terraform_dir, timeout=120,
        )

        if code == 0:
            return ValidationResult(tool="terraform_init", passed=True, raw_output=stdout)

        errors = [line for line in stderr.strip().split("\n") if "Error" in line or "error" in line]
        return ValidationResult(
            tool="terraform_init", passed=False,
            errors=errors or [stderr.strip()[:500]], raw_output=stdout + stderr,
        )

    def run_validate(self) -> ValidationResult:
        """Run terraform validate to check syntax and references."""
        if not self.terraform_bin:
            return ValidationResult(tool="terraform_validate", passed=False, errors=["Terraform not installed"])

        code, stdout, stderr = _run_cmd(
            [self.terraform_bin, "validate", "-json"],
            cwd=self.terraform_dir,
        )

        try:
            data = json.loads(stdout)
            if data.get("valid", False):
                return ValidationResult(tool="terraform_validate", passed=True, raw_output=stdout)

            errors = []
            for diag in data.get("diagnostics", []):
                severity = diag.get("severity", "error")
                summary = diag.get("summary", "")
                detail = diag.get("detail", "")
                rng = diag.get("range", {})
                filename = rng.get("filename", "")
                start = rng.get("start", {})
                line = start.get("line", 0)
                err_msg = f"[{severity}] {filename}:{line} - {summary}"
                if detail:
                    err_msg += f" ({detail[:200]})"
                errors.append(err_msg)

            return ValidationResult(
                tool="terraform_validate", passed=False,
                errors=errors, raw_output=stdout + stderr,
            )
        except json.JSONDecodeError:
            errors = [line for line in (stdout + stderr).split("\n") if "Error" in line]
            return ValidationResult(
                tool="terraform_validate", passed=False,
                errors=errors or [(stdout + stderr)[:500]], raw_output=stdout + stderr,
            )

    def run_checkov(self) -> ValidationResult:
        """Run checkov security scan."""
        if not self.checkov_bin:
            return ValidationResult(tool="checkov", passed=True, warnings=["Checkov not installed, skipping"])

        code, stdout, stderr = _run_cmd(
            [self.checkov_bin, "-d", self.terraform_dir, "--output", "json", "--quiet", "--compact"],
            cwd=self.terraform_dir, timeout=120,
        )

        try:
            data = json.loads(stdout)
            failed_checks = []
            for result in data if isinstance(data, list) else [data]:
                for check in result.get("results", {}).get("failed_checks", []):
                    failed_checks.append(
                        f"[{check.get('check_id', '')}] {check.get('check_name', '')} "
                        f"in {check.get('file_path', '')}:{check.get('file_line_range', [0])[0]}"
                    )

            return ValidationResult(
                tool="checkov",
                passed=len(failed_checks) == 0,
                errors=failed_checks[:20],  # Cap at 20
                raw_output=stdout[:2000],
            )
        except (json.JSONDecodeError, TypeError):
            return ValidationResult(
                tool="checkov", passed=code == 0,
                warnings=["Could not parse checkov output"],
                raw_output=(stdout + stderr)[:1000],
            )

    def run_all(self) -> List[ValidationResult]:
        """Run all available validation steps."""
        results = []
        results.append(self.run_fmt())
        init_result = self.run_init()
        results.append(init_result)
        if init_result.passed:
            results.append(self.run_validate())
        results.append(self.run_checkov())
        return results


class CodeSimulator:
    """Self-healing code validator: validate → fix → re-validate loop."""

    MAX_ROUNDS = 5

    def __init__(
        self,
        terraform_dir: str,
        llm: LLMClient,
        writer: FileWriter,
        on_status: Optional[Callable] = None,
    ):
        self.terraform_dir = terraform_dir
        self.llm = llm
        self.writer = writer
        self.validator = TerraformValidator(terraform_dir)
        self.on_status = on_status or (lambda msg: print(f"  [Simulator] {msg}"))
        self.report = SimulatorReport()

        # Wire up fallback logging
        self.llm._on_fallback = lambda old, new, reason: self._status(
            f"  Rate limit on {old} — auto-switching to {new}"
        )

    def _status(self, msg: str):
        self.on_status(msg)

    def run(self) -> SimulatorReport:
        """Run the full validate → fix → re-validate loop."""
        tools = self.validator.get_available_tools()
        self._status(f"Tools available: {', '.join(k for k, v in tools.items() if v)}")

        if not any(tools.values()):
            self.report.summary = "No validation tools available. Install terraform and/or checkov."
            return self.report

        for round_num in range(1, self.MAX_ROUNDS + 1):
            self._status(f"Round {round_num}/{self.MAX_ROUNDS}: Validating...")

            # Run all validators
            results = self.validator.run_all()
            all_errors = []
            round_data = {"round": round_num, "results": [], "fixes_applied": False}

            for r in results:
                round_data["results"].append({
                    "tool": r.tool,
                    "passed": r.passed,
                    "errors": r.errors,
                    "warnings": r.warnings,
                })
                if not r.passed:
                    all_errors.extend(r.errors)
                status_icon = "PASS" if r.passed else "FAIL"
                err_count = len(r.errors)
                warn_count = len(r.warnings)
                self._status(f"  {r.tool}: {status_icon} ({err_count} errors, {warn_count} warnings)")

            self.report.total_errors_found += len(all_errors)
            self.report.rounds.append(round_data)

            # All passed?
            if not all_errors:
                self._status(f"All validations passed in round {round_num}!")
                self.report.final_passed = True
                break

            # Last round — don't fix, just report
            if round_num == self.MAX_ROUNDS:
                self._status(f"Max rounds reached. {len(all_errors)} errors remaining.")
                break

            # Send errors to LLM for fixing
            self._status(f"Found {len(all_errors)} errors. Sending to LLM for auto-fix...")
            fixed = self._auto_fix(all_errors)
            round_data["fixes_applied"] = fixed

            if fixed:
                self.report.total_errors_fixed += len(all_errors)
                self._status("Fixes applied. Re-validating...")
            else:
                self._status("LLM could not generate fixes. Stopping.")
                break

        # Generate summary
        self.report.summary = self._generate_summary()
        return self.report

    def _strip_ansi(self, text: str) -> str:
        """Remove ANSI color codes from text."""
        import re
        return re.sub(r'\x1b\[[0-9;]*m', '', text)

    def _group_errors_by_file(self, errors: List[str]) -> Dict[str, List[str]]:
        """Group errors by the file they reference."""
        grouped = {}
        for err in errors:
            err = self._strip_ansi(err)
            # Extract filename from error
            for ext in [".tf"]:
                if ext in err:
                    parts = err.split(ext)
                    filename = parts[0].split()[-1].strip("\\/ ") + ext
                    filename = os.path.basename(filename)
                    grouped.setdefault(filename, []).append(err)
                    break
            else:
                grouped.setdefault("_general", []).append(err)
        return grouped

    def _auto_fix(self, errors: List[str]) -> bool:
        """Fix errors file-by-file to avoid token limits."""
        grouped = self._group_errors_by_file(errors)
        any_fixed = False

        # Prioritize terraform init/validate errors over checkov
        terraform_errors = [e for e in errors if "Error" in e and "CKV" not in e]
        checkov_errors = [e for e in errors if "CKV" in e]

        # Fix file-by-file
        for filename, file_errors in grouped.items():
            if filename == "_general":
                continue

            filepath = os.path.join(self.terraform_dir, filename)
            if not os.path.exists(filepath):
                continue

            with open(filepath, "r", encoding="utf-8") as f:
                file_code = f.read()

            error_text = "\n".join(f"- {self._strip_ansi(e)}" for e in file_errors[:10])

            prompt = f"""Fix these errors in {filename}. Output the COMPLETE corrected file.

ERRORS:
{error_text}

COMMON FIXES:
- CKV_AWS_8: Add encrypted=true to EBS/launch template block_device_mappings
- CKV_AWS_79: Add metadata_options {{ http_tokens="required" http_endpoint="enabled" }}
- CKV_AWS_23: Add description field to security groups
- CKV_AWS_382: Restrict egress to specific CIDRs instead of 0.0.0.0/0
- CKV_AWS_338: Add retention_in_days=365 to cloudwatch_log_group
- CKV_AWS_158: Add kms_key_id to cloudwatch_log_group
- CKV_AWS_129: Add enabled_cloudwatch_logs_exports to RDS
- CKV_AWS_16: Add storage_encrypted=true to RDS
- CKV_AWS_157: Add multi_az=true to RDS
- CKV_AWS_293: Add deletion_protection=true to RDS
- CKV2_AWS_60: Add copy_tags_to_snapshot=true to RDS
- Duplicate resource: Remove the duplicate, keep only one definition

CURRENT {filename}:
```hcl
{file_code}
```

Output ONLY the complete corrected file:
### FILE: {filename}
```hcl
<corrected code>
```"""

            try:
                self._status(f"  Fixing {filename} ({len(file_errors)} errors)...")
                response = self.llm.generate(MASTER_SYSTEM_PROMPT, prompt, max_tokens=4096)
                files = self.writer.parse_and_write_iac_files(response, "terraform")
                if files:
                    any_fixed = True
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "rate_limit" in err_str:
                    # Extract wait time if available
                    import re
                    wait_match = re.search(r'(\d+)m(\d+)', err_str)
                    if wait_match:
                        wait_msg = f"{wait_match.group(1)}m{wait_match.group(2)}s"
                    else:
                        wait_msg = "a few minutes"
                    self._status(f"  Rate limit hit. Retry in {wait_msg}. Skipping remaining files this round.")
                    break
                else:
                    self._status(f"  Fix failed for {filename}: {e}")

        return any_fixed

    def _generate_summary(self) -> str:
        """Generate a human-readable summary."""
        lines = [f"# Code Simulator Report\n"]
        lines.append(f"**Rounds**: {len(self.report.rounds)}")
        lines.append(f"**Final Status**: {'PASSED' if self.report.final_passed else 'FAILED'}")
        lines.append(f"**Total Errors Found**: {self.report.total_errors_found}")
        lines.append(f"**Total Errors Fixed**: {self.report.total_errors_fixed}\n")

        for rd in self.report.rounds:
            lines.append(f"## Round {rd['round']}")
            for r in rd["results"]:
                icon = "PASS" if r["passed"] else "FAIL"
                lines.append(f"- **{r['tool']}**: {icon}")
                for e in r["errors"][:5]:
                    lines.append(f"  - {e}")
                for w in r["warnings"]:
                    lines.append(f"  - (warning) {w}")
            if rd.get("fixes_applied"):
                lines.append("- **Auto-fix applied**\n")
            lines.append("")

        return "\n".join(lines)
