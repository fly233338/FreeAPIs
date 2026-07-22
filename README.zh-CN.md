# FreeAPIs

[English](README.md)

FreeAPIs 是一个无需提供凭据、可自动更新的免费生成式模型导航，当前覆盖
OpenRouter、Groq 和 Gemini Developer API。

本项目只发布导航数据，不提供代理、网关、额度追踪或配置生成，也不要求用户或
CI 提交任何平台 API Key。免费状态和限制可能随时变化；正式使用前请再次核对
平台当前条款。

## 平台导航

<!-- BEGIN GENERATED MODELS -->
| 平台 | 状态 | 模型数 | 输出类型 | 免费类型 | 最近更新 | 完整列表 |
|---|---|---:|---|---|---|---|
| [OpenRouter](<https://openrouter.ai/api/v1/models>) | <code>fresh</code> | 13 | <code>text</code> | <code>free_variant</code> | 2026-07-22 | [查看模型](<providers/openrouter/README.zh-CN.md>) |
| [Groq](<https://console.groq.com/docs/rate-limits>) | <code>fresh</code> | 7 | <code>text</code>, <code>audio</code> | <code>free_plan</code> | 2026-07-22 | [查看模型](<providers/groq/README.zh-CN.md>) |
| [Gemini](<https://ai.google.dev/gemini-api/docs/pricing>) | <code>fresh</code> | 17 | <code>text</code>, <code>audio</code> | <code>free_tier</code> | 2026-07-22 | [查看模型](<providers/gemini/README.zh-CN.md>) |
<!-- END GENERATED MODELS -->

## 收录规则

- **OpenRouter：** 仅收录以 `:free` 结尾且核心价格为零的具体模型 ID；排除
  `openrouter/free` 路由器及非生成模型。
- **Groq：** 以官方 Free Plan Limits 表格为准，并要求公开模型详情页确认其输出
  为生成式文本、图像、音频或视频。
- **Gemini：** 仅收录 Standard 定价表中 Free Tier 核心输入和输出均标记为
  `Free of charge` 的模型。

Embedding、Rerank、安全/分类以及语音识别或纯转写模型均不收录。无法确认输出
类型时，只记录日志并跳过该模型。

`free_type` 仅使用 `free_variant`、`free_plan`、`free_tier`；`output_types`
仅使用 `text`、`image`、`audio`、`video`。本项目不维护各平台的具体额度。

## 使用方法

需要 Python 3.12 或更高版本。

```console
python -m pip install -e .
python -m freeapis update
python -m freeapis update --provider groq
python -m freeapis render
python -m freeapis check
```

`update` 会抓取公开官方来源，按平台独立合并，校验 `data/models.json`，并重建
README 导航及平台详情页。某个平台失败时保留其旧记录并标记为 `stale`，其他成功平台仍会
更新。命令在写入有效的部分结果后以非零状态退出，以便 CI 提醒维护者。

## 数据约定

`data/models.json` 顶层包含 `schema_version`、`generated_at`、`providers` 和
`models`。每条模型记录严格包含以下字段：

```text
provider, model_id, name, output_types, free_type, model_url, api_key_url,
docs_url, source_url, last_updated
```

`last_updated` 表示该模型最近一次被官方来源确认免费的日期。项目不保存历史
快照，变更追踪由 Git 历史承担。

## 开发

```console
python -m pip install -e ".[test]"
pytest
```

单元测试使用精简官方页面夹具，不访问实时网络。

## 许可证

[MIT](LICENSE)
