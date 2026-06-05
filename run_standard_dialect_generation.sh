#!/usr/bin/env bash
set -euo pipefail

export OMP_NUM_THREADS=${OMP_NUM_THREADS:-1}
export MKL_NUM_THREADS=${MKL_NUM_THREADS:-1}

CSV=${CSV:-cleaned_transcripts.csv}
REFS_DIR=${REFS_DIR:-refs}
CLEAN_DIR=${CLEAN_DIR:-outputs/clean}
NOISY_DIR=${NOISY_DIR:-outputs/noisy}
METADATA=${METADATA:-outputs/metadata.csv}
LIMIT=${LIMIT:-20000}
START=${START:-0}
DIALECTS=${DIALECTS:-东北话,河南话,陕西话,甘肃话}
REGULAR_SNRS=${REGULAR_SNRS:-20,10,5}
EXTREME_SNR=${EXTREME_SNR:-0}
EXTREME_LIMIT=${EXTREME_LIMIT:-100}
SKIP_AUGMENT=${SKIP_AUGMENT:-0}

IFS=',' read -r -a dialect_list <<< "${DIALECTS}"
standard_refs=("${REFS_DIR}"/*_standard.wav)

if [[ ! -e "${standard_refs[0]}" ]]; then
  echo "No standard refs found: ${REFS_DIR}/*_standard.wav" >&2
  exit 1
fi

for ref_path in "${standard_refs[@]}"; do
  ref_name=$(basename "${ref_path}" .wav)
  for dialect in "${dialect_list[@]}"; do
    python generate_tts.py \
      --csv "${CSV}" \
      --refs-dir "${REFS_DIR}" \
      --ref "${ref_name}" \
      --start "${START}" \
      --limit "${LIMIT}" \
      --mode auto \
      --dialect "${dialect}" \
      --output-dir "${CLEAN_DIR}" \
      --metadata "${METADATA}" \
      --append-metadata \
      --skip-existing
  done
done

if [[ "${SKIP_AUGMENT}" == "1" ]]; then
  exit 0
fi

python augment_audio.py \
  --metadata "${METADATA}" \
  --noise-dir noise \
  --output-dir "${NOISY_DIR}" \
  --snrs "${REGULAR_SNRS}" \
  --limit $((LIMIT * ${#standard_refs[@]} * ${#dialect_list[@]})) \
  --append-metadata \
  --skip-existing

python augment_audio.py \
  --metadata "${METADATA}" \
  --noise-dir noise \
  --output-dir "${NOISY_DIR}" \
  --snrs "${EXTREME_SNR}" \
  --limit "${EXTREME_LIMIT}" \
  --append-metadata \
  --skip-existing
