#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
RUNNER="${SCRIPT_DIR}/run_collection_with_storage_fallback.sh"

source_root="/Users/scottwilliams/Library/CloudStorage/OneDrive-ShanghaiAmericanSchool/2_Models-Frameworks-Research"
storage="auto" # auto | external | local
external_base="/Volumes/My Passport/knowledge-hub"
pdf_processor="pymupdf"
start_at=""
max_dirs=0
resume="true"
dry_run="false"
min_source_free_gb=50
min_external_free_gb=25
exclude_top_dirs=("__knowledge_base" "_gsdata_" "Z_Archived")

usage() {
  cat <<'EOF'
Usage:
  scripts/collections/run_root_collections_batch.sh [options]

Options:
  --source_root <path>           Top-level root containing collection directories.
  --storage auto|external|local  Storage mode passed through to collection runner.
  --external_base <path>         External knowledge-hub base path.
  --pdf_processor <name>         PDF processor (default: pymupdf).
  --start_at <dir_name>          Start when this top-level directory name is reached.
  --max_dirs <n>                 Process at most n directories (0 = no limit).
  --no_resume                    Do not pass --resume.
  --dry_run                      Run each directory in dry-run mode.
  --min_source_free_gb <n>       Stop if source volume free space is below n GiB (default: 50).
  --min_external_free_gb <n>     Stop if external output volume free space is below n GiB (default: 25).
  --exclude_top_dir <name>       Exclude top-level directory name (repeatable).
  --help                         Show this help text.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --source_root)
      source_root="${2:-}"
      shift 2
      ;;
    --storage)
      storage="${2:-}"
      shift 2
      ;;
    --external_base)
      external_base="${2:-}"
      shift 2
      ;;
    --pdf_processor)
      pdf_processor="${2:-}"
      shift 2
      ;;
    --start_at)
      start_at="${2:-}"
      shift 2
      ;;
    --max_dirs)
      max_dirs="${2:-0}"
      shift 2
      ;;
    --no_resume)
      resume="false"
      shift
      ;;
    --dry_run)
      dry_run="true"
      shift
      ;;
    --min_source_free_gb)
      min_source_free_gb="${2:-0}"
      shift 2
      ;;
    --min_external_free_gb)
      min_external_free_gb="${2:-0}"
      shift 2
      ;;
    --exclude_top_dir)
      exclude_top_dirs+=("${2:-}")
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ ! -x "${RUNNER}" ]]; then
  echo "Runner script missing or not executable: ${RUNNER}" >&2
  exit 3
fi

if [[ ! -d "${source_root}" ]]; then
  echo "Source root not found: ${source_root}" >&2
  exit 4
fi

run_id="$(date '+%Y%m%d_%H%M%S')"
log_base="${external_base}/logs"
if [[ ! -d "${log_base}" ]]; then
  log_base="${PROJECT_ROOT}/data/output/collections/logs"
fi
mkdir -p "${log_base}"

batch_log="${log_base}/root_batch_${run_id}.log"
summary_file="${log_base}/root_batch_${run_id}_summary.txt"

slugify() {
  local value="$1"
  local slug
  slug="$(printf '%s' "${value}" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//')"
  if [[ -z "${slug}" ]]; then
    slug="collection"
  fi
  printf '%s' "${slug}"
}

contains_excluded() {
  local dir_name="$1"
  local excluded
  for excluded in "${exclude_top_dirs[@]}"; do
    if [[ "${dir_name}" == "${excluded}" ]]; then
      return 0
    fi
  done
  return 1
}

available_gb() {
  local path="$1"
  local avail_kb
  avail_kb="$(df -Pk "${path}" | awk 'NR==2 {print $4}')"
  if [[ -z "${avail_kb}" ]]; then
    echo 0
    return
  fi
  echo $((avail_kb / 1024 / 1024))
}

should_stop_for_space() {
  local label="$1"
  local path="$2"
  local min_gb="$3"
  if [[ "${min_gb}" -le 0 ]]; then
    return 1
  fi
  local free_gb
  free_gb="$(available_gb "${path}")"
  printf '[%s] SPACE %s free=%sGiB min=%sGiB (%s)\n' \
    "$(date '+%F %T')" "${label}" "${free_gb}" "${min_gb}" "${path}" | tee -a "${batch_log}"
  if [[ "${free_gb}" -lt "${min_gb}" ]]; then
    printf '[%s] STOP low space on %s: free=%sGiB < min=%sGiB\n' \
      "$(date '+%F %T')" "${label}" "${free_gb}" "${min_gb}" | tee -a "${batch_log}"
    return 0
  fi
  return 1
}

printf 'Run ID: %s\n' "${run_id}" | tee -a "${batch_log}"
printf 'Source root: %s\n' "${source_root}" | tee -a "${batch_log}"
printf 'Storage: %s\n' "${storage}" | tee -a "${batch_log}"
printf 'External base: %s\n' "${external_base}" | tee -a "${batch_log}"
printf 'PDF processor: %s\n' "${pdf_processor}" | tee -a "${batch_log}"
printf 'Resume: %s\n' "${resume}" | tee -a "${batch_log}"
printf 'Dry run: %s\n' "${dry_run}" | tee -a "${batch_log}"
printf 'Min source free GiB: %s\n' "${min_source_free_gb}" | tee -a "${batch_log}"
printf 'Min external free GiB: %s\n' "${min_external_free_gb}" | tee -a "${batch_log}"
printf 'Exclude top dirs: %s\n' "${exclude_top_dirs[*]}" | tee -a "${batch_log}"
printf '\n' | tee -a "${batch_log}"

processed=0
failed=0
started=false
failed_dirs=()

while IFS= read -r dir_path; do
  dir_name="$(basename "${dir_path}")"

  if contains_excluded "${dir_name}"; then
    continue
  fi

  if [[ -n "${start_at}" && "${started}" == "false" ]]; then
    if [[ "${dir_name}" != "${start_at}" ]]; then
      continue
    fi
  fi
  started=true

  if [[ "${max_dirs}" -gt 0 && "${processed}" -ge "${max_dirs}" ]]; then
    break
  fi

  if should_stop_for_space "source_volume" "${source_root}" "${min_source_free_gb}"; then
    break
  fi
  if [[ "${storage}" != "local" ]]; then
    if [[ -d "${external_base}" ]] && should_stop_for_space "external_volume" "${external_base}" "${min_external_free_gb}"; then
      break
    fi
  fi

  collection_name="$(slugify "${dir_name}")"
  collection_log="${log_base}/root_batch_${run_id}_${collection_name}.log"

  printf '[%s] START %s -> %s\n' "$(date '+%F %T')" "${dir_name}" "${collection_name}" | tee -a "${batch_log}"

  cmd=(
    "${RUNNER}"
    "--storage" "${storage}"
    "--external_base" "${external_base}"
    "--source_dir" "${dir_path}"
    "--collection_name" "${collection_name}"
    "--pdf_processor" "${pdf_processor}"
    "--exclude_dir" "__knowledge_base"
    "--exclude_dir" "_gsdata_"
    "--exclude_dir" "Z_Archived"
  )

  if [[ "${resume}" == "true" ]]; then
    cmd+=("--resume")
  fi
  if [[ "${dry_run}" == "true" ]]; then
    cmd+=("--dry_run")
  fi

  set +e
  "${cmd[@]}" 2>&1 | tee "${collection_log}"
  rc=${PIPESTATUS[0]}
  set -e

  if [[ ${rc} -ne 0 ]]; then
    failed=$((failed + 1))
    failed_dirs+=("${dir_name}")
    printf '[%s] FAIL %s (exit=%d)\n' "$(date '+%F %T')" "${dir_name}" "${rc}" | tee -a "${batch_log}"
  else
    printf '[%s] DONE %s\n' "$(date '+%F %T')" "${dir_name}" | tee -a "${batch_log}"
  fi

  processed=$((processed + 1))
  printf '\n' | tee -a "${batch_log}"
done < <(find "${source_root}" -mindepth 1 -maxdepth 1 -type d | LC_ALL=C sort)

{
  echo "run_id: ${run_id}"
  echo "source_root: ${source_root}"
  echo "processed_directories: ${processed}"
  echo "failed_directories: ${failed}"
  if [[ ${#failed_dirs[@]} -gt 0 ]]; then
    echo "failed_list:"
    for d in "${failed_dirs[@]}"; do
      echo "  - ${d}"
    done
  else
    echo "failed_list: []"
  fi
  echo "batch_log: ${batch_log}"
} | tee "${summary_file}"

printf 'Summary written: %s\n' "${summary_file}" | tee -a "${batch_log}"
