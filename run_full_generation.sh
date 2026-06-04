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
REGULAR_SNRS=${REGULAR_SNRS:-20,10,5}
EXTREME_SNR=${EXTREME_SNR:-0}
EXTREME_LIMIT=${EXTREME_LIMIT:-100}

for ref_path in "${REFS_DIR}"/*.wav; do
  ref_name=$(basename "${ref_path}" .wav)
  python generate_tts.py \
    --csv "${CSV}" \
    --refs-dir "${REFS_DIR}" \
    --ref "${ref_name}" \
    --limit "${LIMIT}" \
    --output-dir "${CLEAN_DIR}" \
    --metadata "${METADATA}" \
    --append-metadata \
    --skip-existing
done

python augment_audio.py \
  --metadata "${METADATA}" \
  --noise-dir noise \
  --output-dir "${NOISY_DIR}" \
  --snrs "${REGULAR_SNRS}" \
  --limit $((LIMIT * 10)) \
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
