# 航空指令语音生成最简设计

## 目标

本项目只用于快速生成可供 ASR/Paraformer 等下游模型训练的航空指令合成语音数据。

输入为 `cleaned_transcripts.csv`，默认读取 `key` 和 `target`。输出为 clean/noisy wav 文件和 metadata CSV。

## 当前最终生成策略

当前用户确认的最终策略：

```text
20000 条文本 × 5 个普通话参考说话人 × 4 种方言指令
```

参考音频只使用：

```text
refs/spk001_standard.wav
refs/spk002_standard.wav
refs/spk003_standard.wav
refs/spk004_standard.wav
refs/spk005_standard.wav
```

方言通过 CosyVoice3 `instruct2` 显式指定，不再依赖方言参考音频：

```text
东北话
河南话
陕西话
甘肃话
```

输出文件名和 `utt_id` 使用方言 slug 区分，例如：

```text
utt_001464_spk001_standard_dongbei.wav
utt_001464_spk001_standard_henan.wav
utt_001464_spk001_standard_shaanxi.wav
utt_001464_spk001_standard_gansu.wav
```

## 最简流程

1. 从 `cleaned_transcripts.csv` 读取航空指令文本。
2. 对阿拉伯数字做航空读法预处理，用于 TTS 输入。
3. 使用 5 个普通话参考音频和 4 种方言 instruct 生成 clean wav。
4. 对 clean wav 做电台噪声和无线电效果增强。
5. 生成 noisy/radio wav。
6. 写出 metadata，供下游训练读取。

## 推荐目录

```text
DataGenerator/
├── cleaned_transcripts.csv
├── CosyVoice/
├── pretrained_models/
│   └── Fun-CosyVoice3-0.5B-2512/
├── refs/
│   ├── spk001_standard.wav
│   ├── spk002_standard.wav
│   ├── spk003_standard.wav
│   ├── spk004_standard.wav
│   └── spk005_standard.wav
├── noise/
│   └── radio_static_lw_freesound_84915_cc0.wav
├── outputs/
│   ├── clean/
│   ├── noisy/
│   └── metadata.csv
├── generate_tts.py
├── augment_audio.py
├── run_standard_dialect_generation.sh
└── memory-bank/
```

## 输入数据

`cleaned_transcripts.csv` 第一版至少需要：

```text
key,target
```

当前数据已扩充到 20000 条，并保留 `dialogue_id`、`turn_index`、`speaker_role` 等辅助字段。生成脚本只强依赖 `key` 和 `target`。

## 数字读法

TTS 输入文本使用航空读法，metadata 标注文本仍保留阿拉伯数字。

基础映射：

```text
0 -> 洞
1 -> 幺
2 -> 两
3 -> 三
4 -> 四
5 -> 五
6 -> 六
7 -> 拐
8 -> 八
9 -> 九
```

当前实现是最小逐字符替换。示例：

```text
4151 -> 四幺五幺
733.9 -> 拐三三.九
0到2 -> 洞到两
```

## TTS 模型

主模型使用 ModelScope 的：

```text
FunAudioLLM/Fun-CosyVoice3-0.5B-2512
```

模型路径：

```text
pretrained_models/Fun-CosyVoice3-0.5B-2512
```

推理代码：

```text
CosyVoice/
```

## 噪声和无线电增强

TTS 只生成 clean wav，噪声由 `augment_audio.py` 后处理完成。

当前增强策略：

- 重采样到 8kHz。
- 300-3400Hz 带通滤波。
- 混入 `noise/radio_static_lw_freesound_84915_cc0.wav`。
- 常规 SNR：20、10、5dB。
- 极端 SNR：0dB 少量抽样。
- 轻微 clipping 和短时 dropout。

## Metadata

字段为：

```text
utt_id,text,tts_text,speaker_id,accent,gender,speed,snr,noise_type,radio_effect,wav_path,split
```

其中：

- `text`：训练标注，保留阿拉伯数字。
- `tts_text`：实际送入 TTS 的航空读法文本。
- `accent`：实际方言，例如 `东北话`、`河南话`、`陕西话`、`甘肃话`。
- `wav_path`：音频路径。
- `radio_effect`：clean 为 `false`，noisy/radio 为 `true`。

## 验收方式

先用 `SKIP_AUGMENT=1` 生成 clean 听测样本，用户确认方言听感后，再执行全量 clean/noisy。

当前听测样本：

```text
outputs/standard_dialect_test/
outputs/standard_dialect_test_metadata.csv
```

样本规模为 5 个普通话参考 × 4 种方言 = 20 条 clean wav。
