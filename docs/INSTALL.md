# 安装与接入指南

> 覆盖 WorkBuddy、Claude Code、Codex、Cursor、Trae、Qoder、VSCode、Cherry Studio
> 以及「让 AI 帮你配」的最省事路径。

---

## 目录

1. [第 0 步：申请麦当劳 MCP Token](#第-0-步申请麦当劳-mcp-token)
2. [第 1 步：把 MCP 接到你的 AI 客户端](#第-1-步把-mcp-接到你的-ai-客户端)
3. [第 2 步：装上 Skill（得到完整工作流）](#第-2-步装上-skill得到完整工作流)
4. [不想手动配？让 AI 帮你配](#不想手动配让-ai-帮你配)
5. [只用解析器（完全不接 MCP）](#只用解析器完全不接-mcp)
6. [故障排查](#故障排查)

---

## 第 0 步：申请麦当劳 MCP Token

**这是所有人必做的第一步。** Token 与你的麦当劳会员账号绑定，领券、查积分、算价都要用它识别你是谁。

### 申请地址

**https://open.mcd.cn/mcp**

官方使用指南（含每一步截图）：https://github.com/M-China/mcd-mcp-server

### 五步拿到 Token

| 步骤 | 操作 |
|---|---|
| 1 | 打开 https://open.mcd.cn/mcp ，点右上角 **登录** |
| 2 | 用**手机号 + 验证码**登录（就是你的麦当劳账号），登录后右上角变成 **控制台** |
| 3 | 点 **控制台** → 弹窗里点 **激活** |
| 4 | 阅读并同意《使用条款》和《麦当劳 MCP 服务规则》 |
| 5 | Token 生成成功，点**一键复制**，先存到一个安全的地方 |

> ⚠️ **Token 等同于你的账号凭证**。拿到之后：
> - 不要写进代码、不要提交到 GitHub、不要发在群里
> - 本仓库的 `mcp-config.example.json` 只有 `${MCD_MCP_TOKEN}` 占位符，就是为了防止这件事
> - 如果怀疑泄露，回控制台重新生成

### 服务端参数（所有客户端都用这三个值）

| 项 | 值 |
|---|---|
| 接入地址 | `https://mcp.mcd.cn` |
| 传输协议 | **Streamable HTTP** |
| 鉴权头 | `Authorization: Bearer <你的 Token>` |

### 三条限制，先知道

| 情况 | 表现 | 说明 |
|---|---|---|
| 请求太密 | 返回 `429` | 每个 Token **每分钟最多 600 次**，超了会短暂拒绝 |
| Token 不对 | 返回 `401` | Token 无效、过期或没带 Authorization 头 |
| 门店打烊 | 返回 `60003` | 算价、门店类接口会失败；**但领券不受营业时间影响** |

---

## 第 1 步：把 MCP 接到你的 AI 客户端

这一步只干一件事：告诉客户端「有个叫 mcd-mcp 的服务在 https://mcp.mcd.cn ，请求要带 Token」。

**完成这一步，你就已经能用了**——直接在对话里说「帮我领麦当劳券」「我积分还有多少」，AI 会自己去调工具。装上 Skill（第 2 步）只是让它更懂流程。

### 先看一张对照表

| 客户端 | 配置放在哪 | 下面有详细步骤 |
|---|---|---|
| **WorkBuddy** | 界面里粘贴 JSON | ✅ |
| **Claude Code** | `.mcp.json` 或 `claude mcp add` | ✅ |
| **Codex CLI** | `~/.codex/config.toml` | ✅ |
| **Cursor** | 设置 → Tools & MCP | ✅ |
| **Trae** | 设置 → MCP | ✅ |
| **Qoder** | 设置 → MCP / `~/.qoder/mcp.json` | ✅ |
| **VSCode（Copilot）** | `.vscode/mcp.json` | ✅ |
| **Cherry Studio** | 设置 → MCP → 从 JSON 导入 | ✅ |

---

### 1.1 WorkBuddy

1. 打开 WorkBuddy → 左侧边栏 **【专家 · 技能 · 连接器】** → **【连接器】** 页签
2. 右上角 **【自定义连接器】** → **【配置 MCP】**
3. 在手动配置页粘贴下面这段，把 `YOUR_MCP_TOKEN` 换成你的真实 Token，点**【保存】**

```json
{
  "mcpServers": {
    "mcd-mcp": {
      "type": "streamablehttp",
      "url": "https://mcp.mcd.cn",
      "headers": {
        "Authorization": "Bearer YOUR_MCP_TOKEN"
      }
    }
  }
}
```

4. 回到【自定义连接器】，把 **mcd-mcp 启用**
5. 在对话框里说「麦当劳 MCP 连上了吗」，能返回当前时间就是通了

> 如果新加的 MCP 没有立刻生效，检查它是否处于启用状态；部分版本需要在自定义连接器里点一下「信任」。

---

### 1.2 Claude Code

**方式 A：一条命令（推荐）**

```bash
claude mcp add --transport http mcd-mcp https://mcp.mcd.cn \
  --header "Authorization: Bearer YOUR_MCP_TOKEN"
```

**方式 B：项目级 `.mcp.json`**

在项目根目录建 `.mcp.json`：

```json
{
  "mcpServers": {
    "mcd-mcp": {
      "type": "http",
      "url": "https://mcp.mcd.cn",
      "headers": {
        "Authorization": "Bearer ${MCD_MCP_TOKEN}"
      }
    }
  }
}
```

然后设环境变量，避免 Token 落盘：

```bash
# macOS / Linux
export MCD_MCP_TOKEN="你的token"
# Windows PowerShell
$env:MCD_MCP_TOKEN="你的token"
```

验证：

```bash
claude mcp list
```

看到 `mcd-mcp` 状态为 connected 即可。

---

### 1.3 Codex CLI

编辑 `~/.codex/config.toml`（Windows 是 `C:\Users\<你>\.codex\config.toml`），追加：

```toml
[mcp_servers.mcd-mcp]
url = "https://mcp.mcd.cn"
bearer_token_env_var = "MCD_MCP_TOKEN"
startup_timeout_sec = 20
tool_timeout_sec = 120
```

Codex 不支持把 Token 写在 `http_headers` 里明文落盘（官方也不建议），**用 `bearer_token_env_var` 从环境变量读**：

```bash
# macOS / Linux
export MCD_MCP_TOKEN="你的token"

# Windows PowerShell（临时生效）
$env:MCD_MCP_TOKEN="你的token"

# Windows（永久，需要新开终端）
setx MCD_MCP_TOKEN "你的token"
```

`url` 字段会让 Codex 自动按 **Streamable HTTP** 连接，不需要额外指定协议类型。

---

### 1.4 Cursor

1. 顶部菜单 **设置** → **Tools & MCP**
2. 在 Installed MCP Servers 里点 **Add Custom MCP**
3. 在打开的 `mcp.json` 里填入：

```json
{
  "mcpServers": {
    "mcd-mcp": {
      "url": "https://mcp.mcd.cn",
      "headers": {
        "Authorization": "Bearer YOUR_MCP_TOKEN"
      }
    }
  }
}
```

4. 保存，回到设置页，状态应显示 **已连接**，并能看到麦当劳的工具列表

> 官方 Cursor 教程：https://cursor.com/cn/docs/context/mcp

---

### 1.5 Trae

1. **设置** → **MCP** → **手动添加**
2. 粘贴：

```json
{
  "mcpServers": {
    "mcd-mcp": {
      "url": "https://mcp.mcd.cn",
      "headers": {
        "Authorization": "Bearer YOUR_MCP_TOKEN"
      }
    }
  }
}
```

3. 点 **确认**，回到 MCP 页面确认状态为「已连接」
4. 回到对话框，**选择 `Builder with MCP` 模式**（这一步容易漏，不选就调不到工具）

> 官方 Trae 教程：https://docs.trae.cn/ide/model-context-protocol

---

### 1.6 Qoder

1. 右上角用户图标（或 `Ctrl + Shift + ,`）→ **Qoder Settings** → 左侧 **MCP**
2. **My Servers** 选项卡 → 右上角 **+ Add**
3. 在 JSON 里填入：

```json
{
  "mcpServers": {
    "mcd-mcp": {
      "url": "https://mcp.mcd.cn",
      "headers": {
        "Authorization": "Bearer YOUR_MCP_TOKEN"
      }
    }
  }
}
```

4. 关闭文件并按提示 **Save**，列表里出现 `mcd-mcp`，链接图标表示连接成功

> **注意**：Qoder 文档只列出了 STDIO 和 SSE 两种传输类型，对 Streamable HTTP 的说明是「用与 SSE 相同的方式配置 URL，IDE 会自动识别」。所以上面**没有写 `type` 字段**——写了 `"type": "streamablehttp"` 反而可能不被识别。
> 也可以直接编辑 `~/.qoder/mcp.json`。
> 官方文档：https://docs.qoder.com/zh/user-guide/chat/model-context-protocol

---

### 1.7 VSCode（GitHub Copilot）

在项目里建 `.vscode/mcp.json`：

```json
{
  "servers": {
    "mcd-mcp": {
      "type": "http",
      "url": "https://mcp.mcd.cn",
      "headers": {
        "Authorization": "Bearer ${input:mcd_token}"
      }
    }
  },
  "inputs": [
    {
      "id": "mcd_token",
      "type": "promptString",
      "description": "麦当劳 MCP Token（在 open.mcd.cn/mcp 申请）",
      "password": true
    }
  ]
}
```

用 `inputs` 的好处：Token 存在本机 VSCode 的加密存储里，**不会出现在文件里**，也不怕误提交。

> 官方文档：https://code.visualstudio.com/docs/copilot/customization/mcp-servers

---

### 1.8 Cherry Studio

1. 设置 → **MCP** → **添加** → 下拉选 **从 JSON 导入**
2. 粘贴官方标准 JSON（就是 1.1 里那段），替换 Token
3. 点确定，然后**打开启用开关**
4. 在聊天窗口选一个支持工具调用的模型，直接用自然语言提需求

> 官方文档：https://docs.cherry-ai.com/advanced-basic/mcp

---

## 第 2 步：装上 Skill（得到完整工作流）

**接 MCP 和装 Skill 是两件事。**

- **接 MCP** = 让 AI 有手（能调工具）
- **装 Skill** = 给 AI 一本操作手册（知道先查券、再领券、然后**必须核对到账**、最后按三档盘点）

不装 Skill 也能用，但 AI 可能会跳过「核对到账」这一步——而实测里正因为这一步才发现「领 3 张只到账 2 张」。**这个 Skill 的价值主要就在这里。**

### 2.1 WorkBuddy（原生支持，最简单）

把 `SKILL.md` 和 `references/` 整个目录复制到：

```
macOS / Linux:  ~/.workbuddy/skills/mcd-coupon-helper/
Windows:        C:\Users\<你>\.workbuddy\skills\mcd-coupon-helper\
```

最终结构必须是：

```
mcd-coupon-helper/
├── SKILL.md
└── references/
    ├── coupon-claim.md
    ├── coupon-wallet.md
    ├── coupon-price.md
    ├── points.md
    ├── parsing.md
    └── pitfalls.md
```

然后对话里说「麦当劳领券」「我的积分」即可触发。

> 主文件只有 59 行，只做路由；细节在 `references/` 里按需加载。不要一次读完所有子文件。

### 2.2 Claude Code

Claude Code 的 Agent Skills 用的是同一套 `SKILL.md` 约定（frontmatter 都是 `name` + `description`），可以直接搬。若你的版本对 frontmatter 有额外校验，按 Claude Code 官方 Skills 文档补字段即可。

```
<项目>/.claude/skills/mcd-coupon-helper/SKILL.md
<项目>/.claude/skills/mcd-coupon-helper/references/*.md
```

也可以放用户级目录（对所有项目生效）：

```
~/.claude/skills/mcd-coupon-helper/
```

### 2.3 Codex / Cursor / Trae / Qoder

这几个没有原生的 Skill 目录，两种可行做法：

**做法 A：塞进项目规则文件**（推荐）

把 `SKILL.md` 里的「铁律 + 路由表」复制到你项目的规则文件里：

| 客户端 | 规则文件 |
|---|---|
| Codex | `AGENTS.md` |
| Claude Code | `CLAUDE.md` |
| Cursor | `.cursor/rules/` 下的 `.mdc` |
| Trae | 项目规则设置 |
| Qoder | 项目规则 / 自定义指令 |

> 具体路径和命名各版本略有差异，以各客户端官方文档为准。核心是：**让 AI 每次会话都能看到这份流程约束。**

**做法 B：让 AI 自己读**（最省事，零配置）

直接把这两句发过去：

```
先读这两个文件，把它们当作你的操作手册，然后按里面写的流程帮我做事：
https://github.com/zxyyxzzxy/mcd-coupon-helper/blob/main/SKILL.md
https://github.com/zxyyxzzxy/mcd-coupon-helper/tree/main/references

读完先告诉我：领券之后必须做哪一步核对？为什么？
```

最后那句反问是关键——**它在检验 AI 到底有没有真的读到「双向核对」这条铁律**，而不是假装读过。

### 2.4 Skill 是干什么的：一句话版本

如果你不想搬整个 Skill，只想记住最重要的一条：

> **领券接口说「成功 N 张」不算数，必须再拉一次券包比对张数。**

实测中「免费脆薯饼」连续多天显示已领取，但券包里从来没有它。只信接口返回的工具，会一直告诉用户"领到了"。

---

## 不想手动配？让 AI 帮你配

以上步骤都可以交给 AI 做。**把下面这段复制给你的 AI（WorkBuddy / Claude Code / Cursor 都行）**，它就会直接帮你写好配置文件。

### 通用版（任何客户端）

```
帮我配置麦当劳 MCP 服务，按这个规范来：

服务参数：
- 名称：mcd-mcp
- 地址：https://mcp.mcd.cn
- 传输：Streamable HTTP
- 鉴权头：Authorization: Bearer <我的 token>

请这样做：
1. 先判断当前是什么客户端，找到它正确的 MCP 配置文件位置（不要猜，先确认文件是否存在）
2. 优先用环境变量 MCD_MCP_TOKEN 承载 token，不要把我的 token 以明文写进会被提交的文件
3. 如果配置文件已存在，追加而不是覆盖，不要破坏我原有的其他 MCP 配置
4. 配完告诉我：改了哪个文件、改了什么、怎么验证
5. 然后调用 now-time-info 验证连通性，把返回的时间给我看

我的 token：____________________

注意：不要把这个 token 写进任何 git 仓库、日志或输出里。
```

### WorkBuddy 专用版

```
帮我配麦当劳 MCP：
1. 读 ~/.workbuddy/mcp.json（Windows: C:\Users\<我>\.workbuddy\mcp.json）
2. 在 mcpServers 里加一个 mcd-mcp，type 用 streamablehttp，url 是 https://mcp.mcd.cn，
   headers 里放 Authorization: Bearer <我的 token>
3. 保留文件里现有的其他 MCP，不要覆盖
4. 写完调用 now-time-info 验证，再调用 query-my-account 看能不能读到我账号积分

我的 token 是：____________________

做完告诉我改了哪个文件的哪一段。如果配置里已经存在 mcd-mcp，先告诉我它现在长什么样再动手。
```

> ⚠️ 提醒：把 token 贴给 AI 意味着它会出现在这次对话里。如果你在意，配完之后回控制台重新生成一个，把旧的作废。

### 为什么推荐环境变量而不是明文

| 方式 | 风险 |
|---|---|
| Token 明文写进配置文件 | 文件一旦被提交/同步/截图就泄露 |
| 环境变量 + 占位符 | 配置文件可以安全分享，Token 只在本机内存里 |

本仓库的 `mcp-config.example.json` 用的就是 `${MCD_MCP_TOKEN}` 占位符。

---

## 只用解析器（完全不接 MCP）

如果你不需要麦当劳数据，只是想处理券的 Markdown 文本，可以只用 `scripts/parse_coupons.py`：

```bash
python3 scripts/parse_coupons.py fixtures/coupons_sample.md
python3 scripts/parse_coupons.py --now "2026-10-19T08:00:00" fixtures/coupons_sample.md
```

输出结构化 JSON，含 `usable_now`（此刻能否使用）、`days_left`、`weekdays` 等字段。

纯标准库，无第三方依赖，Python 3.8+。

```bash
python3 -m unittest discover -s tests -v   # 19 个测试，覆盖 4 种有效期格式与可用性判定
```

`--now` 参数不是多余的：券的可用性依赖「现在几点」，而机器时区未必是北京时间。把服务器时间注入进来，结果才正确、也可复现。

---

## 故障排查

| 现象 | 原因 | 处理 |
|---|---|---|
| `401` | Token 无效 / 过期 / 没带 Authorization 头 | 回 https://open.mcd.cn/mcp 重新复制 Token，检查 `Bearer ` 后面有一个空格 |
| `429` | 超过 600 次/分钟 | 降低请求频率，批量操作之间加间隔 |
| `60003` | 门店暂停营业 | 算价、门店、菜单类接口在打烊后会失败。**领券和查积分不受影响**，可以凌晨跑 |
| `60006` | 商品在该场景不可售 | 大概率是 `productCode` 跨场景复用了（到店 / 外送 / 团餐是三套 SKU），`beCode` 必须按场景重新获取 |
| 工具列表是空的 | MCP 没启用，或客户端不认这个传输类型 | 检查是否点了「启用 / 信任」；Qoder 要**去掉 `type` 字段** |
| AI 说"没有可领的券"但你不确定 | `available-coupons` 在异常时会抛协议错误（`data must be array`） | 让它**重试一次**。查询失败 ≠ 没有券，这两个不能混 |
| 领了券但券包里没有 | 已知数据不一致，实测真实存在 | 这就是为什么流程要求**双向核对**，别只信接口的成功计数 |
| Trae 里调不到工具 | 没切到 `Builder with MCP` 模式 | 回对话框切换到该模式 |
| Codex 连不上 | Token 环境变量没设 | `echo $MCD_MCP_TOKEN` 确认；Windows `setx` 后要重开终端 |

---

## 一句话总结

```text
1. 去 https://open.mcd.cn/mcp 拿 Token（手机号登录 → 控制台 → 激活）
2. 把 https://mcp.mcd.cn + Bearer Token 配进你的客户端
3. 想省心就把 SKILL.md 装进去（WorkBuddy 直接复制目录）
4. 最重要的那条规则：领券之后一定要核对到账
```
