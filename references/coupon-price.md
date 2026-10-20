# 场景 D：按门店算用券实付

> **何时读本文件**：用户说「用这张券能省多少」「这家店能用什么券」「用券后多少钱」。
> **不适用**：只想看券包走 `coupon-wallet.md`；只想领券走 `coupon-claim.md`。

这是唯一能算出「省多少钱」的路径，**必须确认门店在营业中**。

---

## 流程

1. 调 `now-time-info` 取服务器时间（不要用本地时间，避免时区偏差）。
2. 调 `query-nearby-stores`（`beType=1` 到店 / `beType=5` 得来速，`searchType=2` + `city` + `keyword`），取 `storeCode`、`businessStartTime`、`businessEndTime`。
3. **不在营业区间就停止算价**：告知最近门店的营业时间，请其营业时再查。此时 `calculate-price` 会返回 `60003 门店暂停营业`。
4. 调 `query-store-coupons`（`storeCode` + `orderType` + `beType`；外送/团餐需 `beCode`），拿到该门店**已生效**的可用券，含 `couponId`、`couponCode`、`products[].productCode`。
5. 对目标餐品调 `calculate-price` **两次**：
   - 不带券：`items: [{productCode, quantity}]`
   - 带券：`items: [{productCode, quantity, couponId, couponCode}]`
6. 比较两次的 `data.price`（单位：**分**），差值即真实省额；同时读 `data.enjoyed.realDiscount` 与 `promotionName`（若有）做校验。

输出：原价 → 用券价 → 省 X 元（Y%），并注明券名与有效期。

---

## 关键约束

- **`productCode` 必须按场景获取。** 到店、外送、团餐是三套独立 SKU 与价格体系，拿点餐菜单的 code 去算团餐价会报 `60006 商品已售罄或不可售`。
- **`query-store-coupons` 返回空不代表没券。** 它只返回「当前门店 + 当前订单类型 + 已过生效时间」的券；券常在 10:30 生效，上午早段为空是正常的。
- **已持有券未必能查到 `couponId`。** 若用户想用的券在门店可用券里找不到，如实说明拿不到券标识、无法完成带券算价，**不要编一个**。
- 券超过 4 张时，逐张试算会多次调用，先说明耗时再执行。
