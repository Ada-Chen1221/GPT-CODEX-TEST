# LLM 批量实验脚手架

这是一个用于论文实验的最小可用脚手架：
- 批量读取 prompt（CSV/JSONL）
- 调用多个大模型 API（GPT / DeepSeek / Qianwen / Llama）
- 保存原始响应与结构化提取结果

## 1. 安装

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. 配置

1) 复制配置：

```bash
cp configs/models.example.json configs/models.json
```

2) 在环境变量里放 API Key（推荐 `.env`）：

```env
OPENAI_API_KEY=...
DEEPSEEK_API_KEY=...
QIANWEN_API_KEY=...
LLAMA_API_KEY=...
```

## 3. 准备输入

默认读取 `data/prompts.csv`，至少包含：
- `id`
- `prompt`

## 4. 运行

```bash
python scripts/run_batch.py \
  --config configs/models.json \
  --input data/prompts.csv \
  --outdir outputs \
  --temperature 0.0 \
  --max-tokens 512
```

## 5. 输出说明

每次运行会在 `outputs/<timestamp>/` 下生成：
- `raw_responses.jsonl`：原始响应（含模型名、耗时、错误信息）
- `extracted.csv`：提取后的结构化结果（默认提取 `answer` 与 `label`）

## 6. 提取规则

脚本会优先尝试把模型输出解析为 JSON，并提取：
- `answer`
- `label`

如解析失败，会把完整文本写入 `answer`，`label` 为空。你可以按论文任务自定义 `extract_fields`。

## 7. 干跑（不请求 API）

```bash
python scripts/run_batch.py --config configs/models.json --input data/prompts.csv --dry-run
```
