# 当前架构

本项目采用最简脚本式架构，只用于生成航空指令训练音频。

## 数据流

`cleaned_transcripts.csv` -> `generate_tts.py` -> `outputs/clean/` -> `augment_audio.py` -> `outputs/noisy/` + `outputs/metadata.csv`

## 外部依赖

- `CosyVoice/`：从 GitHub 拉取的推理代码。
- `pretrained_models/Fun-CosyVoice3-0.5B-2512/`：从 ModelScope 下载的模型权重。
- `refs/`：参考说话人音频。
- `noise/`：噪声素材。

## 原则

不做完整工程化封装。优先快速、可控地生成 wav 和 metadata。
