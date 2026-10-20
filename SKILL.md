---
name: "mcd-coupon-helper"
displayName: "麦麦领券助手"
description: "基于麦当劳中国 MCP 的省钱管家，管两样东西：优惠券和麦享会积分。券：查询可领取的麦麦省券、一键领取并核对是否真的到账、盘点券包按到期时间分档、按门店算用券后的真实实付；积分：查可用/累计/已用/已过期积分、算出本月将过期的积分、结合积分商城给出该换什么。触发场景：当用户说「麦当劳领券」「麦麦领券」「麦麦省」「麦当劳优惠券」「领麦当劳的券」「我的麦当劳券」「麦当劳券包」「麦当劳有什么券」「麦麦券」「券快过期了」「用这张券能省多少」「麦当劳积分」「麦享会积分」「我的积分」「积分快过期了」「积分能换什么」「积分商城」，或询问任何与麦当劳优惠券、优惠、积分、省钱相关的问题时使用。"
description_zh: "麦当劳优惠券与麦享会积分管家：一键领券、核对到账、券包盘点、积分过期预警"
description_en: "McDonald's China coupon and points helper: claim coupons, verify delivery, track expiry, warn on expiring points"
version: "1.1.0"
homepage: "https://mcp.mcd.cn"
---

# 麦麦领券助手

麦当劳中国的**省钱管家**，基于官方 MCP（`mcd-mcp`）。管两件事：**券** 和 **积分**。

## 铁律（所有场景通用）

1. **只报事实，不造字段。** 券接口返回的是人读文本，不是 JSON。文本里没有的东西（例如单张已持有券的 `couponId`）绝对不许臆造或推断。
2. **领券必须双向核对。** 领完要交叉验证 ① `available-coupons` 状态是否变为已领取 ② `query-my-coupons` 张数是否相应增加。对不上就如实报差异。
3. **区分「没券」和「没营业」。** `query-store-coupons` 返回空数组可能是门店打烊，必须结合 `businessStartTime`/`businessEndTime` 判断。
4. **金额与积分别混。** 券接口价格单位是**元**；`calculate-price` 金额单位是**分**（展示要 ÷100）；积分单位是**分**（直接写「891.1 分」，不要换算成钱）。
5. **不擅自下单、不擅自兑换。** 本 Skill 只做查询、领券、算价、建议。下单（`create-order`）与积分兑换（`mall-create-order`）都必须用户明确要求并二次确认后才可执行。

## 按需加载：先判断意图，再读对应文件

**不要一次读完所有文件。** 按下表只读当前意图对应的那一份，其余等用到再读。

| 用户意图 | 读这个文件 | 涉及工具 |
|---|---|---|
| 有什么券可领 / 帮我领券 | `references/coupon-claim.md` | `available-coupons`、`auto-bind-coupons` |
| 我有哪些券 / 哪些快过期 | `references/coupon-wallet.md` | `query-my-coupons` |
| 这张券能省多少 / 这家店能用什么券 | `references/coupon-price.md` | `now-time-info`、`query-nearby-stores`、`query-store-coupons`、`calculate-price` |
| **我的积分 / 积分快过期 / 积分能换什么** | `references/points.md` | `query-my-account`、`mall-points-products` |
| 解析失败、字段看不懂、输出异常 | `references/parsing.md` | — |
| 接口报错、结果为空、数量不符 | `references/pitfalls.md` | — |

多意图并存时（例如「帮我领券，再看看积分」），**先做券再做积分**，两次独立输出，不要混成一段。

## 意图识别要点

- 出现「券」→ 券链路；出现「积分 / 麦享会 / 兑换」→ 积分链路。
- 「省多少」「划算」「值不值」且带具体餐品 → 走算价场景（`coupon-price.md`）。
- 只说「麦当劳有什么优惠」→ 先走 `coupon-claim.md`，可顺带提一句积分，但不要主动展开。
- 用户问的是**别的品牌**或**通用积分**（如信用卡积分、话费积分）时，不要触发本 Skill。

## 前置条件

依赖 `mcd-mcp` 连接器：

- 配置：`~/.workbuddy/mcp.json` 的 `mcd-mcp`（`type: streamablehttp`、`url: https://mcp.mcd.cn`、`headers.Authorization: Bearer <token>`）
- 工具不可用时，提示用户在 WorkBuddy 左下角「专家·技能·连接器 → 连接器」启用，**不要自行猜测或重装**
- Token 与用户麦当劳会员账号绑定，**属于敏感凭证，任何情况下不得输出、不得写入项目仓库**

## 输出风格

- 表格优先，一张券一行，不要长段落
- 日期统一 `MM-DD HH:mm`，跨年才补年份
- 券价格带 `¥` 保留两位小数；积分写作 `891.1 分`
- 报差异、报失败、报限制时说清楚，不要弱化
- 适度用标记（⚠️ 提醒 / ✅ 完成 / 💡 建议）提升可读性，但不要每行都加
