# 最简技术栈

## 目标

本项目只为生成训练音频，不做 Python package、不做 CLI 框架、不做 Web UI、不做数据库。

## 当前实际环境

| 项目 | 当前值 |
| --- | --- |
| 运行环境 | Linux/AutoDL |
| Python | 3.12.13 |
| GPU | NVIDIA GeForce RTX 5090 |
| PyTorch | 2.8.0+cu128 |
| CUDA | 可用 |
| ONNXRuntime | onnxruntime-gpu 1.26.0，`get_device()` 为 `GPU` |
| TTS 推理代码 | `CosyVoice/` |
| TTS 模型 | `Fun-CosyVoice3-0.5B-2512` |

## 核心依赖

| 用途 | 技术 |
| --- | --- |
| TTS 推理 | CosyVoice GitHub 仓库 |
| TTS 模型 | FunAudioLLM/Fun-CosyVoice3-0.5B-2512 |
| 模型下载 | modelscope |
| 张量/GPU | torch |
| ONNX 推理 | onnxruntime-gpu |
| 音频增强 | numpy、scipy |
| wav 读写 | Python `wave` 标准库 |
| CSV 读写 | Python `csv` 标准库 |

## 已知依赖处理

当前为了避免 Transformers 进入 sklearn 导入链导致 SciPy/Numpy 兼容问题，已卸载可选依赖 `scikit-learn`。

当前确认可用组合：

```text
numpy 2.1.3
scipy 1.14.1
pyworld 0.3.4 rebuilt for NumPy 2 ABI
torch 2.8.0+cu128
onnxruntime-gpu 1.26.0
```

注意：`librosa` 可能提示缺少 `scikit-learn`，但当前 `generate_tts.py` 和 `augment_audio.py` 不依赖 librosa 的 sklearn 路径。若后续新增 librosa 相关功能，需要重新评估依赖组合。

## 外部资源

CosyVoice 代码：

```text
https://github.com/FunAudioLLM/CosyVoice
```

ModelScope 模型：

```text
FunAudioLLM/Fun-CosyVoice3-0.5B-2512
```

本地路径：

```text
CosyVoice/
pretrained_models/Fun-CosyVoice3-0.5B-2512/
```

## 推荐文件

```text
generate_tts.py
augment_audio.py
run_standard_dialect_generation.sh
cleaned_transcripts.csv
refs/
noise/
outputs/clean/
outputs/noisy/
outputs/metadata.csv
```

## 当前推荐命令

生成普通话参考 + 四方言 clean 听测样本：

```bash
START=1463 LIMIT=1 CLEAN_DIR=outputs/standard_dialect_test METADATA=outputs/standard_dialect_test_metadata.csv SKIP_AUGMENT=1 ./run_standard_dialect_generation.sh
```

全量断点续跑 clean/noisy：

```bash
./run_standard_dialect_generation.sh
```

仅验证 TTS 计划：

```bash
python generate_tts.py --dry-run --start 1463 --limit 1   --ref spk001_standard --mode auto --dialect 甘肃话
```

## 不需要的东西

第一版不要引入：

- Typer CLI
- Pydantic 配置系统
- pytest 测试框架
- Python package 结构
- 数据库
- Docker
- Web UI
- 复杂任务队列

## 实施原则

先跑通一条，再跑通小批量听测，最后全量生成。所有大文件、模型权重、参考音频、噪声素材、生成音频默认不提交到 git。
