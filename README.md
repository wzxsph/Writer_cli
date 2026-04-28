# Writer_cli - 网文撰写 CLI Agent

> 测试版本，可直接让 Claude Code 运行。中国区推荐使用 MiniMax API：https://platform.minimaxi.com/subscribe/token-plan?code=JBtwp2z3Vh&source=link

基于 Claude Code 架构的网文自动化生成管线。通过 9 步确定性工程流程，实现无需人工干预的章节批量生成。

---

## 目录

- [快速开始](#快速开始)
- [输入文件清单](#输入文件清单)
- [输出产物清单](#输出产物清单)
- [CLI 命令详解](#cli-命令详解)
- [工作流程](#工作流程)
- [项目结构](#项目结构)
- [配置文件详解](#配置文件详解)
- [核心模块](#核心模块)
- [沙盒校验器](#沙盒校验器)
- [Agent 系统](#agent-系统)

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API

项目根目录创建 `env` 文件：

```bash
export ANTHROPIC_BASE_URL=https://api.minimaxi.com/anthropic
export ANTHROPIC_API_KEY=你的API密钥
```

### 3. 初始化项目

```bash
python cli.py init
```

### 4. 填充配置文件

首次使用需要编辑以下文件（详见[配置文件详解](#配置文件详解)）：

| 必填文件 | 用途 |
|---------|------|
| `MANIFEST.md` | **作品元数据**（书名、标签、主角、简介） |
| `CLAUDE.md` | 世界观规则、主角人设、文风禁区 |
| `OUTLINE.md` | 小说大纲、每章核心情节点 |
| `WORLDBUILD.md` | 地理、组织、实体别名 |
| `POWERSYSTEM.md` | 战力等级体系 |
| `CHARACTERS.md` | 角色状态表 |
| `SCHEDULE.md` | 任务调度队列（首章设为 READY） |

> **重要**：`MANIFEST.md` 是必填文件！包含：
> 1. 书本名称
> 2. 作品标签（男频/女频、具体标签）
> 3. 主角名1、2
> 4. 作品简介
>
> 每次写作前必须检查该文件是否已填写完整。

### 5. 创建章节任务文件

在项目根目录创建 `TASK_VOL_1_CHAPTER_1.md`，定义本章任务：

```markdown
# VOL_1 Chapter 1 任务

## 任务类型
normal

## 章节锚点
主角重生回末世前夕，在自己身体上发现混沌诀刻印

## 应激活的伏笔
[FORESHADOW_MAIN_001]

## 叙事视角
第三人称

## 章节目标
1. 建立主角重生设定
2. 发现混沌诀刻印
3. 铺垫末世即将到来的紧迫感
```

### 6. 生成章节

```bash
python cli.py generate --vol VOL_1 --chapter 1
```

成功后在 `chapters/VOL_1/CHAPTER_1.md` 生成正文。

---

## 输入文件清单

### 必须填写的设定文件

| 文件 | 说明 | 格式 |
|------|------|------|
| `MANIFEST.md` | **作品元数据**（必填！书名/标签/主角/简介） | Markdown |
| `CLAUDE.md` | 全局硬规则锁（必读） | Markdown |
| `OUTLINE.md` | 小说大纲 | Markdown |
| `WORLDBUILD.md` | 世界观设定 | Markdown |
| `POWERSYSTEM.md` | 战力等级体系 | Markdown |
| `CHARACTERS.md` | 角色状态表 | Markdown |
| `TIMELINE.md` | 时间线锁 | Markdown |
| `STYLE_BLACKLIST.md` | 文风禁止词表 | Markdown |
| `PROTECTED_CHARS.md` | 不可死亡角色名单 | Markdown |

### 必须填写的运行时文件

| 文件 | 说明 | 格式 |
|------|------|------|
| `SCHEDULE.md` | 任务调度队列 | Markdown |
| `TASK_VOL_X_CHAPTER_Y.md` | 单章任务定义（每次生成前创建） | Markdown |

### 可选的运行时文件

| 文件 | 说明 | 格式 |
|------|------|------|
| `MEMORY.md` | 伏笔状态追踪（首次自动创建） | Markdown |
| `SUMMARY_BUFFER.md` | 最近10章摘要（首次自动创建） | Markdown |
| `CONFIG.md` | 系统配置（首次自动创建） | YAML |

---

## 输出产物清单

| 产物 | 路径 | 说明 |
|------|------|------|
| **章节正文** | `chapters/VOL_X/CHAPTER_Y.md` | 生成的小说正文 |
| **伏笔状态** | `MEMORY.md` | 自动更新的伏笔追踪 |
| **调度状态** | `SCHEDULE.md` | 任务队列推进状态 |

---

## CLI 命令详解

### generate - 生成章节

```bash
python cli.py generate --vol VOL_1 --chapter 1
python cli.py generate --vol VOL_1 --chapter 5 --type climax
python cli.py generate --vol VOL_2 --chapter 15 --type transition
```

**参数：**

| 参数 | 必填 | 说明 | 示例 |
|------|------|------|------|
| `--vol` | 是 | 卷名 | `VOL_1`, `VOL_2` |
| `--chapter` | 是 | 章节号 | `1`, `15` |
| `--type` | 否 | 章节类型 | `normal`(默认), `climax`, `transition` |

**输出：**

- 成功：输出 `chapters/VOL_X/CHAPTER_Y.md` 文件
- 失败：输出错误码和原因，进程退出

**章节类型对应字数（由 CONFIG.md 控制）：**

| 类型 | 默认字数区间 |
|------|-------------|
| `normal` | 2500-8000 字 |
| `climax` | 3500-10000 字 |
| `transition` | 1500-5000 字 |

### status - 查看当前状态

```bash
python cli.py status
```

**输出示例：**

```
# 当前状态

当前任务: VOL_1 Chapter 5
状态: READY
```

### list-pending - 列出待执行任务

```bash
python cli.py list-pending
```

### init - 初始化项目

```bash
python cli.py init
```

创建必要的目录结构和默认配置文件（仅当文件不存在时）。

---

## 工作流程

### 9 步自动化管线

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLI 跑批模式                              │
│  每次章节生成通过以下线性自动流完成完整的"感知—规划—生成—校验—提交"闭环 │
└─────────────────────────────────────────────────────────────────┘

Step 1: 上下文装配 (Context Assembly)
   │
   ├─ 读取 WORLDBUILD.md (世界观设定)
   ├─ 读取 OUTLINE.md (小说大纲)
   ├─ 读取最近3章摘要 (SUMMARY_BUFFER.md)
   ├─ 读取 TASK_VOL_X_CHAPTER_Y.md (当前章节任务)
   └─ 提取 MEMORY.md 中 open 状态的伏笔快照
   │
   ▼

Step 2: 任务意图解析 (Intent Parsing)
   │
   ├─ 将上下文 + 任务解析 Prompt 传入模型
   ├─ 模型返回结构化 JSON：
   │   ├─ core_plot_nodes (核心情节节点)
   │   ├─ entities_to_appear (本章需出现的实体)
   │   └─ foreshadow_triggered (是否触发伏笔)
   └─ 输出是下游所有步骤的调度依据
   │
   ▼

Step 3: 权限门控预检 (Permission Gate Pre-Check)
   │
   ├─ 高危操作拦截：
   │   ├─ 核心角色死亡 (PROTECTED_CHARS.md 名单)
   │   ├─ 世界观底层设定更改
   │   └─ 已公开伏笔强制关闭
   ├─ 命中任意一条 → 暂停并输出错误码
   └─ 等待人工审核或 --override 重启
   │
   ▼

Step 4: 正文生成 (Primary Generation)
   │
   ├─ 调用大模型生成章节正文
   ├─ Prompt 严格规定：
   │   ├─ 纯叙事散文格式
   │   ├─ 禁止 Markdown 标记
   │   └─ 字数区间约束
   └─ 模型职责：填充上下文约束内的散文
   │
   ▼

Step 5: 编程式沙盒校验 (Tool Sandbox Validation)
   │
   ├─ 独立子进程运行校验脚本
   ├─ 校验内容：
   │   ├─ A: 字数区间
   │   ├─ B: 人名/地名一致性
   │   ├─ C: 战力/等级边界
   │   ├─ D: 伏笔引用连贯性
   │   ├─ E: 敏感词/文风污染
   │   └─ F: 首末句连贯性 (仅警告)
   └─ stdin/stdout 通信，进程隔离
   │
   ▼

Step 6: 沙盒报告路由 (Report Routing)
   │
   ├─ 全部通过 → Step 7
   ├─ 可自动修复 (如人名拼写偏差) → 局部修正 Prompt → 回 Step 5
   └─ 无法修复 (如结构性矛盾) → 终止，记录失败原因
   │
   ▼

Step 7: 动态记忆提交 (Memory Commit)
   │
   ├─ 独立轻量级调用提取：
   │   ├─ foreshadow_new (新增伏笔)
   │   ├─ foreshadow_closed (已收束伏笔)
   │   └─ character_state_delta (角色状态变更)
   └─ 追加写入 MEMORY.md (不覆盖历史)
   │
   ▼

Step 8: 章节归档 (Chapter Archive)
   │
   ├─ 写入 chapters/VOL_X/CHAPTER_Y.md
   └─ 原子性写入：先写 .tmp，成功后重命名
   │
   ▼

Step 9: 调度器推进 (Scheduler Advance)
   │
   ├─ 更新 SCHEDULE.md
   │   ├─ 当前任务 DONE
   │   └─ 下一任务 READY
   ├─ 生成 TASK_VOL_X_CHAPTER_Y+1.md (如不存在)
   └─ 管线空闲，等待下一轮
```

---

## 项目结构

```
Writer_cli/
├── core/                    # 核心管线
│   ├── assembler.py         # 上下文装配器
│   ├── intent_parser.py     # 任务意图解析
│   ├── permission_gate.py   # 权限门控
│   ├── generator.py         # 正文生成器
│   ├── scheduler.py         # 调度器
│   ├── compressor.py        # 5级压缩管线
│   └── config.py            # 配置加载
│
├── sandbox/                 # 沙盒校验器
│   ├── validator.py         # 主校验程序
│   ├── word_count_guard.py  # A: 字数区间守卫
│   ├── entity_consistency_guard.py  # B: 实体一致性守卫
│   ├── power_scaling_guard.py       # C: 战力边界守卫
│   ├── foreshadow_guard.py          # D: 伏笔引用守卫
│   ├── style_contamination_guard.py # E: 文风污染守卫
│   └── chapter_boundary_guard.py     # F: 首末连贯守卫
│
├── agents/                  # Agent 系统
│   ├── orchestrator.py      # 主控写手 Agent
│   ├── lore_verifier.py     # 设定考据 Subagent
│   ├── anti_cliche.py       # 反套路审查 Subagent
│   ├── memory_manager.py    # 伏笔管理 Subagent
│   └── mailbox.py           # Mailbox 通信机制
│
├── chapters/                # 章节归档目录（输出）
│   ├── VOL_1/
│   │   └── CHAPTER_1.md
│   └── VOL_2/
│
├── mailbox/                 # Agent 通信邮箱
│   ├── outbox/             # 主控→Subagent（不纳入版本控制）
│   └── inbox/              # Subagent→主控
│
├── cli.py                   # CLI 入口
├── CONFIG.md                # 系统配置
├── CLAUDE.md                # 全局硬规则锁
├── MEMORY.md                # 动态伏笔状态机（自动更新）
├── OUTLINE.md              # 小说大纲
├── WORLDBUILD.md           # 世界观设定
├── CHARACTERS.md           # 角色状态表
├── TIMELINE.md             # 时间线锁
├── POWERSYSTEM.md          # 战力等级体系
├── PROTECTED_CHARS.md      # 核心角色保护名单
├── STYLE_BLACKLIST.md      # 文风禁止词表
├── SCHEDULE.md             # 任务调度队列
└── SUMMARY_BUFFER.md       # 最近10章摘要（自动维护）
```

---

## 配置文件详解

### CLAUDE.md - 全局硬规则锁（必填）

系统的"宪法文件"，永不压缩、永不修改。

```markdown
# 全局硬规则锁

## 世界观物理规则
1. 灵气潮汐定律：灵气以12年为一个周期涌动
2. 能量守恒法则：所有超凡力量消耗等价生命力
3. 因果追溯律：改变重大历史事件必受天道反噬

## 主角永久性格定义
- 核心：利己但不损人，精明但不奸诈
- 行为准则：人不犯我我不犯人，人若犯我加倍奉还

## 文风禁止列表
- 禁止使用"读者老爷"、"作者菌"等打破第四墙的表达
- 禁止超过300字的纯内心独白

## 伏笔永久保护区
- FORESHADOW_MAIN_*：主线核心伏笔
- FORESHADOW_FEMALE_*：女主相关伏笔
```

### OUTLINE.md - 小说大纲（必填）

```markdown
# 小说大纲

## 总纲
[一句话概括全书主线]

## 卷纲
### VOL_1 末世重生
- 核心冲突：主角重生复仇
- 预计章节：30章

### VOL_2 灵气复苏
- 核心冲突：势力洗牌
- 预计章节：30章

## 章纲（节选）
### VOL_1 Chapter 1
- 章节类型：climax
- 核心事件：主角重生，发现混沌诀刻印
- 章节目标：建立重生设定，遇见第一女主伏笔

### VOL_1 Chapter 2
- 章节类型：normal
- 核心事件：末世倒计时，主角布局
```

### WORLDBUILD.md - 世界观设定（必填）

```markdown
## 物理规则
[灵气体系、修炼规则、地理限制]

## 已注册实体别名
### 角色名
- 云霄：[云霄宗主, 云少宗主]
- 李沉舟：[沉舟, 舟哥]

### 地名
- 青云宗：[青云山, 宗门]
- 青州城：[青州, 州城]
```

### POWERSYSTEM.md - 战力等级体系（必填）

```markdown
## 境界等级锚点
- 炼气期: 1
- 筑基期: 2
- 金丹期: 3
- 元婴期: 4
- 化神期: 5

## 势力划分
- 一流势力：太虚宗、万剑门
- 二流势力：青云宗、紫霄派
- 三流势力：散修联盟

## 角色当前修为
- 云霄: 元婴中期
- 李沉舟: 金丹后期
```

### PROTECTED_CHARS.md - 不可死亡角色名单（必填）

```markdown
# 核心角色保护名单

## 绝对保护（禁止死亡）
- 叶尘（主角）
- 林诗音（第一女主）
- 上官婉儿（第二女主）

## 相对保护（禁止轻易死亡）
- 老周（重要配角）
```

### STYLE_BLACKLIST.md - 文风禁止词表（必填）

```markdown
## 平台审核敏感词（阻断级）
[敏感词列表...]

## 网文烂俗表达（警告级）
- 猛地一愣
- 心中一凛
- 众人哗然
- 不由得

## 作者自定义禁止词（阻断级）
[自定义词表...]
```

### SCHEDULE.md - 任务调度队列（必填）

```markdown
# 任务调度队列

## 当前任务
- volume: VOL_1
- chapter: 1
- status: READY

## 等待队列
- volume: VOL_1
  chapter: 2
  status: PENDING
```

### TASK_VOL_X_CHAPTER_Y.md - 单章任务（每次生成前创建）

```markdown
# VOL_1 Chapter 1 任务

## 任务类型
climax

## 章节锚点
主角重生回末世前夕，在自己身体上发现混沌诀刻印，获得第一桶金机遇信息

## 应激活的伏笔
[FORESHADOW_MAIN_001, FORESHADOW_FEMALE_001]

## 叙事视角
第三人称

## 章节目标
1. 建立主角重生设定，展示前世十年末世生存经验
2. 发现混沌诀刻印，获取前世机遇信息
3. 铺垫末世即将到来的紧迫感
4. 展示主角利己但不损人的核心性格

## 写作风格要求
- 开头直接切入场景，不要铺垫
- 环境描写用具体细节展现（声音、气味、温度）
- 对话用「」标记
- 心理活动通过动作和对话展现，不直接描写
- 章节结尾留钩子
```

### CONFIG.md - 系统配置（首次自动创建）

```yaml
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
```

### MEMORY.md - 动态伏笔状态机（自动维护）

首次生成后自动创建，手动编辑需遵循格式：

```markdown
# 动态伏笔状态机

## 伏笔条目格式
# - id: FORESHADOW_001
#   status: open|closed|dormant
#   last_chapter: 1
#   keywords: [关键词1, 关键词2]

## 伏笔条目

### 主线伏笔
- id: FORESHADOW_MAIN_001
  status: open
  last_chapter: 1
  keywords: [混沌诀, 重生者, 修炼系统]

### 女主伏笔
- id: FORESHADOW_FEMALE_001
  status: open
  last_chapter: 1
  keywords: [上官婉儿, 命运羁绊]

## 角色状态变更

### 第一卷状态
- char: 叶尘
  change: 重生者，获得混沌修炼系统
  chapter: 1
```

---

## 核心模块

### 配置加载 (`core/config.py`)

```python
from core.config import load_config

config = load_config()
print(config.model)           # 模型名称
print(config.max_tokens)      # 最大 token 数
print(config.chapter_word_count["normal"].min)  # 普通章节最少字数
```

### 上下文装配 (`core/assembler.py`)

```python
from core.assembler import assemble_chapter_context

context = assemble_chapter_context("VOL_1", 5, "normal")
# 返回拼接好的上下文字符串
```

### 正文生成 (`core/generator.py`)

```python
from core.generator import create_llm_client, get_generator

client = create_llm_client()  # 自动检测 MiniMax/Mock
generator = get_generator(client)

text = generator.generate_chapter(
    context="...",
    task="...",
    vol="VOL_1",
    chapter=5,
    chapter_type="normal"
)
```

### 调度器 (`core/scheduler.py`)

```python
from core.scheduler import get_scheduler

scheduler = get_scheduler()
next_task = scheduler.advance_to_next("VOL_1", 5)
# 返回下一章任务信息
```

### 5级压缩管线 (`core/compressor.py`)

防止上下文随小说长度膨胀：

| 级别 | 名称 | 机制 |
|------|------|------|
| 1 | 原文截断 | 历史章节仅存路径引用，不注入内容 |
| 2 | 摘要压缩 | 2000字正文→200字摘要 |
| 3 | 滚动窗口 | 维持最近10章摘要，冷存储旧摘要 |
| 4 | 废稿清洗 | 修正循环中间产物不污染主上下文 |
| 5 | 定期去重 | closed 伏笔迁移至冷存储 |

---

## 沙盒校验器

沙盒以独立子进程运行，通过 stdin/stdout 与主控进程通信。

### A. 字数区间守卫

```python
from sandbox.word_count_guard import WordCountGuard

guard = WordCountGuard(min_count=2000, max_count=2500)
passed, reason = guard.validate("章节正文...")
```

### B. 实体一致性守卫

```python
from sandbox.entity_consistency_guard import EntityConsistencyGuard

guard = EntityConsistencyGuard()
passed, violations = guard.validate("章节正文...")
# violations 包含未注册变体信息
```

### C. 战力边界守卫

```python
from sandbox.power_scaling_guard import PowerScalingGuard

guard = PowerScalingGuard()
passed, violations = guard.validate("章节正文...")
# 检测角色修为描述是否超出锚点
```

### D. 伏笔引用守卫

```python
from sandbox.foreshadow_guard import ForeshadowCoherenceGuard

guard = ForeshadowCoherenceGuard()
passed, violations = guard.validate("章节正文...", "VOL_1", 5)
```

### E. 文风污染守卫

```python
from sandbox.style_contamination_guard import StyleContaminationGuard

guard = StyleContaminationGuard()
passed, violations = guard.validate("章节正文...")
```

### F. 首末连贯守卫

```python
from sandbox.chapter_boundary_guard import ChapterBoundaryGuard

guard = ChapterBoundaryGuard()
passed, reason = guard.validate("当前章节正文", "VOL_1", 5, llm_client)
# 仅作警告，不触发阻断
```

### 主校验程序

```python
from sandbox.validator import SandboxValidator

validator = SandboxValidator()
report = validator.validate_all(
    text="章节正文",
    vol="VOL_1",
    chapter=5,
    chapter_type="normal",
    min_word_count=2000,
    max_word_count=2500,
    llm_client=client
)

print(report["passed"])           # 是否通过
print(report["violations"])        # 违规列表
print(report["warnings"])          # 警告列表
print(report["auto_fixable"])      # 是否有可自动修复的违规
```

---

## Agent 系统

### Mailbox 通信机制

基于 JSON 文件的异步消息传递，实现进程隔离：

```
mailbox/
├── outbox/                    # 主控 Agent 投递任务
│   └── msg_xxx_lore_verifier.json
└── inbox/                     # Subagent 写回结果
    └── resp_xxx_lore_verifier.json
```

消息格式：

```json
{
    "id": "msg_xxx",
    "sender": "orchestrator",
    "recipient": "lore_verifier",
    "message_type": "verify_lore",
    "task_id": "task_xxx",
    "payload": {...},
    "timestamp": "2026-04-27T12:00:00",
    "status": "pending"
}
```

### 主控写手 Agent

负责执行 9 步循环，向 Subagent 派发任务：

```python
from agents.orchestrator import get_orchestrator

orchestrator = get_orchestrator(llm_client)
success, message = orchestrator.run_chapter_loop("VOL_1", 5, "normal")
```

### Subagent 类型

| Agent | 职责 | 接收的上下文 |
|-------|------|-------------|
| **设定考据** | 校验世界观规则、角色能力、组织结构 | 文本片段 + 设定文件路径 |
| **反套路审查** | 检测套路桥段、疲劳模式 | 200字情节摘要 |
| **伏笔管理** | 识别新增/已收束伏笔，更新 MEMORY.md | 本章正文 |

### 用完即毁策略

每个 Subagent 任务完成后：
1. 临时上下文立即销毁
2. 中间推理不进入长期记忆
3. 仅保留审查结论和必要状态更新
4. 防止审查者偏见污染主控 Agent

---

## 架构原则

> **大模型的输出是原材料，系统的拦截链路才是产品质量的决定因素。**

核心设计原则：
1. **不信任大模型的自我约束** - 所有"正确性要求"由系统校验
2. **确定性优先** - 管线的每一步都是可重现、可审计的
3. **气密隔离** - Subagent 间上下文不共享，防止污染
4. **可回滚** - 任何步骤失败都可追溯原因
5. **可跑批** - 支持无人值守的批量章节生成
