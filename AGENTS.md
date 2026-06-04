# Repository Guidelines

## Project Structure & Module Organization

This repository is for generating synthetic aviation-command audio, not for building a full application. The current planning docs live in `memory-bank/`.

Recommended working layout:

```text
cleaned_transcripts.csv                 # input text CSV
CosyVoice/                              # cloned inference code
pretrained_models/Fun-CosyVoice3-0.5B-2512/
refs/                                   # reference speaker wavs
noise/                                  # MUSAN or radio/airport noise wavs
outputs/clean/                          # generated clean wavs
outputs/noisy/                          # augmented wavs
outputs/metadata.csv                    # training metadata
generate_tts.py                         # CSV -> clean wav
augment_audio.py                        # clean wav -> noisy/radio wav
memory-bank/                            # design, tech stack, plan, progress
```

## Development Commands

Use a simple Python environment. Follow CosyVoice installation instructions first, then add lightweight data-processing dependencies.

Useful commands:

```bash
git clone https://github.com/FunAudioLLM/CosyVoice
modelscope download --model FunAudioLLM/Fun-CosyVoice3-0.5B-2512 --local_dir pretrained_models/Fun-CosyVoice3-0.5B-2512
python generate_tts.py
python augment_audio.py
```

Start with one sample, then ten samples, then full generation.

## Coding Style & Naming Conventions

Keep scripts direct and readable. Use Python 3.10, 4-space indentation, and `snake_case` names. Avoid unnecessary frameworks, package scaffolding, web servers, databases, or task queues.

Use clear file naming for outputs, for example:

```text
outputs/clean/ch01_01_001_spk001.wav
outputs/noisy/ch01_01_001_spk001_snr10_radio.wav
```

## Data and Metadata Guidelines

Do not commit model weights, generated wavs, private speaker references, or large noise datasets. Keep those paths local.

`outputs/metadata.csv` should include at least:

```text
utt_id,text,tts_text,speaker_id,snr,noise_type,radio_effect,wav_path
```

`text` keeps Arabic numerals for training labels. `tts_text` stores the spoken-form text sent to TTS.

## Agent-Specific Instructions

**写任何代码前必须完整阅读 `memory-bank/architecture.md`。**

**写任何代码前必须完整阅读 `memory-bank/design-document.md`。**

**每完成一个重大功能或里程碑后，必须更新 `memory-bank/progress.md`。**
