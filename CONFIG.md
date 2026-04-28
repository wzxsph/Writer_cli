# 系统配置

## 模型配置
model: minimax-m2.7
max_tokens: 16000

## 章节字数配置
chapter_word_count:
  normal:
    min: 2500
    max: 8000
  climax:
    min: 3500
    max: 10000
  transition:
    min: 1500
    max: 5000

## 摘要窗口
summary_buffer_size: 10
recent_chapters_in_context: 3

## 沙盒校验超时
sandbox_timeout: 90

## Subagent 超时
subagent_timeout: 90

## 敏感词阈值
style_warning_threshold: 3
