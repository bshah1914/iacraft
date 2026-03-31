"""Output parser and file writer for generated IaC artifacts."""

import os
import re
import json
from typing import Dict, List, Tuple


class FileWriter:
    """Parse LLM output and write structured files to disk."""

    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.terraform_dir = os.path.join(output_dir, "terraform")
        self.architecture_dir = os.path.join(output_dir, "architecture")
        self.validation_dir = os.path.join(output_dir, "validation")

        # Create directories
        for d in [self.terraform_dir, self.architecture_dir, self.validation_dir]:
            os.makedirs(d, exist_ok=True)

    def write_json(self, filename: str, data: dict, subdir: str = "architecture") -> str:
        """Write a JSON file."""
        target_dir = os.path.join(self.output_dir, subdir)
        os.makedirs(target_dir, exist_ok=True)
        filepath = os.path.join(target_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return filepath

    def write_markdown(self, filename: str, content: str, subdir: str = "architecture") -> str:
        """Write a markdown file."""
        target_dir = os.path.join(self.output_dir, subdir)
        os.makedirs(target_dir, exist_ok=True)
        filepath = os.path.join(target_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return filepath

    def write_file(self, filename: str, content: str, subdir: str = "") -> str:
        """Write any file to the output directory."""
        target_dir = os.path.join(self.output_dir, subdir) if subdir else self.output_dir
        os.makedirs(target_dir, exist_ok=True)
        filepath = os.path.join(target_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return filepath

    def parse_and_write_iac_files(self, llm_output: str, iac_tool: str = "terraform") -> List[str]:
        """Parse LLM output containing multiple files and write them.

        Expects format:
        ### FILE: <filename>
        ```
        <content>
        ```
        """
        written_files = []
        # Match both ### FILE: and ### CORRECTED FILE: patterns
        pattern = r'###\s+(?:CORRECTED\s+)?FILE:\s*(\S+)\s*\n```[a-z]*\n(.*?)```'
        matches = re.findall(pattern, llm_output, re.DOTALL)

        if not matches:
            # Try alternative pattern without ### prefix
            pattern = r'(?:FILE|File):\s*[`]*(\S+)[`]*\s*\n```[a-z]*\n(.*?)```'
            matches = re.findall(pattern, llm_output, re.DOTALL)

        if not matches:
            # Last resort: look for ```hcl blocks with filename comments
            pattern = r'#\s*(\S+\.tf)\s*\n(.*?)(?=\n#\s*\S+\.tf|\Z)'
            matches = re.findall(pattern, llm_output, re.DOTALL)

        subdir = "terraform" if iac_tool == "terraform" else iac_tool
        for filename, content in matches:
            filename = filename.strip().strip("`")
            content = content.strip()
            filepath = self.write_file(filename, content, subdir=subdir)
            written_files.append(filepath)

        return written_files

    def parse_corrected_files(self, llm_output: str, iac_tool: str = "terraform") -> List[str]:
        """Parse auto-fix output and overwrite corrected files."""
        return self.parse_and_write_iac_files(llm_output, iac_tool)

    def write_diagram(self, mermaid_content: str) -> str:
        """Write Mermaid diagram file."""
        # Extract mermaid code from markdown block if needed
        cleaned = mermaid_content.strip()
        if "```mermaid" in cleaned:
            start = cleaned.index("```mermaid") + 10
            end = cleaned.index("```", start)
            cleaned = cleaned[start:end].strip()
        elif "```" in cleaned:
            start = cleaned.index("```") + 3
            end = cleaned.index("```", start)
            cleaned = cleaned[start:end].strip()

        return self.write_file("diagram.mmd", cleaned, subdir="architecture")

    def write_summary_report(self, sections: Dict[str, str]) -> str:
        """Write a combined summary report with all sections."""
        report = "# Infrastructure as Code - Generation Report\n\n"
        report += "---\n\n"

        for title, content in sections.items():
            report += f"## {title}\n\n{content}\n\n---\n\n"

        return self.write_file("REPORT.md", report)

    def get_all_iac_content(self, iac_tool: str = "terraform") -> str:
        """Read all generated IaC files and return as combined string."""
        subdir = os.path.join(self.output_dir, "terraform" if iac_tool == "terraform" else iac_tool)
        if not os.path.exists(subdir):
            return ""

        combined = ""
        for filename in sorted(os.listdir(subdir)):
            filepath = os.path.join(subdir, filename)
            if os.path.isfile(filepath):
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                combined += f"\n### FILE: {filename}\n```\n{content}\n```\n"

        return combined

    def list_iac_files(self, iac_tool: str = "terraform") -> str:
        """List all generated IaC files."""
        subdir = os.path.join(self.output_dir, "terraform" if iac_tool == "terraform" else iac_tool)
        if not os.path.exists(subdir):
            return "No files generated yet."

        files = sorted(os.listdir(subdir))
        return "\n".join(f"- {f}" for f in files) if files else "No files generated yet."
