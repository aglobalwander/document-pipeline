#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

storage_mode="auto" # auto | external | local
external_base="/Volumes/My Passport/knowledge-hub"
local_output_root="${PROJECT_ROOT}/data/output/collections"
local_registry_path="${PROJECT_ROOT}/data/processing_registry.yaml"
pass_args=()

usage() {
  cat <<'EOF'
Usage:
  scripts/collections/run_collection_with_storage_fallback.sh [storage-options] [process_collection args...]

Storage options:
  --storage auto|external|local
  --external_base /Volumes/My\ Passport/knowledge-hub
  --local_output_root /path/to/local/output/collections
  --local_registry_path /path/to/local/processing_registry.yaml
  --help

Any other arguments are passed to scripts/collections/process_collection.py.
Example:
  scripts/collections/run_collection_with_storage_fallback.sh \
    --storage auto \
    --source_dir "/path/to/collection" \
    --collection_name "my_collection" \
    --resume \
    --pdf_processor pymupdf
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --storage)
      storage_mode="${2:-}"
      shift 2
      ;;
    --external_base)
      external_base="${2:-}"
      shift 2
      ;;
    --local_output_root)
      local_output_root="${2:-}"
      shift 2
      ;;
    --local_registry_path)
      local_registry_path="${2:-}"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      pass_args+=("$1")
      shift
      ;;
  esac
done

if [[ "${storage_mode}" != "auto" && "${storage_mode}" != "external" && "${storage_mode}" != "local" ]]; then
  echo "Error: --storage must be one of auto, external, local." >&2
  exit 2
fi

external_available="false"
if [[ -d "${external_base}" ]]; then
  external_available="true"
fi

selected_output_root=""
selected_registry_path=""
selected_tmp=""
selected_storage=""

if [[ "${storage_mode}" == "external" ]]; then
  if [[ "${external_available}" != "true" ]]; then
    echo "Error: external storage requested but not available at: ${external_base}" >&2
    exit 3
  fi
  selected_storage="external"
elif [[ "${storage_mode}" == "local" ]]; then
  selected_storage="local"
else
  if [[ "${external_available}" == "true" ]]; then
    selected_storage="external"
  else
    selected_storage="local"
  fi
fi

if [[ "${selected_storage}" == "external" ]]; then
  selected_output_root="${external_base}/collections"
  selected_registry_path="${external_base}/processing_registry.yaml"
  selected_tmp="${external_base}/tmp"
  mkdir -p "${selected_output_root}" "${selected_tmp}" "${external_base}/logs"
else
  selected_output_root="${local_output_root}"
  selected_registry_path="${local_registry_path}"
  selected_tmp="/tmp"
  mkdir -p "${selected_output_root}"
fi

echo "Storage mode: ${storage_mode}"
echo "Selected storage: ${selected_storage}"
echo "Output root: ${selected_output_root}"
echo "Registry path: ${selected_registry_path}"
echo "TMPDIR: ${selected_tmp}"

cd "${PROJECT_ROOT}"
TMPDIR="${selected_tmp}" poetry run python scripts/collections/process_collection.py \
  --output_root "${selected_output_root}" \
  --registry_path "${selected_registry_path}" \
  "${pass_args[@]}"
