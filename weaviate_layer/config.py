from pydantic_settings import BaseSettings
from pathlib import Path
import yaml, os

def read_yaml(path: str | None) -> dict:
    return yaml.safe_load(Path(path).read_text()) if path and Path(path).exists() else {}

class Settings(BaseSettings):
    weav_url: str | None = None
    weav_api_key: str | None = None
    weav_grpc_url: str | None = None
    openai_api_key: str
    model_config = {"env_file": ".env", "extra": "ignore"}     # pydantic-v2 style

# 1. read YAML (may be {})
yaml_defaults = read_yaml(os.getenv("PIPELINE_CONFIG"))
# 2. strip any key already present in real env
filtered_yaml = {k: v for k, v in yaml_defaults.items() if k not in os.environ}
# 3. instantiate
settings = Settings(**filtered_yaml)