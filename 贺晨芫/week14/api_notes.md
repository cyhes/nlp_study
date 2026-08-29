# 巨量算数 API 采集 —— 领域知识 & 排错手册

本文件供 WorkBuddy 在使用 `douyin-keyword-scraper` skill 时参考，记录接口、鉴权、AES 与常见故障的处理方式。

## 1. 接口概况

- **Endpoint**：`https://trendinsight.oceanengine.com/api/open/index/get_multi_keyword_hot_trend`
- **方法**：`POST`，`Content-Type: application/json;charset=UTF-8`
- **请求体（JSON）**：

  | 字段 | 说明 |
  |------|------|
  | `keyword_list` | 关键词数组，单批上限约 5 个（超过需分批） |
  | `start_date` / `end_date` | 起止日期，格式 `YYYYMMDD`；接口返回区间内全部历史日数据 |
  | `app_name` | `aweme`(抖音) / `toutiao`(头条) / `hotsoon`(抖音火山版) / `ixigua`(西瓜) |
  | `region` | 留空=全国；可填省份/城市编码列表 |

- **响应**：外层为 JSON，业务数据在 **`data` 字段**中，且为 **Base64(AES 密文)**。解密后才是真实 JSON（含 `hot_list` / `search_hot_list` 等时间序列）。
- **两种接口形态**（本 skill 用 oceanengine 形态）：
  - `trendinsight.oceanengine.com`：需 `msToken` + `X-Bogus` 参数签名（本 skill 方案）。
  - `creator.douyin.com/api/v2/index/get_multi_keyword_hot_trend`：用 `sessionid` Cookie 鉴权，**无需 X-Bogus**，但有两个实测坑（见下）。完整可运行参考实现见工作区 `juliang_direct_post.py`（直连 + `AUTO_FALLBACK` 浏览器兜底）。

### 1.1 creator.douyin.com 变体实测要点（重要）
- **请求头**：`X-Csrf-Token` = `passport_csrf_token` Cookie 的值（不是 `x-secsdk-csrf-token`）；同源 Cookie 随请求自动带上 `sessionid`。
- **请求体（JSON）必填**：
  - `keyword_list`：**必须是 JSON 数组**（如 `["小米17Ultra",...]`）。传逗号拼接的字符串会触发 **HTTP 500**（服务端内部错误）。
  - `app_name`：**必填枚举**（`isIn` 校验），抖音=`"aweme"`；缺失直接 **422**。
  - `start_date` / `end_date`：`YYYYMMDD`，区间内返回全部日级数据（实测 180 天窗口完整不截断）。
- **响应**：`data` 为 Base64(AES-CBC 密文)，解密后顶层 `hot_list[]`；每项含 `keyword`（服务端会改写大小写/空白，如 `xiaomi17Ultra`→`xiaomi 17 ultra`）、`search_hot_list[]`（**搜索指数**）、`hot_list[]`（**综合指数**），元素为 `{datetime, index}`（`index` 是字符串）。
- **Cookie 来源**：浏览器登录 `https://creator.douyin.com` → 复制 `sessionid` + `passport_csrf_token` + `csrf_session_id`。

## 2. Cookie 提取步骤（必读）

1. 用浏览器**登录** `https://trendinsight.oceanengine.com`（巨量算数 / 算数指数页）。
2. 打开 DevTools → **Network** → 筛选 **XHR/fetch** → 触发一次关键词查询。
3. 在任意请求上右键 → **Copy** → **Copy Request Headers**，或直接看 Request Headers 里的 `Cookie` 整行。
4. 把整段 Cookie 字符串粘到 `scripts/fetch.py` 顶部的 `COOKIE = "..."` 配置块。
5. **必须包含 `msToken`**：脚本通过它生成 `X-Bogus` 并拼到 query；缺失会导致鉴权失败 / 风控页。

> Cookie 是登录态，会过期（几小时~几天不等）。过期后重新走上述步骤复制即可。

## 3. X-Bogus 签名

- 纯 Python 实现已在 `scripts/fetch.py` 的 `XBogus` 类中（来源 JohnserfSeed/TikTokDownload，Apache-2.0，已验证可用），**不要改动**。
- 生成方式：`X-Bogus` 作用于 `msToken=xxx` 这段 query，结果拼成 `&X-Bogus=xxxxx` 追加到 URL。
- 若站点改版导致 `X-Bogus` 校验失败（返回 401 / 签名错误），需从站点前端 JS 重新提取算法替换该类。

## 4. AES 解密参数

- 默认值（前端公开值，可能随版本变动）：

  | 模式 | key | iv |
  |------|-----|----|
  | CBC（默认） | `SjXbYTJb7zXoUToSicUL3A==`（Base64） | `OekMLjghRg8vlX/PemLc+Q==`（Base64） |
  | CFB（备用） | `anN2bXA2NjYsamlh`（明文） | `amlheW91LHFpYW53`（明文） |

- **如何重新提取 key/iv**：DevTools 在 JS 中搜 `decrypt` / `AES` / `CryptoJS`，在解密调用处下断点，取出 `key`、`iv`（常为 Base64 或明文字符串），替换 `fetch.py` 顶部 `AES_KEY_*` / `AES_IV_*`。
- CBC 解密后做 PKCS7 `unpad`；若填充异常则保留原样（容错）。
- 切换模式：改 `AES_MODE = "CBC"` → `"CFB"`。

## 5. 排错速查

| 现象 | 原因 | 处理 |
|------|------|------|
| `接口返回的不是 JSON（疑似反爬/风控页面）` | Cookie 无效/过期，缺 `msToken` | 重新按 §2 复制 Cookie |
| `响应缺少 data 字段` | 鉴权被拒 / 参数错误 | 检查 Cookie、时间窗口、app_name |
| `解密后不是合法 JSON` | AES_MODE/key/iv 不符 | 按 §4 重新提取 |
| HTTP 401 / 签名错误 | X-Bogus 失效 | 重新提取 X-Bogus 算法 |
| 数据为空 / 全 0 | 时间窗口无数据 或 `KEEP_ZERO_RECORDS=False` 过滤 | 调整 `--days`/`--start`/`--end` |
| 偶发单批失败 | 频率/网络 | 脚本已 catch 单批异常并继续，调大 `DELAY` |
| HTTP 422 `property app_name ... isIn` | creator 端点缺必填 `app_name` | 请求体加 `app_name:"aweme"`（或对应平台枚举） |
| HTTP 500（creator） | `keyword_list` 传成逗号字符串 | 改为 **JSON 数组** `["词1","词2"]` |

## 6. 合规与频率

- 仅用于学习 / 技术研究；遵守网站 ToS，不绕过登录、不商业滥用。
- 默认 `BATCH_SIZE=5`、`DELAY=1.5s`、`TIMEOUT=20s`；高频采集易被风控，按需调小批次或调大延迟。
- 分享脚本时提醒使用者：Cookie 属敏感登录态，需自行替换，勿外泄。
