# 航空指令 TTS 数据生成系统技术栈推荐

## 1. 技术栈原则

本项目是离线批量数据生成工具，不是在线服务。技术栈应优先满足：

- 简单：依赖少，安装和排查成本低
- 健壮：支持断点续跑、失败重试、质量检查
- 可维护：模块边界清晰，便于后续替换 TTS 模型
- 适合 GPU 批处理：能在 AutoDL/Linux 服务器稳定运行
- 数据友好：方便处理 CSV、wav、metadata 和报告

不建议第一版引入 Web UI、数据库、消息队列、容器编排或复杂工作流系统。

## 2. 推荐结论

第一版推荐技术栈：

| 层级 | 推荐技术 | 说明 |
| --- | --- | --- |
| 语言 | Python 3.10 | 与 CosyVoice、PyTorch、音频库兼容性较稳 |
| 包管理 | Conda + pip | Conda 管 Python/CUDA 基础环境，pip 装项目依赖 |
| 项目结构 | Python package | 使用 `atc_tts_generator/` 模块化组织代码 |
| CLI | Typer | 简洁、类型友好，比 argparse 更易维护 |
| 配置 | PyYAML + Pydantic | YAML 管参数，Pydantic 做配置校验 |
| TTS 后端 | CosyVoice-300M-SFT | 第一版默认模型，后续预留替换接口 |
| 深度学习 | PyTorch + torchaudio | CosyVoice 依赖基础，兼顾音频 IO |
| 表格处理 | pandas | 处理 transcript、speakers、metadata |
| 音频 IO | soundfile + torchaudio | soundfile 写 wav 稳定，torchaudio 适合张量处理 |
| 音频处理 | scipy + librosa | 带通滤波、重采样、时长和能量分析 |
| 噪声增强 | 自实现核心逻辑，少量使用 numpy/scipy | SNR 混合逻辑可控，避免过度依赖黑盒增强库 |
| 进度条 | tqdm | 批量生成进度展示 |
| 日志 | loguru | 简洁好用，适合 CLI 批处理日志 |
| 测试 | pytest | 单元测试文本规范化、配置校验、metadata、质检 |
| 代码质量 | ruff | 轻量、快速，覆盖 lint 和格式化 |

## 3. 运行环境

### 3.1 操作系统

推荐：

```text
Ubuntu 20.04 / Ubuntu 22.04
```

不建议第一版支持 Windows 原生环境。Windows 用户可通过 WSL2 或 Linux 服务器运行。

### 3.2 Python 版本

推荐：

```text
Python 3.10
```

原因：

- CosyVoice 相关依赖兼容性较好
- PyTorch、torchaudio、librosa、pandas 支持稳定
- 避免 Python 3.12 带来的旧依赖兼容问题

### 3.3 GPU 与 CUDA

推荐硬件：

```text
RTX 4090 24GB
```

可接受硬件：

```text
RTX 3090 24GB
A10 24GB
A5000 24GB
```

测试硬件：

```text
RTX 3060 12GB
RTX 4060 Ti 16GB
```

CUDA 版本应跟随 PyTorch 和 CosyVoice 环境要求选择，不在项目代码中强绑定。

## 4. 包管理与安装方式

### 4.1 推荐方式

使用 Conda 创建基础环境：

```bash
conda create -n atc-tts python=3.10 -y
conda activate atc-tts
```

再用 pip 安装项目依赖：

```bash
pip install -e .
```

### 4.2 依赖文件

建议项目提供：

```text
pyproject.toml
requirements.txt
requirements-dev.txt
```

职责划分：

| 文件 | 用途 |
| --- | --- |
| pyproject.toml | Python package、CLI entry point、工具配置 |
| requirements.txt | 运行依赖 |
| requirements-dev.txt | 测试和开发依赖 |

CosyVoice 可以作为外部目录或可配置路径接入，不建议第一版直接把 CosyVoice 源码合入本项目。

## 5. 项目结构

推荐结构：

```text
DataGenerator/
├── atc_tts_generator/
│   ├── __init__.py
│   ├── cli.py
│   ├── config.py
│   ├── dataset.py
│   ├── normalizer.py
│   ├── cosyvoice_client.py
│   ├── generator.py
│   ├── augmentation.py
│   ├── radio_effects.py
│   ├── metadata.py
│   ├── quality.py
│   └── utils.py
├── configs/
│   └── generation.yaml
├── tests/
│   ├── test_normalizer.py
│   ├── test_config.py
│   ├── test_metadata.py
│   └── test_quality.py
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── AGENTS.md
└── memory-bank/
    ├── architecture.md
    ├── design-document.md
    ├── implementation-plan.md
    ├── progress.md
    └── tech-stack.md
```

## 6. CLI 技术选型

推荐使用 Typer。

原因：

- 代码比 argparse 更清晰
- 支持类型提示
- 自动生成 help 信息
- 对多子命令友好
- 依赖较轻，不引入复杂框架

建议命令：

```bash
atc-tts generate --config configs/generation.yaml --stage all
atc-tts validate --config configs/generation.yaml
atc-tts inspect --metadata atc_tts_dataset/metadata.csv
```

`pyproject.toml` 中注册入口：

```toml
[project.scripts]
atc-tts = "atc_tts_generator.cli:app"
```

## 7. 配置技术选型

推荐：

```text
PyYAML + Pydantic
```

分工：

| 技术 | 职责 |
| --- | --- |
| PyYAML | 读取 `configs/generation.yaml` |
| Pydantic | 校验字段、默认值、路径、枚举、数值范围 |

配置校验应覆盖：

- 输入 CSV 是否存在
- `text_column` 是否为 `target`
- speakers.csv 字段是否完整
- SNR 是否为合法数字
- 0dB 样本数量是否为正数
- 音频时长阈值是否合法
- 噪声类型是否在允许列表中

## 8. TTS 后端技术选型

### 8.1 默认模型

推荐：

```text
CosyVoice-300M-SFT
```

第一版原因：

- 相比更新模型，环境复杂度更低
- 适合先跑通批量生成流程
- 支持参考音频控制音色
- 与当前设计目标匹配

### 8.2 接入方式

建议封装为 `CosyVoiceClient`：

```python
class CosyVoiceClient:
    def synthesize(
        self,
        text: str,
        ref_wav: str,
        ref_text: str,
        output_path: str,
    ) -> None:
        ...
```

业务层不要直接调用 CosyVoice 原始 API，避免后续切换 CosyVoice2、CosyVoice3 或其他 TTS 模型时牵动全局代码。

### 8.3 不推荐方案

第一版不推荐：

- 同时支持多个 TTS 后端
- 使用 Web API 形式调用 TTS
- 直接做模型微调
- 引入 vLLM 推理优化

这些会增加环境复杂度，不利于先稳定生成数据。

## 9. 音频处理技术选型

### 9.1 音频 IO

推荐组合：

```text
soundfile + torchaudio
```

使用建议：

- `soundfile`：稳定读写 wav，适合保存生成结果
- `torchaudio`：和 PyTorch 张量流衔接，适合模型输出处理

### 9.2 重采样

推荐：

```text
torchaudio.transforms.Resample
```

原因：

- 与 PyTorch 张量兼容
- 避免在主流程中频繁转换数据类型

### 9.3 带通滤波

推荐：

```text
scipy.signal
```

用于实现 300-3400Hz 无线电带通滤波。

### 9.4 时长、能量、静音检测

推荐：

```text
librosa + numpy
```

用于：

- 计算音频时长
- RMS 能量
- 静音比例
- 简单异常检测

## 10. 噪声增强技术选型

推荐第一版自实现 SNR 混合逻辑。

原因：

- SNR 计算需要可解释、可复现
- metadata 需要记录 `snr`、`noise_type`、`seed`
- 本项目增强项较明确，不需要完整增强框架
- 避免 audiomentations 版本差异带来的不确定性

核心依赖：

```text
numpy
scipy
soundfile
torchaudio
```

建议实现能力：

- 按 SNR 混合噪声
- 噪声不足时循环拼接
- 随机截取噪声片段
- 控制 0dB 样本数量
- 固定 seed 保证可复现

`audiomentations` 可作为后续可选扩展，不建议作为第一版核心依赖。

## 11. 数据与 Metadata 技术选型

推荐：

```text
pandas + CSV
```

原因：

- 输入本身是 CSV
- 下游 ASR 训练读取方便
- 人工检查方便
- 不需要数据库

metadata 写入策略：

- 每生成一条样本就追加或定期 flush
- 每条样本独立记录 `status`
- 失败样本也写 metadata
- 程序启动时读取已有 metadata 用于断点续跑

第一版不推荐 SQLite。当前样本规模约 2.5 万条，CSV 足够简单可靠。

## 12. 日志与报告

### 12.1 日志

推荐：

```text
loguru
```

输出位置：

```text
atc_tts_dataset/logs/generation.log
```

建议日志内容：

- 配置摘要
- 模型加载状态
- 当前生成进度
- TTS 失败信息
- 音频增强失败信息
- 质量检查异常

### 12.2 报告

推荐格式：

```text
quality_report.csv
generation_summary.json
```

`quality_report.csv` 方便定位单条异常样本；`generation_summary.json` 方便快速查看统计。

## 13. 测试技术选型

推荐：

```text
pytest
```

第一版重点测试：

- 数字读法规范化
- YAML 配置校验
- speakers.csv 字段校验
- metadata 字段生成
- SNR 混合计算
- 静音检测
- 断点续跑判断

不建议第一版对真实 CosyVoice 推理做自动化单元测试。TTS 推理属于 GPU 集成测试，可通过小样本 smoke test 单独执行。

## 14. 代码质量

推荐：

```text
ruff
```

用途：

- lint
- import 排序
- 基础格式化

不建议第一版同时引入 black、isort、flake8、pylint 多套工具。`ruff` 一套足够。

## 15. 推荐依赖清单

### 15.1 运行依赖

```text
typer
pydantic
PyYAML
pandas
numpy
tqdm
loguru
soundfile
librosa
scipy
torch
torchaudio
```

CosyVoice 及其 requirements 按 CosyVoice 官方项目单独安装。

### 15.2 开发依赖

```text
pytest
ruff
```

## 16. 不推荐引入的技术

第一版不推荐：

| 技术 | 不推荐原因 |
| --- | --- |
| FastAPI / Flask | 当前不是在线服务，无需 Web API |
| Streamlit / Gradio | 会分散重点，第一版应优先稳定批处理 |
| Celery / Redis | 当前任务可本地顺序执行，不需要分布式队列 |
| SQLite / PostgreSQL | 2.5 万条 metadata 用 CSV 足够 |
| Airflow / Prefect | 工作流复杂度高于当前需求 |
| Docker Compose | GPU/CUDA/TTS 环境调试成本高，第一版可先不用 |
| audiomentations | 可后续扩展，第一版自实现 SNR 更可控 |
| vLLM | CosyVoice-300M-SFT 第一版不需要推理优化复杂度 |

## 17. 最小可行技术栈

如果希望最快开始实现，最小栈为：

```text
Python 3.10
Typer
PyYAML
Pydantic
pandas
numpy
soundfile
torchaudio
scipy
tqdm
loguru
pytest
ruff
CosyVoice-300M-SFT
```

该组合已经足够覆盖：

- CLI
- 配置管理
- CSV 和 metadata
- TTS 封装
- 音频读写
- SNR 噪声混合
- 无线电滤波
- 质量检查
- 单元测试
- 断点续跑

## 18. 推荐实施顺序

建议按以下顺序落地：

1. 搭建 Python package、CLI、配置读取
2. 实现 CSV 和 speakers.csv 校验
3. 实现数字规范化与单元测试
4. 封装 CosyVoiceClient，并跑通 1 条 clean 样本
5. 实现 clean 批量生成和 metadata
6. 实现 SNR 噪声混合
7. 实现无线电效果
8. 实现 0dB 极难样本采样
9. 实现质量检查和报告
10. 执行 825 × 6 × 4 的正式生成

