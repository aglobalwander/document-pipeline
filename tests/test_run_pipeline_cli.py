import subprocess
import sys
import json
from pathlib import Path

def run_pipeline(input_path: Path, pipeline_type: str, output_dir: Path, output_format: str = None) -> str:
    """Helper to invoke the run_pipeline CLI."""
    cmd = [
        sys.executable,
        "scripts/run_pipeline.py",
        "--input_path", str(input_path),
        "--pipeline_type", pipeline_type,
        "--output_dir", str(output_dir)
    ]
    if output_format:
        cmd += ["--output_format", output_format]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0, f"Pipeline exited with error:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    return result.stdout

def test_cli_text(tmp_path: Path):
    """Test the CLI with a text pipeline on a .txt input."""
    input_file = Path("data/input/text/sample_report.txt")
    assert input_file.exists(), f"Test input not found: {input_file}"
    output_dir = tmp_path / "out_text"
    # Run pipeline
    run_pipeline(input_file, "text", output_dir)
    # Verify output file
    output_file = output_dir / "text" / f"{input_file.stem}_output.txt"
    assert output_file.exists(), f"Expected output file not found: {output_file}"
    content = output_file.read_text(encoding="utf-8").strip()
    assert content, "Output content should not be empty"

def test_cli_json(tmp_path: Path):
    """Test the CLI with a JSON pipeline on a .txt input."""
    input_file = Path("data/input/text/sample_report.txt")
    assert input_file.exists(), f"Test input not found: {input_file}"
    output_dir = tmp_path / "out_json"
    # Run pipeline
    run_pipeline(input_file, "json", output_dir)
    # Verify output file
    output_file = output_dir / "json" / f"{input_file.stem}_output.json"
    assert output_file.exists(), f"Expected JSON output file not found: {output_file}"
    # Load and check JSON
    data = json.loads(output_file.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "JSON output should be a dictionary"
    assert data, "JSON output dictionary should not be empty"

def test_cli_markdown(tmp_path: Path):
    """Test the CLI with a Markdown pipeline on a .txt input."""
    input_file = Path("data/input/text/sample_report.txt")
    assert input_file.exists(), f"Test input not found: {input_file}"
    output_dir = tmp_path / "out_md"
    # Run pipeline
    run_pipeline(input_file, "markdown", output_dir)
    # Verify output file
    output_file = output_dir / "markdown" / f"{input_file.stem}_output.markdown"
    assert output_file.exists(), f"Expected Markdown output file not found: {output_file}"
    content = output_file.read_text(encoding="utf-8")
    # Basic sanity checks for Markdown formatting
    assert content.strip(), "Markdown output should not be empty"
    assert any(sym in content for sym in ("#", "*", "_")), "Markdown output should contain markdown syntax"