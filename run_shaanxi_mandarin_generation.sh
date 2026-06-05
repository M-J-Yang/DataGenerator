#!/usr/bin/env bash
set -euo pipefail

export OMP_NUM_THREADS=${OMP_NUM_THREADS:-1}
export MKL_NUM_THREADS=${MKL_NUM_THREADS:-1}

CSV=${CSV:-cleaned_transcripts.csv}
REFS_DIR=${REFS_DIR:-refs}
LIMIT=${LIMIT:-20000}
START=${START:-0}
CLEAN_DIR=${CLEAN_DIR:-outputs/full_shaanxi_mandarin/clean}
NOISY_DIR=${NOISY_DIR:-outputs/full_shaanxi_mandarin/noisy}
METADATA=${METADATA:-outputs/full_shaanxi_mandarin/metadata.csv}
REGULAR_SNRS=${REGULAR_SNRS:-20,10,5}
EXTREME_SNR=${EXTREME_SNR:-0}
EXTREME_LIMIT=${EXTREME_LIMIT:-100}
SKIP_NOISY=${SKIP_NOISY:-0}
PYTHON_BIN=${PYTHON_BIN:-/root/miniconda3/bin/python}

mkdir -p "${CLEAN_DIR}" "${NOISY_DIR}" "$(dirname "${METADATA}")"

standard_refs=("${REFS_DIR}"/*_standard.wav)
if [[ ! -e "${standard_refs[0]}" ]]; then
  echo "No standard refs found: ${REFS_DIR}/*_standard.wav" >&2
  exit 1
fi

ref_count=${#standard_refs[@]}
accent_count=2
clean_limit=$((LIMIT * ref_count * accent_count))

echo "CSV=${CSV}"
echo "REFS_DIR=${REFS_DIR}"
echo "START=${START} LIMIT=${LIMIT}"
echo "CLEAN_DIR=${CLEAN_DIR}"
echo "NOISY_DIR=${NOISY_DIR}"
echo "METADATA=${METADATA}"
echo "PYTHON_BIN=${PYTHON_BIN}"
echo "standard refs=${ref_count}; accents=mandarin,shaanxi; clean_limit=${clean_limit}"

for ref_path in "${standard_refs[@]}"; do
  ref_name=$(basename "${ref_path}" .wav)
  echo "[mandarin] ${ref_name}"
  "${PYTHON_BIN}" generate_tts.py \
    --csv "${CSV}" \
    --refs-dir "${REFS_DIR}" \
    --ref "${ref_name}" \
    --start "${START}" \
    --limit "${LIMIT}" \
    --mode auto \
    --output-dir "${CLEAN_DIR}" \
    --metadata "${METADATA}" \
    --append-metadata \
    --skip-existing
done

for ref_path in "${standard_refs[@]}"; do
  ref_name=$(basename "${ref_path}" .wav)
  echo "[shaanxi] ${ref_name}"
  "${PYTHON_BIN}" generate_tts.py \
    --csv "${CSV}" \
    --refs-dir "${REFS_DIR}" \
    --ref "${ref_name}" \
    --start "${START}" \
    --limit "${LIMIT}" \
    --mode auto \
    --dialect 陕西话 \
    --output-dir "${CLEAN_DIR}" \
    --metadata "${METADATA}" \
    --append-metadata \
    --skip-existing
done

if [[ "${SKIP_NOISY}" == "1" ]]; then
  echo "SKIP_NOISY=1, clean generation finished."
  exit 0
fi

echo "[noisy] regular SNRs=${REGULAR_SNRS}; limit=${clean_limit}"
"${PYTHON_BIN}" augment_audio.py \
  --metadata "${METADATA}" \
  --noise-dir noise \
  --output-dir "${NOISY_DIR}" \
  --snrs "${REGULAR_SNRS}" \
  --limit "${clean_limit}" \
  --append-metadata \
  --skip-existing

echo "[noisy] extreme SNR=${EXTREME_SNR}; limit=${EXTREME_LIMIT}"
"${PYTHON_BIN}" augment_audio.py \
  --metadata "${METADATA}" \
  --noise-dir noise \
  --output-dir "${NOISY_DIR}" \
  --snrs "${EXTREME_SNR}" \
  --limit "${EXTREME_LIMIT}" \
  --append-metadata \
  --skip-existing

echo "Done. Metadata: ${METADATA}"
