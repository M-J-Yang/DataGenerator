# Repository Guidelines

## Project Structure & Module Organization

This repository currently contains planning documents for an aviation-command TTS data generator: `memory-bank/design-document.md` and `memory-bank/tech-stack.md`. The intended implementation is a Python package:

```text
atc_tts_generator/      # source package
configs/generation.yaml # runtime configuration
tests/                  # pytest tests
atc_tts_dataset/        # generated data, wavs, metadata, logs
```

Keep source modules focused: `normalizer.py` for aviation text rules, `cosyvoice_client.py` for TTS integration, `augmentation.py` and `radio_effects.py` for audio processing, and `quality.py` for validation.

## Build, Test, and Development Commands

Recommended setup:

```bash
conda create -n atc-tts python=3.10 -y
conda activate atc-tts
pip install -e .
pip install -r requirements-dev.txt
```

Expected CLI commands after implementation:

```bash
atc-tts generate --config configs/generation.yaml --stage all
atc-tts validate --config configs/generation.yaml
atc-tts inspect --metadata atc_tts_dataset/metadata.csv
pytest
ruff check .
```

`generate` creates clean/noisy wavs and metadata, `validate` runs quality checks, and `inspect` summarizes generated data.

## Coding Style & Naming Conventions

Use Python 3.10, 4-space indentation, type hints for public functions, and clear module boundaries. Prefer small, testable functions over large scripts. Use `snake_case` for functions, variables, files, and config keys; use `PascalCase` for classes such as `CosyVoiceClient`.

Use `ruff` for linting and formatting. Keep generated audio, model weights, and large datasets out of source control.

## Testing Guidelines

Use `pytest`. Name tests as `tests/test_*.py` and test functions as `test_*`. Prioritize deterministic unit tests for:

- digit and slot normalization
- YAML/Pydantic config validation
- metadata row creation
- SNR mixing math
- silence, duration, and sample-rate checks
- skip-existing resume logic

Treat real CosyVoice GPU inference as a smoke or integration test, not a normal unit test.

## Commit & Pull Request Guidelines

No git history is present in this workspace, so use a simple convention: short imperative commits such as `Add text normalizer` or `Implement metadata validation`.

Pull requests should include a concise summary, changed modules, test results, and any data-generation assumptions. Link related issues when available. For changes affecting audio output, include sample metadata rows and the exact config used.

## Security & Configuration Tips

Do not commit reference speaker audio, generated wavs, model checkpoints, or private datasets unless explicitly approved. Keep paths and generation parameters in `configs/generation.yaml`; avoid hard-coded absolute paths.
**重要提示**

**写任何代码前必须完整阅读memory-bank/architecture.md**

**写任何代码前必须完整阅读memory-bank/design-document.md**

**每完成一个重大功能或里程碑后，必须更新memory-bank/architecture.md**