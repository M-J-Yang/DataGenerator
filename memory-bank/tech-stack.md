# 最简技术栈

## 目标

本项目只为生成训练音频，不做 Python package、不做 CLI 框架、不做 Web UI、不做数据库。

## 推荐技术栈

| 用途 | 技术 |
| --- | --- |
| 运行语言 | Python 3.10 |
| TTS 推理代码 | CosyVoice GitHub 仓库 |
| TTS 模型 | Fun-CosyVoice3-0.5B-2512 |
| 模型下载 | modelscope |
| 表格读取 | pandas |
| 音频读写 | soundfile |
| 音频增强 | numpy、scipy、librosa |
| 进度显示 | tqdm |

## 外部资源

CosyVoice 代码：

```text
https://github.com/FunAudioLLM/CosyVoice
```

ModelScope 模型：

```text
FunAudioLLM/Fun-CosyVoice3-0.5B-2512
```

本地建议路径：

```text
CosyVoice/
pretrained_models/Fun-CosyVoice3-0.5B-2512/
```

## 推荐文件

```text
generate_tts.py
augment_audio.py
cleaned_transcripts.csv
refs/
noise/
outputs/clean/
outputs/noisy/
outputs/metadata.csv
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

## 环境建议

使用 Linux/AutoDL，优先 16GB 以上显存。推荐 24GB 显存 GPU，例如 RTX 4090、RTX 3090、A10、A5000。

安装依赖时先按 CosyVoice 官方 requirements 处理，再补充：

```text
modelscope
pandas
soundfile
librosa
scipy
tqdm
```

## 实施原则

先跑通一条，再跑通十条，最后全量生成。所有大文件、模型权重、生成音频默认不提交到 git。
