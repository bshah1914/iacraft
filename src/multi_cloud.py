"""Multi-cloud comparison engine.

Generates IaC for AWS, Azure, and GCP from the same requirement,
then compares services, cost, and security across all three.
"""

import json
import time
import os
import threading
from typing import Callable, Optional, Dict, List
from dataclasses import dataclass, field

from .config import PipelineConfig, CLOUD_SERVICE_MAP, DEFAULT_REGIONS
from .engine import PipelineEngine
from .llm_client import LLMClient
from .file_writer import FileWriter
from .prompts.system_prompts import MASTER_SYSTEM_PROMPT


@dataclass
class CloudResult:
    """Result from a single cloud pipeline run."""
    cloud: str
    status: str = "pending"  # pending, running, complete, error
    time_taken: float = 0.0
    analysis: dict = field(default_factory=dict)
    architecture: dict = field(default_factory=dict)
    mapping: dict = field(default_factory=dict)
    iac_files: list = field(default_factory=list)
    diagram: str = ""
    security: str = ""
    cost: str = ""
    errors: list = field(default_factory=list)
    error_msg: str = ""


@dataclass
class ComparisonReport:
    """Multi-cloud comparison report."""
    clouds: Dict[str, CloudResult] = field(default_factory=dict)
    comparison_table: str = ""
    recommendation: str = ""
    total_time: float = 0.0


class MultiCloudEngine:
    """Generates and compares infrastructure across AWS, Azure, and GCP."""

    CLOUDS = ["aws", "azure", "gcp"]

    def __init__(
        self,
        user_message: str,
        iac_tool: str = "terraform",
        provider: str = "groq",
        model: str = None,
        ollama_url: str = None,
        output_dir: str = "output",
        on_status: Optional[Callable] = None,
    ):
        self.user_message = user_message
        self.iac_tool = iac_tool
        self.provider = provider
        self.model = model
        self.ollama_url = ollama_url
        self.output_dir = output_dir
        self.on_status = on_status or (lambda cloud, msg: print(f"  [{cloud.upper()}] {msg}"))
        self.report = ComparisonReport()

    def _status(self, cloud: str, msg: str):
        self.on_status(cloud, msg)

    def run(self) -> ComparisonReport:
        """Run pipeline for all 3 clouds and compare."""
        start = time.time()

        # Run all 3 clouds sequentially (to respect rate limits)
        for cloud in self.CLOUDS:
            self._run_single_cloud(cloud)

        # Generate comparison
        self._generate_comparison()

        self.report.total_time = time.time() - start
        self._status("all", f"Multi-cloud comparison complete in {self.report.total_time:.1f}s")
        return self.report

    def run_parallel(self) -> ComparisonReport:
        """Run pipeline for all 3 clouds in parallel (use with Ollama/unlimited providers)."""
        start = time.time()

        threads = []
        for cloud in self.CLOUDS:
            t = threading.Thread(target=self._run_single_cloud, args=(cloud,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self._generate_comparison()
        self.report.total_time = time.time() - start
        self._status("all", f"Multi-cloud comparison complete in {self.report.total_time:.1f}s")
        return self.report

    def _run_single_cloud(self, cloud: str):
        """Run the full pipeline for a single cloud."""
        result = CloudResult(cloud=cloud, status="running")
        self.report.clouds[cloud] = result
        self._status(cloud, "Starting pipeline...")

        cloud_output = os.path.join(self.output_dir, f"compare_{cloud}")

        try:
            start = time.time()

            def cloud_status(step: int, msg: str):
                self._status(cloud, f"Step {step}/11: {msg}")

            config = PipelineConfig(
                user_message=self.user_message,
                cloud=cloud,
                iac_tool=self.iac_tool,
                region=DEFAULT_REGIONS[cloud],
                output_dir=cloud_output,
                provider=self.provider,
                model=self.model,
                ollama_url=self.ollama_url,
            )

            engine = PipelineEngine(config, on_status=cloud_status)
            results = engine.run()

            result.time_taken = time.time() - start
            result.status = "complete"
            result.analysis = results.get("analysis", {})
            result.architecture = results.get("architecture", {})
            result.mapping = results.get("mapping", {})
            result.iac_files = [os.path.basename(str(f)) for f in results.get("iac_files", [])]
            result.diagram = results.get("diagram", "")
            result.security = results.get("security", "")
            result.cost = results.get("cost", "")
            result.errors = results.get("errors", [])

            self._status(cloud, f"Complete in {result.time_taken:.1f}s — {len(result.iac_files)} files")

        except Exception as e:
            result.status = "error"
            result.error_msg = str(e)
            self._status(cloud, f"Failed: {e}")

    def _generate_comparison(self):
        """Generate comparison table and recommendation using LLM."""
        self._status("all", "Generating comparison report...")

        # Build comparison data
        cloud_summaries = {}
        for cloud, result in self.report.clouds.items():
            if result.status == "complete":
                services = [m.get("service", "") for m in result.mapping.get("mappings", [])]
                cloud_summaries[cloud.upper()] = {
                    "services": services,
                    "files_count": len(result.iac_files),
                    "time": f"{result.time_taken:.1f}s",
                    "cost_section": result.cost[:500] if result.cost else "N/A",
                }

        if not cloud_summaries:
            self.report.comparison_table = "No successful cloud generations to compare."
            self.report.recommendation = "All cloud pipelines failed."
            return

        try:
            llm = LLMClient(provider=self.provider, model=self.model, ollama_url=self.ollama_url)

            prompt = f"""Compare these cloud infrastructure solutions for: "{self.user_message}"

{json.dumps(cloud_summaries, indent=2)}

Generate:

1. **Service Comparison Table** in markdown:
| Feature | AWS | Azure | GCP |
|---|---|---|---|
| Compute | ... | ... | ... |
| Database | ... | ... | ... |
(cover all major categories)

2. **Cost Comparison** — which is cheapest for this workload and why

3. **Recommendation** — which cloud is best for this specific use case and why (consider cost, features, ecosystem)

Keep it concise and actionable."""

            response = llm.generate(MASTER_SYSTEM_PROMPT, prompt, max_tokens=4096)

            # Split into sections
            self.report.comparison_table = response
            self.report.recommendation = response

            # Write comparison report
            report_dir = os.path.join(self.output_dir, "comparison")
            os.makedirs(report_dir, exist_ok=True)

            with open(os.path.join(report_dir, "comparison-report.md"), "w", encoding="utf-8") as f:
                f.write(f"# Multi-Cloud Comparison Report\n\n")
                f.write(f"**Requirement**: {self.user_message}\n\n")
                f.write(f"**Clouds**: {', '.join(c.upper() for c in self.CLOUDS)}\n\n")
                f.write(f"**Total Time**: {self.report.total_time:.1f}s\n\n---\n\n")
                f.write(response)
                f.write("\n\n---\n\n## Per-Cloud Details\n\n")
                for cloud, result in self.report.clouds.items():
                    f.write(f"### {cloud.upper()}\n")
                    f.write(f"- **Status**: {result.status}\n")
                    f.write(f"- **Time**: {result.time_taken:.1f}s\n")
                    f.write(f"- **Files**: {len(result.iac_files)}\n")
                    f.write(f"- **Services**: {', '.join(m.get('service','') for m in result.mapping.get('mappings',[]))}\n\n")

            with open(os.path.join(report_dir, "comparison-data.json"), "w", encoding="utf-8") as f:
                data = {}
                for cloud, result in self.report.clouds.items():
                    data[cloud] = {
                        "status": result.status,
                        "time": result.time_taken,
                        "services": [m.get("service", "") for m in result.mapping.get("mappings", [])],
                        "files": result.iac_files,
                    }
                json.dump(data, f, indent=2)

        except Exception as e:
            self.report.comparison_table = f"Error generating comparison: {e}"
            self.report.recommendation = "Could not generate recommendation."
