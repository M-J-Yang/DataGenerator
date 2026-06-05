# 最简实施计划

本文档面向 AI 开发者。目标是快速生成航空指令训练音频，不构建完整软件项目。每一步都要小而具体，并包含验证方式。

## 步骤 1：准备目录

实施指令：确认根目录存在 `memory-bank/`。创建 `refs/`、`noise/`、`outputs/clean/`、`outputs/noisy/`、`pretrained_models/` 目录。

验证：检查这些目录都存在，且不会覆盖已有数据。

状态：已完成。

## 步骤 2：拉取 CosyVoice 代码

实施指令：从 `https://github.com/FunAudioLLM/CosyVoice` 拉取代码到本地 `CosyVoice/`。如果目录已存在，只检查其 git 远端是否正确，不强制覆盖。

验证：确认 `CosyVoice/` 存在，且包含 CosyVoice 推理相关文件。

状态：已完成。

## 步骤 3：下载 Fun-CosyVoice3 模型

实施指令：使用 ModelScope 下载 `FunAudioLLM/Fun-CosyVoice3-0.5B-2512` 到 `pretrained_models/Fun-CosyVoice3-0.5B-2512/`。

验证：确认模型目录存在，且不是空目录。

状态：已完成。

## 步骤 4：准备输入 CSV

实施指令：把 `cleaned_transcripts.csv` 放到项目根目录。第一版只读取 `key` 和 `target`，`key` 用作音频 ID。

验证：读取 CSV，确认至少包含 `key` 和 `target`，且 `target` 非空。

状态：已完成，当前 CSV 已扩充到 20000 条。

## 步骤 5：准备参考说话人

实施指令：把参考说话人 wav 放入 `refs/`。当前已整理 5 个说话人的普通话和方言/轻口音版本，共 10 段。

当前最终生成策略只使用普通话版本：

```text
refs/spk001_standard.wav
refs/spk002_standard.wav
refs/spk003_standard.wav
refs/spk004_standard.wav
refs/spk005_standard.wav
```

`refs/*_light_accent.wav` 只保留为排查材料，不作为最终方言生成策略。

验证：确认 wav 可正常读取，采样率 24000 Hz，单声道，时长在可用范围内。

状态：已完成。

## 步骤 6：准备噪声素材

实施指令：把电台/机场噪声放入 `noise/`。当前按用户要求只使用：

```text
noise/radio_static_lw_freesound_84915_cc0.wav
```

验证：确认 wav 可正常读取。

状态：已完成。

## 步骤 7：编写 generate_tts.py

实施指令：编写单脚本 `generate_tts.py`，读取 CSV 和 refs，调用 CosyVoice3 生成 clean wav。

当前能力：

- 支持 `--limit`、`--start`、`--ref-limit`、`--ref`。
- 支持 `--mode auto/cross_lingual/zero_shot/instruct2`。
- 指定 `--dialect` 或 `--instruct-text` 时，`--mode auto` 会强制使用 `instruct2`。
- 支持 `--skip-existing` 和 `--append-metadata` 断点续跑。
- 方言输出使用 slug 写入文件名和 `utt_id`，避免覆盖。

验证：用 1 条文本和 1 个参考说话人生成 1 个 clean wav，确认文件存在、非空、可读取。

状态：已完成。

## 步骤 8：加入数字读法预处理

实施指令：在 `generate_tts.py` 中加入最小数字替换逻辑。TTS 文本使用幺、两、洞、拐等航空读法；metadata 中训练文本保留阿拉伯数字。

验证：输入包含 `4151`、`733.9`、`0到2` 的样本时，确认 `metadata.text` 保留数字，`metadata.tts_text` 使用中文读法。

状态：已完成。

## 步骤 9：编写 augment_audio.py

实施指令：编写单脚本 `augment_audio.py`，读取 clean wav，混入噪声并添加无线电效果，输出到 `outputs/noisy/`。

当前能力：

- 输出 8kHz 单声道 16-bit wav。
- 支持 SNR 列表，例如 `20,10,5,0`。
- 支持带通、轻微 clipping、短时 dropout。
- 支持 `--append-metadata` 和 `--skip-existing`。

验证：对 1 个 clean wav 生成 1 个 noisy wav，确认输出采样率为 8kHz，文件非空。

状态：已完成。

## 步骤 10：生成 metadata.csv

实施指令：在生成 clean 和 noisy 时写入 metadata。字段为：

```text
utt_id,text,tts_text,speaker_id,accent,gender,speed,snr,noise_type,radio_effect,wav_path,split
```

验证：确认 metadata 行数与生成 wav 数量一致，所有 `wav_path` 都能找到文件。

状态：已完成。

## 步骤 11：小样本 smoke test

实施指令：使用少量文本、1-2 个说话人、1 类噪声生成 clean 和 noisy 数据。

验证：确认 clean/noisy wav 都存在，metadata 无空路径，随机抽听几条音频。

状态：已完成。

## 步骤 12：全量生成

当前最终策略：

```text
20000 条文本 × 5 个普通话参考音频 × 4 种方言 instruct
```

推荐先生成 clean 听测样本：

```bash
START=1463 LIMIT=1 CLEAN_DIR=outputs/standard_dialect_test METADATA=outputs/standard_dialect_test_metadata.csv SKIP_AUGMENT=1 ./run_standard_dialect_generation.sh
```

用户听测合格后，再全量断点续跑 clean/noisy：

```bash
./run_standard_dialect_generation.sh
```

可通过环境变量控制：

```text
START=0
LIMIT=20000
DIALECTS=东北话,河南话,陕西话,甘肃话
REGULAR_SNRS=20,10,5
EXTREME_SNR=0
EXTREME_LIMIT=100
SKIP_AUGMENT=0
```

验证：确认输出数量符合预期，metadata 可被下游训练脚本读取，所有 `wav_path` 存在。

状态：小批量新策略听测样本已完成；全量等待用户听测确认。

## 步骤 13：更新进度和提交

实施指令：每完成一个阶段，在 `memory-bank/progress.md` 记录当前状态、已生成数量、失败样本和下一步；代码/文档变更按需 git commit/push。

验证：确认 `progress.md` 记录了最近一次生成结果，git 状态和远端提交符合用户要求。

状态：持续进行。
