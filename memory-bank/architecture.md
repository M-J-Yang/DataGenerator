# 当前架构

本项目采用最简脚本式架构，只用于生成航空指令训练音频，不构建完整应用。

## 数据流

```text
cleaned_transcripts.csv
  -> generate_tts.py
  -> outputs/clean/*.wav + clean metadata rows
  -> augment_audio.py
  -> outputs/noisy/*.wav + noisy metadata rows
  -> outputs/metadata.csv
```

当前最终方言生成入口：

```text
run_standard_dialect_generation.sh
```

该脚本默认使用 `refs/*_standard.wav` 这 5 个普通话参考音频，并通过 CosyVoice3 `instruct2` 显式生成：

```text
东北话, 河南话, 陕西话, 甘肃话
```

旧的 `refs/*_light_accent.wav`/方言参考音频只保留为排查材料，不再作为最终方言生成策略。

## 核心脚本

- `generate_tts.py`：读取 CSV 和参考音频，生成 clean wav，并写入 clean metadata。
- `augment_audio.py`：读取 clean metadata，混入电台噪声并添加无线电效果，生成 noisy/radio wav。
- `run_standard_dialect_generation.sh`：当前推荐批量入口，遍历普通话参考音频和四种方言指令，支持断点续跑。
- `run_full_generation.sh`：旧全参考批量脚本，仍可用于历史流程，但不是当前最终方言策略。

## 外部依赖路径

- `CosyVoice/`：CosyVoice 推理代码。
- `pretrained_models/Fun-CosyVoice3-0.5B-2512/`：Fun-CosyVoice3 模型权重。
- `refs/`：参考说话人音频，最终策略使用 `*_standard.wav`。
- `noise/`：噪声素材，当前只使用 `radio_static_lw_freesound_84915_cc0.wav`。
- `outputs/`：生成产物和 metadata，不提交到 git。

## Metadata 合同

`outputs/metadata.csv` 字段为：

```text
utt_id,text,tts_text,speaker_id,accent,gender,speed,snr,noise_type,radio_effect,wav_path,split
```

其中 `text` 保留阿拉伯数字，`tts_text` 是送入 TTS 的航空读法文本，`accent` 记录实际生成方言或参考音频口音。

## 原则

不做完整工程化封装。优先快速、可控、可断点续跑地生成 wav 和 metadata。模型权重、参考音频、噪声素材、生成音频均不提交到 git。
