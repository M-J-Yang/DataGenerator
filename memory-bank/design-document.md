# 航空指令 TTS 数据生成系统设计文档

## 1. 背景

当前项目需要基于已有航空指令文本，批量生成可用于 ASR/Paraformer 训练的数据集。系统需要支持文本规范化、CosyVoice TTS 推理、说话人音色控制、噪声增强、无线电效果模拟、metadata 生成和自动质量检查。

已有输入文本为 `cleaned_transcripts.csv`，共约 825 条航空指令文本，固定包含以下字段：

```text
key,raw_target,target,source,slot_types,spoken_digit_tags,is_digit_focus
```

第一版默认使用 `target` 字段作为生成入口。TTS 实际输入文本会经过数字读法规范化，输出 metadata 中的标注文本仍保留阿拉伯数字形式，便于后续 ASR 训练和评估。

## 2. 目标

### 2.1 产品目标

构建一个 Python package + CLI 形式的数据生成工具，支持从 CSV 文本批量生成航空指令语音数据，并输出统一 metadata。

系统覆盖以下能力：

- 文本读取与校验
- 航空数字读法规范化
- 基于 CosyVoice-300M-SFT 的 TTS 生成
- 6 个参考说话人音色生成
- clean/noisy 两类样本生成
- 环境噪声增强
- 无线电效果模拟
- metadata 统一管理
- 自动质量检查
- 断点续跑与失败重试

### 2.2 非目标

第一版不覆盖以下内容：

- ASR/Paraformer 模型训练
- ASR 评估指标计算
- Web UI
- 自动下载大规模噪声库
- 参考说话人音频自动采集
- CosyVoice 模型微调

## 3. 总体方案

### 3.1 产品形态

系统采用 Python package + CLI：

```bash
python -m atc_tts_generator generate --config configs/generation.yaml
python -m atc_tts_generator validate --config configs/generation.yaml
python -m atc_tts_generator inspect --metadata atc_tts_dataset/metadata.csv
```

CLI 只负责指定配置、运行阶段和少量覆盖参数；主要参数由 YAML 配置文件管理。

### 3.2 默认规模

正式增强目标规模：

```text
825 条文本 × 6 个说话人 × 4 个常规 SNR 档位 = 19,800 条 noisy 样本
```

同时生成对应 clean 样本：

```text
825 条文本 × 6 个说话人 = 4,950 条 clean 样本
```

额外生成少量极难样本：

```text
约 100 条 0dB noisy 样本
```

最终总量约：

```text
4,950 clean + 19,800 noisy + 100 hard noisy = 24,850 条
```

## 4. 用户与使用场景

### 4.1 主要用户

- 数据工程人员：负责生成和管理航空指令增强数据集
- ASR 训练人员：使用输出 wav 和 metadata 训练识别模型
- 研究人员：调整噪声、说话人、数字读法以对比鲁棒性效果

### 4.2 核心场景

1. 数据工程人员准备 `cleaned_transcripts.csv`、`speakers.csv` 和噪声目录。
2. 运行 CLI 生成 clean 音频。
3. 基于 clean 音频生成 noisy 音频和无线电效果版本。
4. 系统输出统一 `metadata.csv`。
5. 运行质量检查，发现失败样本、静音样本、过短样本或 metadata 不一致问题。
6. 下游 ASR 训练脚本按 metadata 读取数据。

## 5. 输入规范

### 5.1 文本 CSV

路径由配置指定，默认：

```text
atc_tts_dataset/input/cleaned_transcripts.csv
```

必需字段：

```csv
key,raw_target,target,source,slot_types,spoken_digit_tags,is_digit_focus
```

字段说明：

| 字段 | 说明 |
| --- | --- |
| key | 原始语料唯一 ID |
| raw_target | 原始口语文本 |
| target | 清洗后的标准文本，第一版默认使用 |
| source | 文本来源 |
| slot_types | 槽位类型信息 |
| spoken_digit_tags | 数字相关标签 |
| is_digit_focus | 是否数字重点样本 |

### 5.2 说话人 CSV

路径由配置指定，默认：

```text
atc_tts_dataset/refs/speakers.csv
```

必需字段：

```csv
speaker_id,ref_wav,ref_text,gender,accent,role,speed_style
```

字段说明：

| 字段 | 说明 |
| --- | --- |
| speaker_id | 说话人唯一 ID，例如 `spk001` |
| ref_wav | 参考音频路径 |
| ref_text | 参考音频对应文本 |
| gender | 性别，例如 `male`、`female` |
| accent | 口音，例如 `standard`、`north`、`south` |
| role | 角色，例如 `controller`、`pilot` |
| speed_style | 语速风格，例如 `normal`、`fast`、`slow` |

第一版要求准备 6 个参考说话人，建议覆盖：

| speaker_id | gender | accent | role | speed_style |
| --- | --- | --- | --- | --- |
| spk001 | male | standard | controller | normal |
| spk002 | female | standard | controller | normal |
| spk003 | male | north | pilot | normal |
| spk004 | female | south | pilot | normal |
| spk005 | male | standard | controller | fast |
| spk006 | female | standard | pilot | slow |

### 5.3 噪声目录

默认目录：

```text
atc_tts_dataset/noise/
├── airport/
├── radio/
├── cockpit/
├── white_noise/
├── crowd/
└── wind/
```

噪声类型通过配置启用或禁用。第一版至少支持：

- `airport`
- `radio`
- `cockpit`
- `white_noise`
- `crowd`
- `wind`

## 6. 文本规范化设计

### 6.1 设计原则

航空通话中数字读法与普通中文读法不同。为确保 TTS 输出符合业务场景，系统在 TTS 前对输入文本做规范化。

关键原则：

- TTS 输入文本可以改写成中文读法。
- 输出 metadata 中的 `text` 保留原始阿拉伯数字标注。
- 不同槽位使用不同数字读法规则。
- 无法识别槽位时使用保守默认规则，并记录 warning。

### 6.2 数字读法

特殊数字读法：

| 数字 | TTS 读法 |
| --- | --- |
| 0 | 洞 |
| 1 | 幺 |
| 2 | 两 |
| 7 | 拐 |
| 3 | 三 |
| 4 | 四 |
| 5 | 五 |
| 6 | 六 |
| 8 | 八 |
| 9 | 九 |

### 6.3 按槽位处理

| 类型 | 规则 | 示例 |
| --- | --- | --- |
| 呼号 | 逐位读 | `4151` -> `四幺五幺` |
| 频率 | 整数和小数逐位读，点保留为“点” | `733.9` -> `拐三三点九` |
| 高度 | 数值读 | `2800` -> `两千八百` |
| 气压 | 数值读 | `1013` -> `一千零一十三` 或按配置改写 |
| 编号 | 默认逐位读或按配置处理 | `7号` -> `拐号` |

高度和气压采用数值读法，但由于普通中文中的“二/两”“零/洞”存在业务差异，需要在配置中保留覆盖项。

### 6.4 标注与 TTS 文本分离

metadata 中至少保留两类文本：

| 字段 | 说明 |
| --- | --- |
| text | 下游 ASR 使用的标注文本，保留阿拉伯数字 |
| tts_text | 实际送入 TTS 的中文读法文本 |

示例：

```csv
text,tts_text
锦州回答4151声音好,锦州回答四幺五幺声音好
保持高度2800,保持高度两千八百
频率733.9,频率拐三三点九
```

## 7. 生成流水线

### 7.1 流程概览

```text
读取配置
  ↓
校验输入 CSV、说话人 CSV、噪声目录
  ↓
读取 target 文本
  ↓
文本规范化，生成 tts_text
  ↓
遍历文本 × 说话人，生成 clean wav
  ↓
基于 clean wav 生成 noisy wav
  ↓
应用可选无线电效果
  ↓
写入 metadata.csv
  ↓
执行质量检查
  ↓
输出报告
```

### 7.2 clean 生成

clean 样本由 CosyVoice-300M-SFT 直接生成：

```text
input: tts_text + ref_wav + ref_text
output: wav_clean/{utt_id}.wav
```

命名规则：

```text
{key}_{speaker_id}_clean.wav
```

示例：

```text
ch01_01_001_spk001_clean.wav
```

### 7.3 noisy 生成

noisy 样本基于 clean wav 后处理生成，不直接要求 TTS 生成带噪声语音。

常规 SNR 档位：

```text
20dB, 15dB, 10dB, 5dB
```

极难样本：

```text
0dB，约 100 条
```

命名规则：

```text
{key}_{speaker_id}_snr{snr}_{noise_type}_r{radio_effect}.wav
```

示例：

```text
ch01_01_001_spk001_snr10_radio_r1.wav
```

## 8. 噪声与无线电效果设计

### 8.1 增强项拆分

所有增强项均通过配置控制：

| 增强项 | 默认 | 说明 |
| --- | --- | --- |
| mix_noise | true | 是否混入环境噪声 |
| radio_bandpass | true | 是否应用 300-3400Hz 带通滤波 |
| resample_8k | true | 是否重采样到 8kHz |
| clipping | true | 是否加入轻微削波 |
| dropout | true | 是否加入短暂静音/dropout |
| background_hiss | true | 是否加入无线电底噪 |

### 8.2 样本难度分级

| 等级 | SNR | 推荐占比 | 用途 |
| --- | --- | --- | --- |
| clean | 无 | clean 全量 | 基础清晰语音训练 |
| easy | 20dB | 常规增强 | 轻微背景噪声 |
| medium | 15dB | 常规增强 | 常见噪声场景 |
| hard | 10dB | 常规增强 | 明显噪声场景 |
| very_hard | 5dB | 常规增强 | 强噪声鲁棒性 |
| extreme | 0dB | 约 100 条 | 极难样本，仅少量加入 |

0dB 样本不参与常规全量笛卡尔积生成，避免极难样本比例过高影响模型学习。生成方式为从文本、说话人和噪声类型组合中随机采样约 100 条。

### 8.3 无线电效果建议参数

| 参数 | 默认值 |
| --- | --- |
| sample_rate | 8000 |
| bandpass_low_hz | 300 |
| bandpass_high_hz | 3400 |
| clipping_probability | 0.3 |
| dropout_probability | 0.2 |
| dropout_min_ms | 20 |
| dropout_max_ms | 120 |

## 9. 输出目录与文件

默认输出结构：

```text
atc_tts_dataset/
├── input/
│   └── cleaned_transcripts.csv
├── refs/
│   ├── speakers.csv
│   └── *.wav
├── noise/
│   ├── airport/
│   ├── radio/
│   ├── cockpit/
│   ├── white_noise/
│   ├── crowd/
│   └── wind/
├── wav_clean/
├── wav_noisy/
├── metadata.csv
├── reports/
│   ├── quality_report.csv
│   └── generation_summary.json
└── logs/
```

## 10. Metadata 设计

第一版使用一个统一主 metadata 文件：

```text
atc_tts_dataset/metadata.csv
```

建议字段：

```csv
utt_id,key,split,text,tts_text,wav_path,sample_type,difficulty,speaker_id,gender,accent,role,speed_style,snr,noise_type,radio_effect,source,slot_types,spoken_digit_tags,is_digit_focus,model_name,model_version,seed,duration_sec,status,error_message
```

字段说明：

| 字段 | 说明 |
| --- | --- |
| utt_id | 输出样本唯一 ID |
| key | 原始文本 ID |
| split | 数据划分，例如 `train`、`dev`、`test`，第一版可为空或默认 `train` |
| text | ASR 标注文本，保留阿拉伯数字 |
| tts_text | 实际 TTS 输入文本 |
| wav_path | wav 相对路径 |
| sample_type | `clean` 或 `noisy` |
| difficulty | `clean/easy/medium/hard/very_hard/extreme` |
| speaker_id | 说话人 ID |
| gender | 性别 |
| accent | 口音 |
| role | 角色 |
| speed_style | 语速风格 |
| snr | 噪声信噪比，clean 为空 |
| noise_type | 噪声类型，clean 为空 |
| radio_effect | 是否应用无线电效果 |
| source | 原始 source 字段 |
| slot_types | 原始 slot_types 字段 |
| spoken_digit_tags | 原始 spoken_digit_tags 字段 |
| is_digit_focus | 原始 is_digit_focus 字段 |
| model_name | 默认 `CosyVoice-300M-SFT` |
| model_version | 模型版本或模型路径 hash |
| seed | 随机种子 |
| duration_sec | 音频时长 |
| status | `success` 或 `failed` |
| error_message | 失败信息 |

## 11. 配置文件设计

默认配置文件：

```text
configs/generation.yaml
```

示例：

```yaml
project:
  output_dir: atc_tts_dataset
  seed: 20260602

input:
  transcript_csv: atc_tts_dataset/input/cleaned_transcripts.csv
  text_column: target
  speakers_csv: atc_tts_dataset/refs/speakers.csv

model:
  name: CosyVoice-300M-SFT
  model_path: models/CosyVoice-300M-SFT
  device: cuda

generation:
  speakers: 6
  retry_times: 3
  skip_existing: true
  batch_size: 1

normalization:
  digit_map:
    "0": 洞
    "1": 幺
    "2": 两
    "3": 三
    "4": 四
    "5": 五
    "6": 六
    "7": 拐
    "8": 八
    "9": 九
  slot_rules:
    callsign: digit_by_digit
    frequency: digit_by_digit
    altitude: numeric
    pressure: numeric
    number_id: digit_by_digit

augmentation:
  enabled: true
  snr_levels: [20, 15, 10, 5]
  extreme_snr:
    enabled: true
    snr: 0
    count: 100
  noise_types:
    - airport
    - radio
    - cockpit
    - white_noise
    - crowd
    - wind
  effects:
    mix_noise: true
    radio_bandpass: true
    resample_8k: true
    clipping: true
    dropout: true
    background_hiss: true

radio:
  sample_rate: 8000
  bandpass_low_hz: 300
  bandpass_high_hz: 3400
  clipping_probability: 0.3
  dropout_probability: 0.2
  dropout_min_ms: 20
  dropout_max_ms: 120

quality:
  min_duration_sec: 0.3
  max_duration_sec: 30.0
  check_silence: true
  check_sample_rate: true
  expected_sample_rate_clean: 24000
  expected_sample_rate_noisy: 8000
```

## 12. CLI 设计

### 12.1 generate

生成 clean 和 noisy 样本：

```bash
python -m atc_tts_generator generate --config configs/generation.yaml
```

可选阶段：

```bash
python -m atc_tts_generator generate --config configs/generation.yaml --stage clean
python -m atc_tts_generator generate --config configs/generation.yaml --stage noisy
python -m atc_tts_generator generate --config configs/generation.yaml --stage all
```

### 12.2 validate

执行质量检查：

```bash
python -m atc_tts_generator validate --config configs/generation.yaml
```

### 12.3 inspect

查看 metadata 统计：

```bash
python -m atc_tts_generator inspect --metadata atc_tts_dataset/metadata.csv
```

输出统计包括：

- 总样本数
- clean/noisy 数量
- 各 SNR 档位数量
- 各说话人数量
- 各噪声类型数量
- 失败样本数量
- 平均时长

## 13. 模块设计

建议包结构：

```text
atc_tts_generator/
├── __init__.py
├── cli.py
├── config.py
├── dataset.py
├── normalizer.py
├── cosyvoice_client.py
├── generator.py
├── augmentation.py
├── radio_effects.py
├── metadata.py
├── quality.py
└── utils.py
```

模块职责：

| 模块 | 职责 |
| --- | --- |
| cli.py | CLI 参数解析与命令入口 |
| config.py | YAML 配置读取和校验 |
| dataset.py | 文本 CSV、speakers.csv、噪声目录读取 |
| normalizer.py | 航空文本和数字读法规范化 |
| cosyvoice_client.py | CosyVoice 推理封装 |
| generator.py | clean/noisy 主生成流程 |
| augmentation.py | 噪声混合和 SNR 控制 |
| radio_effects.py | 8kHz、带通、clipping、dropout 等效果 |
| metadata.py | metadata 记录、更新、断点续跑 |
| quality.py | 音频与 metadata 质量检查 |
| utils.py | 路径、日志、随机种子等工具函数 |

## 14. 断点续跑与错误处理

### 14.1 断点续跑

系统通过 `metadata.csv` 和 wav 文件存在性判断是否跳过已生成样本。

当 `skip_existing: true` 时：

- wav 文件存在
- metadata 中存在对应 `utt_id`
- status 为 `success`

满足以上条件则跳过。

### 14.2 失败重试

TTS 或增强失败时最多重试 `retry_times` 次。仍失败则写入 metadata：

```text
status=failed
error_message=<具体错误>
```

失败样本不阻塞整体任务，但会在最终报告中统计。

## 15. 质量检查

### 15.1 检查项

| 检查项 | 说明 |
| --- | --- |
| 文件存在 | metadata 中每条成功样本的 wav 必须存在 |
| 时长范围 | 音频时长必须在配置范围内 |
| 静音检测 | 过滤全静音或近似静音样本 |
| 采样率 | clean/noisy 采样率符合配置 |
| metadata 一致性 | wav 数量与 metadata 成功行一致 |
| 说话人覆盖 | 每个说话人生成数量符合预期 |
| SNR 覆盖 | 常规 SNR 和 0dB 极难样本数量符合预期 |
| 文本为空 | `text` 和 `tts_text` 不允许为空 |

### 15.2 质量报告

输出：

```text
atc_tts_dataset/reports/quality_report.csv
atc_tts_dataset/reports/generation_summary.json
```

`quality_report.csv` 记录每条异常样本；`generation_summary.json` 记录总体统计。

## 16. 验收标准

第一版验收标准：

- 能读取固定字段的 `cleaned_transcripts.csv`
- 能读取 6 个说话人的 `speakers.csv`
- 默认使用 `target` 字段生成
- 能将呼号、频率按逐位规则改写为 TTS 文本
- 能将高度、气压按数值规则改写为 TTS 文本
- 能使用 CosyVoice-300M-SFT 生成 clean wav
- 能基于 clean wav 生成 20/15/10/5dB noisy wav
- 能额外生成约 100 条 0dB 极难样本
- 能输出单一 `metadata.csv`
- metadata 同时包含 `text` 和 `tts_text`
- metadata 能区分 clean/noisy、difficulty、speaker、role、accent、SNR 和 noise type
- 能执行质量检查并输出报告
- 支持 `skip_existing` 断点续跑
- 失败样本有状态和错误信息记录

## 17. 风险与应对

| 风险 | 影响 | 应对 |
| --- | --- | --- |
| CosyVoice 对航空数字读法不稳定 | 数字识别训练数据错误 | 在 TTS 前显式中文化数字读法 |
| 参考音频质量差 | 生成音色不稳定 | speakers.csv 中维护 ref_text，质检参考 wav |
| 口音不可控 | 口音增强效果有限 | 主要依赖真实口音参考音频，不依赖 prompt |
| 0dB 样本过多 | 影响 ASR 学习 | 限制约 100 条，并标记为 `extreme` |
| metadata 与 wav 不一致 | 下游训练失败 | 质量检查强制校验 |
| 批量生成中断 | 浪费已生成结果 | metadata + skip_existing 断点续跑 |
| 噪声素材许可不清晰 | 数据集分发受限 | 记录噪声来源，优先使用许可明确数据 |

## 18. 后续扩展

后续可扩展能力：

- 支持 `raw_target` 口语版生成
- 支持 CosyVoice2 / CosyVoice3
- 支持更多说话人和口音配置
- 支持 dev/test split 策略
- 支持人工抽检界面
- 支持 ASR 训练数据 manifest 输出
- 支持 CER/WER 评估闭环
- 支持按 slot 类型控制样本生成比例

