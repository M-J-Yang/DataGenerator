# 实施计划

本文档面向 AI 开发者，基于 `memory-bank/design-document.md` 和 `memory-bank/tech-stack.md` 拆解实现步骤。每一步都必须小而具体，并在完成后执行对应验证。严禁在实施过程中跳过测试。

## 总体要求

- 技术栈使用 Python 3.10、Typer、PyYAML、Pydantic、pandas、numpy、soundfile、torchaudio、scipy、librosa、tqdm、loguru、pytest、ruff。
- 项目形态为 Python package + CLI。
- 第一版只覆盖数据生成，不实现 ASR 训练、不实现 Web UI、不引入数据库或任务队列。
- CosyVoice 作为外部 TTS 后端接入，不把 CosyVoice 源码合入本仓库。
- 每一步完成后必须运行对应测试；测试失败不得进入下一步。

## 步骤 1：建立基础项目骨架

实施指令：创建 `atc_tts_generator/`、`configs/`、`tests/` 目录，以及基础包文件。创建 `pyproject.toml`、`requirements.txt`、`requirements-dev.txt`，注册 `atc-tts` CLI 入口。不要实现业务逻辑，只保证项目可安装、CLI 可被发现。

验证测试：执行本地可编辑安装，确认安装成功。执行 CLI 帮助命令，确认能显示命令入口。执行 ruff 检查，确认没有基础格式问题。

## 步骤 2：实现 CLI 命令框架

实施指令：在 `cli.py` 中建立 `generate`、`validate`、`inspect` 三个子命令。此阶段只接收参数并打印或记录阶段信息，不执行真实生成。

验证测试：新增 CLI 测试，确认三个命令都能被调用，缺少必需参数时返回明确错误。执行 pytest，确认 CLI 测试通过。

## 步骤 3：创建默认配置文件

实施指令：创建 `configs/generation.yaml`，包含项目路径、输入路径、模型配置、生成参数、数字规范化规则、增强参数、无线电参数和质检参数。

验证测试：人工检查配置文件字段是否覆盖 `memory-bank/design-document.md` 的配置项。执行配置读取测试，确认 YAML 能被正常加载。

## 步骤 4：实现配置模型与校验

实施指令：在 `config.py` 中使用 Pydantic 定义配置结构。校验输入字段、SNR 档位、0dB 样本数量、音频时长阈值、噪声类型和布尔增强项。

验证测试：新增 `tests/test_config.py`，覆盖合法配置、缺失字段、非法 SNR、负数极难样本数量、错误时长范围。执行 pytest，确认配置测试通过。

## 步骤 5：实现文本 CSV 读取与字段校验

实施指令：在 `dataset.py` 中实现 `cleaned_transcripts.csv` 读取。固定要求字段为 `key`、`raw_target`、`target`、`source`、`slot_types`、`spoken_digit_tags`、`is_digit_focus`。默认使用 `target` 字段。

验证测试：新增测试数据 fixture，覆盖字段完整、字段缺失、空文本、重复 key。执行 pytest，确认读取和校验行为符合预期。

## 步骤 6：实现说话人 CSV 读取与字段校验

实施指令：在 `dataset.py` 中实现 `speakers.csv` 读取。要求字段为 `speaker_id`、`ref_wav`、`ref_text`、`gender`、`accent`、`role`、`speed_style`，并要求第一版正好或至少提供 6 个说话人。

验证测试：新增 speakers 测试，覆盖字段缺失、说话人数量不足、重复 speaker_id、参考音频路径不存在。执行 pytest，确认校验测试通过。

## 步骤 7：实现噪声目录扫描

实施指令：在 `dataset.py` 中扫描配置启用的噪声类型目录，收集可用 wav 文件。缺少启用目录或目录为空时给出明确错误。

验证测试：新增噪声目录测试，覆盖完整目录、缺失目录、空目录、禁用噪声类型。执行 pytest，确认测试通过。

## 步骤 8：实现基础数字映射

实施指令：在 `normalizer.py` 中实现逐位数字读法映射：0 为洞、1 为幺、2 为两、7 为拐，其余数字为三、四、五、六、八、九。

验证测试：新增 `tests/test_normalizer.py`，验证单个数字和连续数字映射。例如呼号类数字必须逐位转换。执行 pytest，确认规范化测试通过。

## 步骤 9：实现槽位化数字规则

实施指令：扩展 `normalizer.py`，按槽位处理数字。呼号和频率逐位读，高度和气压按数值读。无法识别槽位时使用保守默认规则并记录 warning。

验证测试：测试呼号、频率、高度、气压、未知槽位。确认 metadata 标注文本保留阿拉伯数字，TTS 文本使用中文读法。执行 pytest，确认全部通过。

## 步骤 10：实现 metadata 行生成

实施指令：在 `metadata.py` 中定义统一 metadata 字段，并实现 clean/noisy 样本记录生成。必须包含 `text`、`tts_text`、`sample_type`、`difficulty`、`speaker_id`、`snr`、`noise_type`、`status`。

验证测试：新增 `tests/test_metadata.py`，分别验证 clean、20dB noisy、0dB extreme 样本字段完整性。执行 pytest，确认 metadata 测试通过。

## 步骤 11：实现 metadata 写入与读取

实施指令：实现 `metadata.csv` 写入、读取和追加。失败样本也必须写入，且包含错误信息。避免重复写入相同 `utt_id`。

验证测试：测试追加写入、重复 `utt_id` 处理、失败行记录、重新读取后字段不丢失。执行 pytest，确认通过。

## 步骤 12：实现断点续跑判断

实施指令：在 `metadata.py` 或 `generator.py` 中实现 `skip_existing` 判断。只有 wav 文件存在、metadata 有对应 `utt_id`、状态为 success 时才跳过。

验证测试：覆盖文件存在且成功、文件缺失、metadata 缺失、状态 failed 四种情况。执行 pytest，确认断点续跑测试通过。

## 步骤 13：封装 CosyVoice 客户端接口

实施指令：在 `cosyvoice_client.py` 中封装 TTS 后端接口。业务层只调用统一 synthesize 能力，不直接依赖 CosyVoice 原始 API。此步骤允许使用 mock 后端完成测试。

验证测试：新增 mock TTS 测试，确认传入 `tts_text`、`ref_wav`、`ref_text`、输出路径后能产生预期输出文件或调用记录。执行 pytest，确认不依赖 GPU 的测试通过。

## 步骤 14：实现 clean 样本生成流程

实施指令：在 `generator.py` 中实现文本乘以说话人的 clean 生成流程。生成命名遵循 `{key}_{speaker_id}_clean.wav`，并写入 metadata。

验证测试：使用 mock TTS 和 2 条文本、2 个说话人的测试数据，确认生成 4 条 clean 记录、4 个 wav 路径、metadata 字段正确。执行 pytest，确认通过。

## 步骤 15：实现 SNR 噪声混合

实施指令：在 `augmentation.py` 中实现基于 clean wav 和噪声 wav 的 SNR 混合。支持噪声循环拼接、随机截取、固定 seed 复现。

验证测试：使用合成短音频验证 20、15、10、5dB 目标 SNR 与实际计算误差在可接受范围内。执行 pytest，确认 SNR 测试通过。

## 步骤 16：实现无线电效果

实施指令：在 `radio_effects.py` 中实现可配置无线电效果，包括 8kHz 重采样、300 到 3400Hz 带通滤波、轻微 clipping、短暂 dropout、底噪开关。

验证测试：使用短音频验证输出采样率为 8kHz，时长基本保持，dropout 和 clipping 在启用时产生可检测变化。执行 pytest，确认通过。

## 步骤 17：实现 noisy 常规样本生成

实施指令：在 `generator.py` 中基于 clean 样本生成 20、15、10、5dB noisy 样本。每条 noisy 样本记录 `difficulty`、`snr`、`noise_type`、`radio_effect`。

验证测试：使用小样本数据验证 clean 样本可扩展为完整 SNR 档位的 noisy metadata。确认文件命名包含 `snr`、噪声类型和无线电标记。执行 pytest，确认通过。

## 步骤 18：实现 0dB 极难样本采样

实施指令：实现约 100 条 0dB noisy 样本的独立采样逻辑。0dB 不参与常规全量笛卡尔积，必须标记为 `extreme`。

验证测试：在测试配置中设置较小 extreme 数量，确认只生成指定数量的 0dB 样本，且 difficulty 均为 `extreme`。执行 pytest，确认通过。

## 步骤 19：实现质量检查

实施指令：在 `quality.py` 中实现文件存在、时长范围、静音、采样率、metadata 一致性、说话人覆盖、SNR 覆盖、文本非空检查。

验证测试：构造正常和异常 metadata/wav 样本，确认每类异常都能被识别并写入质量报告。执行 pytest，确认质检测试通过。

## 步骤 20：实现 validate 命令

实施指令：将质量检查接入 CLI 的 `validate` 命令。命令读取配置，检查数据集并输出 `quality_report.csv` 和 `generation_summary.json`。

验证测试：使用临时数据集运行 validate，确认报告文件存在、异常数量正确、命令返回状态符合预期。执行 pytest，确认通过。

## 步骤 21：实现 inspect 命令

实施指令：实现 metadata 统计命令，输出总样本数、clean/noisy 数量、各 SNR 数量、各说话人数量、各噪声类型数量、失败样本数量和平均时长。

验证测试：构造固定 metadata，运行 inspect，确认统计结果与输入数据一致。执行 pytest，确认通过。

## 步骤 22：实现日志与错误处理

实施指令：接入 loguru，记录配置摘要、模型加载、生成进度、失败重试、质检异常。TTS 和增强失败时最多重试配置指定次数，最终失败写入 metadata。

验证测试：使用 mock 后端模拟失败和恢复，确认重试次数、日志记录、metadata 状态和错误信息正确。执行 pytest，确认通过。

## 步骤 23：执行端到端小样本测试

实施指令：准备最小测试数据集，包含 2 条文本、2 个说话人、至少 1 类噪声。使用 mock TTS 或真实 TTS smoke 模式跑通 generate、validate、inspect。

验证测试：确认生成 clean、noisy、metadata、quality report、summary 和日志。确认 pytest 全量通过，ruff 检查通过。

## 步骤 24：执行真实 CosyVoice 单条 smoke test

实施指令：在具备 GPU 和 CosyVoice 环境的机器上，用 1 条文本和 1 个参考说话人生成 1 条 clean wav。此步骤只验证真实 TTS 接入，不做批量生成。

验证测试：确认 wav 文件存在、时长合理、非静音、metadata 状态为 success。运行 validate，确认该样本通过质检。

## 步骤 25：执行正式规模前的试运行

实施指令：使用 10 条文本、6 个说话人、4 个常规 SNR 和少量 0dB 配置试运行。检查生成速度、显存占用、metadata、日志和报告。

验证测试：确认 clean 数量为 60，常规 noisy 数量为 240，0dB 数量等于测试配置指定值。确认 validate 无阻断级异常。

## 步骤 26：执行正式数据生成

实施指令：使用 825 条文本、6 个说话人、20/15/10/5dB 常规 SNR，以及约 100 条 0dB 极难样本执行正式生成。启用 skip_existing。

验证测试：确认 clean 约 4,950 条，常规 noisy 约 19,800 条，0dB extreme 约 100 条，总量约 24,850 条。执行 validate 和 inspect，确认统计与设计目标一致。

## 步骤 27：最终交付检查

实施指令：整理最终目录，确认源码、配置、测试、metadata、报告和日志位置符合设计文档。更新必要 README 或使用说明，但不要改变既定技术栈。

验证测试：执行全量 pytest、ruff 检查、validate、inspect。确认无失败测试，无残留临时文件，无未记录的大文件进入源码目录。

