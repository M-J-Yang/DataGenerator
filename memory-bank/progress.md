# Progress

- 已将方案调整为最简脚本式数据生成流程。
- 2026-06-03：已完成实施计划第 1 步，确认 `refs/`、`noise/`、`outputs/clean/`、`outputs/noisy/`、`pretrained_models/` 目录存在。
- 2026-06-03：已完成实施计划第 2 步，`CosyVoice/` 远端为 `https://github.com/FunAudioLLM/CosyVoice.git`，并已初始化 `third_party/Matcha-TTS` 子模块。
- 2026-06-03：已重新运行 ModelScope 下载并完成实施计划第 3 步，`pretrained_models/Fun-CosyVoice3-0.5B-2512/` 中已存在 `llm.pt`、`llm.rl.pt`、`flow.pt`、`hift.pt`、`cosyvoice3.yaml` 等关键文件；模型目录约 9.1G。
- 2026-06-03：已完成实施计划第 4 步，根据 `fulltext.txt` 生成并扩充 `cleaned_transcripts.csv` 到 20000 条，保留对话字段 `dialogue_id`、`turn_index`、`speaker_role`，共 2880 段对话。
- 2026-06-03：已运行 `python validate_input_csv.py`，确认 `cleaned_transcripts.csv` 包含 20000 条有效记录，`key` 无重复，`target` 无空值。
- 下一步：等待用户验证第 4 步输入表；验证通过后执行第 5 步“准备参考说话人”。
- 2026-06-03：曾根据用户决定更新第 5 步参考说话人方案为 12 段参考音频，即 6 个说话人，每人普通话版本和轻微口音/方言版本各 1 段。
- 2026-06-04：用户已将 5 个说话人的普通话和方言版本放到根目录，第 5 步参考说话人方案调整为 10 段参考音频；`validate_refs.py` 已同步要求 `refs/` 下存在 10 个 wav。
- 2026-06-04：已完成第 5 步“准备参考说话人”：根目录 10 段音频已转码并整理到 `refs/`，命名为 `spk001_standard.wav` 至 `spk005_light_accent.wav`；已运行 `python validate_refs.py`，确认 10 个 wav 全部可读，时长 14.52-18.62 秒，采样率 24000 Hz，单声道。
- 下一步：等待用户验证第 5 步参考音频；用户验证通过前不要开始第 6 步“准备噪声素材”。
