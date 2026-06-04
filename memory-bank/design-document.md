# 航空指令语音生成最简设计

## 目标

本项目不做完整软件系统，只用于快速生成可供其他 ASR/Paraformer 模型训练的航空指令合成语音数据。

输入为 `cleaned_transcripts.csv`，默认读取 `target` 字段。输出为 clean/noisy wav 文件和一个 `metadata.csv`。

## 最简流程

1. 从 `cleaned_transcripts.csv` 读取航空指令文本。
2. 对数字做航空读法预处理，用于 TTS 输入。
3. 使用 CosyVoice/Fun-CosyVoice3 生成 clean wav。
4. 对 clean wav 做噪声和无线电效果增强。
5. 生成 noisy wav。
6. 写出 `metadata.csv`，供下游训练读取。

## 推荐目录

```text
DataGenerator/
├── cleaned_transcripts.csv
├── CosyVoice/                         # GitHub 拉取的推理代码
├── pretrained_models/
│   └── Fun-CosyVoice3-0.5B-2512/       # ModelScope 下载的模型
├── refs/                              # 参考说话人音频
├── noise/                             # MUSAN 或自采噪声
├── outputs/
│   ├── clean/
│   ├── noisy/
│   └── metadata.csv
├── generate_tts.py                    # CSV -> clean wav
├── augment_audio.py                   # clean wav -> noisy/radio wav
└── memory-bank/
```

## 输入数据

`cleaned_transcripts.csv` 建议包含：

```text
key,raw_target,target,slot_types,spoken_digit_tags,is_digit_focus
```

第一版只使用 `target`。后续需要更口语化样本时再使用 `raw_target`。

## 数字读法

TTS 输入文本使用航空读法，metadata 标注文本仍保留阿拉伯数字。

基础映射：

```text
0 -> 洞
1 -> 幺
2 -> 两
7 -> 拐
3/4/5/6/8/9 -> 三/四/五/六/八/九
```

规则：

- 呼号、频率：逐位读。
- 高度、气压：按数值读。
- 无法判断类型时，优先逐位读，并在 metadata 中保留原始文本。

## TTS 模型

主模型直接使用 ModelScope 的：

```text
FunAudioLLM/Fun-CosyVoice3-0.5B-2512
```

模型下载到：

```text
pretrained_models/Fun-CosyVoice3-0.5B-2512
```

推理代码使用 GitHub 仓库：

```text
https://github.com/FunAudioLLM/CosyVoice
```

## 生成策略

初始建议：

```text
20000 条文本 × 6 个说话人 × 2 种口音版本 × clean/noisy
```

不要一开始生成 5 万条。先用 10 条文本跑通，再扩大到全量。

参考说话人第一版使用 12 段 wav：6 个说话人，每人普通话版本和轻微口音/方言版本各 1 段。每段保持单一稳定口音，不在同一段参考音频中混合普通话和方言。

## 噪声和无线电增强

TTS 只生成 clean wav，噪声后处理完成。

推荐增强：

- 重采样到 8kHz
- 带通滤波 300-3400Hz
- 混入 MUSAN 或自采电台底噪
- SNR 随机选择 20、10、5、0dB
- 少量 clipping
- 少量短时静音/dropout

## Metadata

`outputs/metadata.csv` 至少包含：

```text
utt_id,text,tts_text,speaker_id,accent,gender,speed,snr,noise_type,radio_effect,wav_path,split
```

其中：

- `text`：训练标注，保留阿拉伯数字。
- `tts_text`：实际送入 TTS 的文本。
- `wav_path`：音频路径。
- `radio_effect`：是否应用无线电效果。

## 最小验收

- 能用 1 条文本和 1 个参考音频生成 clean wav。
- 能把 clean wav 增强成 noisy/radio wav。
- 能生成可被训练脚本读取的 `metadata.csv`。
- 全量运行前，先用 10 条文本完成 smoke test。
