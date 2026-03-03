# LLM 涉入度 × 论据强弱 × 主题 批量实验脚手架

用于你的实验场景：同一个模型在多主题（topic）下，按 4 个条件分别重复多次（如 20 次），并保存原始输出与结构化结果。

4 个条件：
- 高涉入度 + 强论据
- 高涉入度 + 弱论据
- 低涉入度 + 强论据
- 低涉入度 + 弱论据

## 1) 安装

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2) 配置 API Key

```bash
cp .env.example .env
```

然后编辑 `.env`：

```env
OPENAI_API_KEY=...
DEEPSEEK_API_KEY=...
QIANWEN_API_KEY=...
LLAMA_API_KEY=...
```

## 3) 配置模型

```bash
cp configs/models.example.json configs/models.json
```

## 4) 配置 Prompt 数据

文件：`data/prompts.csv`

建议字段：
- `id`
- `topic`（新增，主题/claim 维度）
- `condition`
- `involvement`
- `argument_strength`
- `prompt`

仓库里给了 4 条同主题样例；后续你可按不同 claim 扩展为多个 `topic`。

## 5) 先测流程是否跑通（不请求 API）

```bash
python scripts/run_batch.py \
  --config configs/models.example.json \
  --input data/prompts.csv \
  --repeats 20 \
  --dry-run
```

## 6) 正式运行（请求真实 API）

```bash
python scripts/run_batch.py \
  --config configs/models.json \
  --input data/prompts.csv \
  --repeats 20 \
  --temperature 0.7 \
  --max-tokens 256 \
  --outdir outputs
```

## 7) 输出在哪看

每次运行会生成：`outputs/<timestamp>/`

里面有：
- `raw_responses.jsonl`：原始响应（含 `topic`、`repeat_index`、耗时、错误）
- `extracted.csv`：提取后的结构化表（含 `topic`、`attitude_score`）

查看：

```bash
ls outputs
head -n 5 outputs/<timestamp>/raw_responses.jsonl
head -n 5 outputs/<timestamp>/extracted.csv
```

## 8) 这版与你要求对齐的关键点

- 新增 `topic` 维度进入输入与输出，方便后续多 claim 批量分析
- prompt 后缀只做“JSON 输出格式约束”，不再要求模型生成理由
- 默认提取字段为 `attitude_score`
- 如果模型未严格返回 JSON，仍会尝试从文本提取 0~10 分

