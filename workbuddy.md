# WorkBuddy 开发对话上下文

> 本文件记录「麦麦领券助手」使用腾讯 WorkBuddy 智能体（Agent 模式）从需求确认到产出可运行 Skill 的完整开发过程，用于核验 WorkBuddy 专项奖励的联动活动条件。
> 内容为开发会话的忠实整理，已剔除所有 Token、账号凭证与个人身份信息。

---

## 一、开发环境

| 项 | 值 |
|---|---|
| 开发时间 | 2026-10-18 ~ 2026-10-19（北京时间） |
| 智能体 | WorkBuddy，Agent 模式（可读写文件、执行命令） |
| 工作目录 | `G:\workbuddyspace\mcd-mate` |
| 连接器 | 自定义 MCP `mcd-mcp`（麦当劳中国官方 MCP） |
| 依赖 | Python 3.13（仅标准库），Git Bash |

---

## 二、会话主线

### 第 1 轮：了解赛事并连通 MCP

- 用户给出活动仓库地址与 MCP Token，要求先连通 MCP。
- 智能体读取活动仓库 README、`activityGuidelines.md`、`RANKING.md`
- 检查本地 `~/.workbuddy/mcp.json`，发现 `mcd-mcp` 已配置
- 实际调用 `now-time-info` 与 `query-my-account` 验证：**两个接口均返回 200**，后者返回用户真实积分账户，确认 Token 与会员账号绑定有效

结论：连接正常，35 个工具可用，评分机制为公开 Star 数排序。

### 第 2 轮：逐个实测核心接口

- 用户要求「先试通各个核心接口看看真实数据结构」
- 智能体逐个加载 schema 并真实调用，共测 16 个接口，覆盖门店、菜单、定价、券、促销、积分商城、抽奖、外送、团餐
- 关键发现：
  - 到店 / 外送 / 团餐是**三套独立的 `beCode` + SKU + 价格体系**，`productCode` 不能跨场景复用
  - 团餐折扣单调递增（满 500 → 74 折，满 2000 → 66 折），且免费「保鲜速达」折扣最优
  - `list-nutrition-foods` 返回非 JSON 的自定义字符串，且只有商品名没有 `productCode`
  - `campaign-calendar`、`query-my-coupons` 只返回人读 Markdown 文本
- 产出 `MCP_API_PROBE_REPORT.md`（接口实测报告）

### 第 3 轮：确定选题并实测券链路

- 用户提出：「我想做一个能帮我查优惠券、自动领优惠券的 skill，就叫麦麦领券助手」
- 智能体先补齐券相关接口实测，再动笔：
  - `available-coupons` → 3 张可领（首次调用曾抛协议错误，复测恢复）
  - `auto-bind-coupons` → 报「成功 3 张、失败 0 张」，返回含 `couponId` + `couponCode`
  - `query-my-coupons` → 张数 5 → 7，**实际只到账 2 张，「免费脆薯饼」未出现**
  - `query-store-coupons` → 空数组（当时门店已打烊，凌晨 1:44）
  - `calculate-price` → `60003 门店暂停营业`，确认算价强依赖营业时间
- 关键判断：领券不受营业时间限制，算价受限 → 领券可做定时任务，算价只能白天执行

### 第 4 轮：编写并验证 Skill

- 智能体参考本地已有 Skill 的目录与 frontmatter 规范，写入 `~/.workbuddy/skills/mcd-coupon-helper/SKILL.md`
- 通过 Skill 加载器实际加载验证：**可被系统识别**
- 用用户真实券包（7 张）跑了一次完整盘券，输出按「今日到期 / 3 日内 / 稍后可用」分档

### 第 5 轮：自动化 + 参赛包装

- 用户：「好的，继续吧」→ 执行此前建议的两步
- 创建每日 10:35 的定时任务（选点理由：券普遍 10:30 生效），Prompt 内固化「双向核对」流程
- 核对官方必交清单：`README.md`、`CONTEST_DECLARATION.md`、`MCP_INTEGRATION.md`、`mcp-config.example.json`、`workbuddy.md`（专项奖励必需）
- 用 `curl` 下载官方 `CONTEST_DECLARATION.md` 并**原样复制**，以 MD5 校验一致（`91a7b32e...`）
- 抓取一次真实券包返回作为测试样本，发现**部分券缺少「领取时间」字段**
- 编写 `scripts/parse_coupons.py`（券 Markdown → 结构化 JSON）+ 19 个单元测试
- 首轮测试 18/19 通过，失败项为「周一至周五」被正则误判为单日；修正星期枚举分支使分隔符必须被消费后，19/19 全绿

---

## 三、智能体在开发中的具体作用

| 环节 | WorkBuddy 承担的工作 |
|---|---|
| 资料获取 | 抓取并结构化活动规则、必交文件清单、排行榜数据 |
| 接口探测 | 逐个加载 MCP Tool schema 并按真实参数调用，记录原样返回 |
| 事实校验 | 对「折扣阶梯是否倒挂」等推断做二次算价验证，并纠正自身误判 |
| 代码产出 | 编写解析器与测试，运行测试并修复失败用例 |
| 文件治理 | 校验官方声明文件 MD5，确保未被改动；编写 `.gitignore` 防凭证入库 |
| 自动化 | 创建定时任务，把「双向核对」等业务规则固化进 Prompt |

---

## 四、可核验的事实点

1. `CONTEST_DECLARATION.md` 的 MD5 与官方原文一致：`91a7b32ec28098b609ca3f215cdf7147`
2. 解析器 19 个单元测试全部通过：`python3 -m unittest discover -s tests -v`
3. `fixtures/coupons_sample.md` 来自真实接口返回（图片 URL 已脱敏为 `<IMG_URL>`）
4. 「领 3 张只到账 2 张」为真实观测结果，非构造样例
5. 仓库内不含任何真实 Token，`mcp-config.example.json` 仅含环境变量占位符
