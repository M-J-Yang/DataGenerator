# 最简实施计划

本文档面向 AI 开发者。目标是快速生成航空指令训练音频，不构建完整软件项目。每一步都要小而具体，并包含验证方式。

## 步骤 1：准备目录

实施指令：确认根目录存在 `memory-bank/`。创建 `refs/`、`noise/`、`outputs/clean/`、`outputs/noisy/`、`pretrained_models/` 目录。

验证：检查这些目录都存在，且不会覆盖已有数据。

## 步骤 2：拉取 CosyVoice 代码

实施指令：从 `https://github.com/FunAudioLLM/CosyVoice` 拉取代码到本地 `CosyVoice/`。如果目录已存在，只检查其 git 远端是否正确，不强制覆盖。

验证：确认 `CosyVoice/` 存在，且包含 CosyVoice 推理相关文件。

## 步骤 3：下载 Fun-CosyVoice3 模型

实施指令：使用 ModelScope 下载 `FunAudioLLM/Fun-CosyVoice3-0.5B-2512` 到 `pretrained_models/Fun-CosyVoice3-0.5B-2512/`。

验证：确认模型目录存在，且不是空目录。

## 步骤 4：准备输入 CSV

实施指令：把 `cleaned_transcripts.csv` 放到项目根目录。第一版只读取 `target` 字段，`key` 用作音频 ID。

验证：读取 CSV，确认至少包含 `key` 和 `target`，且 `target` 非空。

## 步骤 5：准备参考说话人

实施指令：把 10 段参考说话人 wav 放入 `refs/`。当前使用 5 个说话人，每人普通话版本和轻微口音/方言版本各 1 段。文件名使用 `spk001_standard.wav`、`spk001_light_accent.wav` 这类格式。

验证：确认 `refs/` 下存在 10 个 wav 文件，每个文件可正常读取，时长建议 10-20 秒，允许范围 3-30 秒。

## 步骤 6：准备噪声素材

实施指令：把 MUSAN 或自采机场/电台噪声放入 `noise/`。可以先只放一类 radio noise。

验证：确认 `noise/` 下存在 wav 文件，且可正常读取。

## 步骤 7：编写 generate_tts.py

实施指令：编写单脚本 `generate_tts.py`，读取 CSV 和 refs，调用 CosyVoice 生成 clean wav。先支持少量样本参数，例如只生成前 10 条。

验证：用 1 条文本和 1 个参考说话人生成 1 个 clean wav，确认文件存在、非空、可播放或可读取。

## 步骤 8：加入数字读法预处理

实施指令：在 `generate_tts.py` 中加入最小数字替换逻辑。TTS 文本使用幺、两、洞、拐；metadata 中训练文本保留阿拉伯数字。

验证：输入包含 `4151`、`733.9`、`0到2` 的样本时，确认写入 metadata 的 `text` 保留数字，`tts_text` 使用中文读法。

## 步骤 9：编写 augment_audio.py

实施指令：编写单脚本 `augment_audio.py`，读取 clean wav，混入噪声并添加无线电效果，输出到 `outputs/noisy/`。

验证：对 1 个 clean wav 生成 1 个 noisy wav，确认输出采样率为 8kHz，文件非空。

## 步骤 10：生成 metadata.csv

实施指令：在生成 clean 和 noisy 时写入 `outputs/metadata.csv`。字段至少包含 `utt_id,text,tts_text,speaker_id,snr,noise_type,radio_effect,wav_path`。

验证：确认 metadata 行数与生成 wav 数量一致，所有 `wav_path` 都能找到文件。

## 步骤 11：小样本 smoke test

实施指令：使用 10 条文本、1-2 个说话人、1 类噪声生成 clean 和 noisy 数据。

验证：确认 clean/noisy wav 都存在，metadata 无空路径，随机抽听几条音频。

## 步骤 12：全量生成

实施指令：使用 20000 条文本和 10 段参考音频分批生成全量 clean，再生成 20、10、5、0dB noisy。当前可使用 `run_full_generation.sh` 断点续跑；0dB 可以少量抽样，不必全量生成。

验证：确认输出数量符合预期，metadata 可被下游训练脚本读取。

## 步骤 13：更新进度

实施指令：每完成一个阶段，在 `memory-bank/progress.md` 记录当前状态、已生成数量、失败样本和下一步。

验证：确认 progress 中记录了最近一次生成结果。
