# LinkFile 完整设计说明

## 0. 项目定位

**LinkFile** 是一个面向 **AI 文件传递、临时文件分享、个人直链发布** 的轻量文件上传与分享工具。

它不是传统网盘，而是一个：

> **CLI-first、BYOS、支持加密配置同步、支持自托管 Web/API 的文件分享系统。**

其中 **BYOS** 指：

> Bring Your Own Storage，用户自带存储。

LinkFile 的核心目标是：

1. 快速把文件分享给 AI / Agent / 脚本工具。
2. 临时把文件分享给他人下载。
3. 使用用户自己的 S3 / R2 / WebDAV / OneDrive / Cloudreve / local-server 存储。
4. CLI 不登录也能独立工作。
5. 登录 Web 后可以同步配置、管理文件、生成 LinkFile 域名分享。
6. 用户可使用官方 LinkFile 服务端，也可自行部署 Web/API 或纯 API。
7. 对存储方式配置提供不同安全级别。

一句话概括：

> **LinkFile 是一个面向 AI 工作流、临时下载和个人直链发布的轻量自带存储文件分享工具，提供离线优先的 CLI、可选 Web/API 服务端、加密配置同步，以及 LinkFile 在线分享能力。**

---

## 1. 核心设计原则

### 1.1 CLI First

CLI 是 LinkFile 的第一入口。CLI 必须能在**没有 Web 账户、没有服务端、没有登录状态**的情况下使用。

```bash
linkfile setup
linkfile storage add s3
linkfile storage add cloudreve
linkfile upload report.pdf --expire 24h
```

CLI 离线时应能完成：

1. 读取本地配置。
2. 上传文件到用户配置的远端存储后端。
3. 生成公开链接、临时直链或 Cloudreve 分享链接。
4. 维护本地文件索引。
5. 查看、下载、删除、管理本地记录。

### 1.2 Web/API 是增强能力，不是前置条件

Web/API 端用于提供更完整的管理能力：

1. 文件列表和文件夹管理。
2. 分享链接管理。
3. 用户账户、Token、设备管理。
4. 存储方式图形化配置。
5. 加密配置同步。
6. LinkFile 域名在线分享。
7. 下载日志和访问控制。
8. local-server 存储能力。

但 Web/API **不是** CLI 的必要条件。用户可以选择：

1. CLI Only。
2. API Only。
3. Web + API。
4. CLI + Web/API 同步。
5. 完整自托管部署。

### 1.3 用户可自行部署服务端

LinkFile 不强制用户使用官方服务。支持以下部署形态：

#### CLI Only

只使用本地 CLI，不部署 Web/API。适合个人快速上传到 S3-compatible 或 Cloudreve，并生成 `public_url`、临时直链或 Cloudreve 分享链接。

#### API Only

只部署 FastAPI 后端，不部署 Web 前端。适合脚本、自动化、SDK、Agent 服务集成。用户通过 CLI / Python SDK / HTTP API 使用 LinkFile。

#### Web + API

部署完整 Web 前端和 API 后端。适合个人或小团队作为完整文件分享平台使用。

#### Self-hosted

用户自行部署 LinkFile Web/API 服务端。自托管用户完全控制数据库、服务端主密钥、域名、存储配置和部署环境。在自托管场景下，**LinkFile Online Share** 的服务端托管加密能力由部署者自行控制，服务端主密钥、数据库和域名均归部署者管理。

### 1.4 不提供普通 CLI 本地目录作为正式存储方式

LinkFile 的核心目标是“上传后能分享”。普通 CLI 本机目录无法天然生成可供他人访问的分享链接，容易让用户误以为“上传到本地也可以分享”。

因此，LinkFile 不提供普通 CLI 本地目录作为正式 storage method。

如果需要本地磁盘存储，只保留 **local-server**：

- 文件存储在 LinkFile API 服务端所在机器的磁盘中；
- 由 LinkFile API、反向代理、`X-Accel-Redirect` 或 `X-Sendfile` 提供访问；
- 仅在 API Only、Web + API、自托管 Online Share 场景下可用；
- 不属于 Local Only 模式。

### 1.5 临时链接永不落库

这是 LinkFile 的全局安全原则：

> **LinkFile 永远不持久化保存临时直链。**

临时链接包括：

1. S3/R2/MinIO presigned URL。
2. OneDrive temporary download URL。
3. Cloudreve 临时直链，如果对应实例返回的是短期直链。
4. 其他一次性 direct URL。

这些链接只在需要时即时生成：

1. CLI 输出时即时生成。
2. 浏览器本地生成。
3. 服务端 redirect / proxy 请求生命周期中生成。

不会写入数据库，也不会同步到 Web。

### 1.6 不生成 AI Prompt 片段

LinkFile 面向 AI 文件分享，但不负责生成 AI 提示词。它只保证链接本身适合 AI / Agent / 脚本访问：

1. 无需登录。
2. 无需 JS。
3. 可直接下载。
4. 支持 HEAD。
5. 支持 Range。
6. `Content-Type` 正确。
7. `Content-Length` 正确。
8. `Content-Disposition` 正确。

---

## 2. 系统组成

LinkFile 完整体由四部分组成：

1. **FastAPI 后端**。
2. **Astro Web 前端**。
3. **Python Typer CLI**。
4. **Python SDK**。

推荐 Monorepo 结构：

```text
LinkFile/
├─ apps/
│  ├─ api/                  # FastAPI 后端
│  ├─ web/                  # Astro 前端
│  └─ cli/                  # Python Typer CLI
│
├─ packages/
│  ├─ py-core/              # storage、crypto、local index、config 等公共逻辑
│  └─ py-sdk/               # Python SDK / API client
│
├─ deploy/
│  ├─ docker/
│  ├─ compose/
│  ├─ nginx/
│  └─ systemd/
│
├─ scripts/
│  ├─ dev.sh
│  ├─ test.sh
│  ├─ lint.sh
│  └─ generate-openapi.sh
│
├─ .github/
│  └─ workflows/
│
├─ docker-compose.yml
├─ .env.example
├─ README.md
└─ LICENSE
```

> 建议将 S3、Cloudreve、WebDAV、加密、本地索引等通用逻辑放入 `packages/py-core`，CLI 和 SDK 共同复用，避免重复实现。

---

## 3. 三种工作模式

为了让用户心智简单，LinkFile 不把“凭证模式”和“分享模式”完全暴露给用户自由组合，而是收敛成三种工作模式。

### 3.1 Local Only：离线模式

#### 触发条件

**用户未登录 Web/API**。只要用户未登录 Web/API，CLI 就处于 **Local Only** 模式。

#### 配置位置

配置只存在本机：

```text
~/.config/linkfile/config.json
系统 keyring
~/.local/share/linkfile/index.sqlite3
```

#### 分享方式

Local Only 下，文件分享只能使用：

1. 自定义 S3 / R2 / OSS 域名的长期公开链接。
2. CLI 即时生成的临时直链。
3. Cloudreve 直链或 Cloudreve 分享链接。

例如长期公开链接：

```text
https://files.example.com/uploads/report.pdf
```

例如临时直链：

```text
https://storage.example.com/report.pdf?X-Amz-Signature=...
```

例如 Cloudreve 分享链接：

```text
https://cloudreve.example.com/s/abcdef
```

#### 服务端能力

服务端完全不参与：

1. 不保存 storage config。
2. 不保存临时链接。
3. 不生成 LinkFile 域名分享。
4. 不 redirect。
5. 不 proxy。
6. 不刷新临时链接。
7. 不支持 local-server。

Local Only 可以概括为：

> **LinkFile 是一个本地上传工具和直链生成器。**

### 3.2 E2EE Synced：端到端加密同步模式

#### 触发条件

用户登录 Web/API，并选择端到端加密。

#### 配置存储方式

Web/API 端保存：

1. `encrypted_storage_config`。
2. `key_id`。
3. 文件元数据。
4. 文件索引。
5. 分享记录元数据，可选。

密钥只在用户本地：

1. CLI。
2. 浏览器临时内存。
3. 系统 keyring。
4. 用户手动备份的 LinkFile Master Key。

服务端无法解密 storage config。

#### 分享方式

E2EE Synced 下，分享方式与 Local Only 基本一致：

1. 自定义 S3 / R2 / OSS 域名的长期公开链接。
2. CLI / 浏览器本地解密后即时生成的临时直链。
3. Cloudreve 直链或分享链接，由本地 CLI / 浏览器生成。

#### 服务端能力

服务端可以：

1. 保存加密后的 storage config。
2. 同步文件索引。
3. 展示文件列表。
4. 管理文件元数据。
5. 保存 `public_url` 或长期分享 URL，可选。

服务端不能：

1. 解密 storage config。
2. 生成底层临时链接。
3. 刷新 OneDrive 临时链接。
4. 代表用户调用 Cloudreve SDK。
5. 代理下载。
6. 隐藏源地址。
7. 保存临时链接。
8. 使用 local-server 作为用户文件存储。

E2EE Synced 可以概括为：

> **Web/API 是加密配置同步器和文件索引管理器，不是文件下载代理。**

### 3.3 LinkFile Online Share：在线分享模式

#### 触发条件

用户登录 Web/API，并选择普通加密 / 服务端托管加密。

#### 配置存储方式

Web/API 端加密保存 storage config。服务端数据库不保存明文配置，但服务端运行时具备解密并访问存储后端的能力。这意味着服务端可以：

1. 访问 S3 / R2 / WebDAV / OneDrive / Cloudreve。
2. 使用 local-server 存储文件到服务端磁盘。
3. 生成底层临时链接。
4. 调用 Cloudreve SDK 生成直链或分享链接。
5. 执行 redirect。
6. 执行 proxy。
7. 在用户离线时继续提供分享链接。

#### 分享方式

Online Share 下默认提供 LinkFile 域名链接：

```text
https://linkfile.example.com/s/abc123
https://linkfile.example.com/r/abc123
```

默认策略：

1. **默认使用 redirect**。
2. 用户要求隐藏源地址时使用 **proxy**。
3. 也可选择使用自定义 S3 / R2 / OSS 域名。
4. 如果底层是 Cloudreve，可由服务端生成 Cloudreve 直链 / 分享链接，再由 LinkFile redirect 或 proxy。
5. 如果底层是 local-server，可由 LinkFile API 或反向代理提供文件访问。

#### redirect 模式

流程：

```text
用户访问 LinkFile 链接
→ 服务端检查分享权限
→ 服务端即时生成底层临时链接或获取底层可访问 URL
→ 302 redirect
```

特点：

1. 服务端不承担大流量。
2. 最终可能暴露底层存储地址或 Cloudreve 地址。
3. 适合 S3 / R2 / OneDrive / Cloudreve 等可生成临时下载 URL 或分享 URL 的存储。
4. 临时链接只在本次请求中生成，不落库。

#### proxy 模式

流程：

```text
用户访问 LinkFile 链接
→ 服务端检查分享权限
→ 服务端访问底层存储
→ 服务端流式返回文件
```

特点：

1. 不暴露源地址。
2. 全程使用 LinkFile 域名。
3. 支持访问控制、下载次数、日志、Range。
4. 服务端承担带宽和性能压力。
5. 对 local-server，生产环境推荐通过 `X-Accel-Redirect` 或 `X-Sendfile` 将实际文件传输交给 Nginx / Caddy。

### 3.4 三种模式对比

| 状态 | 模式 | 服务端能否访问存储 | 分享方式 | 是否支持 LinkFile 域名分享 | 是否隐藏源地址 | 是否支持 local-server |
|---|---|---:|---|---:|---:|---:|
| 未登录 | Local Only | 否 | 存储域名 / 本地临时直链 / Cloudreve 链接 | 否 | 否 | 否 |
| 登录 + E2EE | E2EE Synced | 否 | 存储域名 / 本地临时直链 / 本地生成 Cloudreve 链接 | 否或受限 | 否 | 否 |
| 登录 + 普通加密 | LinkFile Online Share | 是 | LinkFile redirect / proxy / 存储域名 / Cloudreve 链接 | 是 | proxy 时支持 | 是 |

最终语义：

> **离线就是本地工具；E2EE 就是安全同步；普通加密就是完整在线分享。**

---

## 4. LinkFile Online Share 的安全边界

**Online Share 的便利性**来自服务端托管密钥能力。必须明确：

> **LinkFile Online Share 不能从密码学上防止服务端查看 storage config。**

因为服务端必须能在用户离线时生成临时链接、刷新 OneDrive token、调用 Cloudreve SDK、执行 redirect 或 proxy。如果用户不希望服务端具备任何访问存储的能力，应使用 Local Only 或 E2EE Synced。

### 4.1 Online Share 的风险降低设计

Online Share 使用服务端托管加密。安全规则如下：

1. **数据库中不保存明文 storage config**，服务端只在运行时解密使用。
2. **每个用户拥有独立的用户数据密钥**。该密钥随用户数据加密保存。服务端需要使用主密钥解密用户数据密钥后，才能读取该用户的 storage config。主密钥支持定时轮换，解密过程仅在服务端内存中进行。
3. **服务端日志、错误信息和审计记录**中永不输出 secret、token、完整临时直链等敏感内容。
4. **引导用户使用受限凭证**，例如只允许访问指定 bucket/prefix，或 Cloudreve 中专用于 LinkFile 的账户 / 目录。

### 4.2 Online Share 的密钥结构

推荐结构：

```text
Server Master Key
  ↓ 解密
User Data Key
  ↓ 解密
Storage Config
```

数据库保存：

```text
encrypted_user_data_key
storage_config_ciphertext
storage_config_nonce
key_id
encryption_metadata
```

数据库不保存：

1. 明文 storage config。
2. 明文用户数据密钥。
3. 明文主密钥。
4. 临时直链。

### 4.3 主密钥轮换

主密钥应支持轮换。流程：

1. 使用旧主密钥解密 `encrypted_user_data_key`。
2. 使用新主密钥重新加密 `user_data_key`。
3. 更新 `key_id`。
4. 全过程在内存中完成。
5. storage config 本身无需逐条解密重加密，除非用户数据密钥也轮换。

### 4.4 新 CLI 登录时的密钥分发

在 LinkFile Online Share 模式下，新设备登录后，服务端可以向已认证、已授权的 CLI 分发用户数据密钥或等价解密能力。推荐采用**设备公钥封装方式**，而不是裸传密钥。

流程：

```text
1. 新 CLI 本地生成设备密钥对：device_public_key / device_private_key
2. CLI 登录 Web/API 账户
3. CLI 将 device_public_key 上传给服务端
4. 服务端验证用户身份和设备授权
5. 服务端使用主密钥解密该用户的用户数据密钥
6. 服务端使用 device_public_key 加密用户数据密钥
7. CLI 收到 encrypted_user_data_key_for_device
8. CLI 用本地 device_private_key 解密，得到用户数据密钥
9. CLI 将用户数据密钥或设备私钥保存到系统 keyring
10. CLI 拉取 encrypted_storage_config，并在本地解密使用
```

三种模式下的新设备行为：

| 模式 | 新 CLI 登录后能否从服务端拿到可解密配置的密钥 |
|---|---:|
| Local Only | 不能，服务端没有配置 |
| E2EE Synced | 不能，必须用户手动导入 LMK |
| LinkFile Online Share | 可以，服务端可向已授权设备安全分发用户数据密钥 |

---

## 5. CLI 登录与服务端地址

CLI 登录时支持指定服务端地址：

```bash
linkfile login --server https://my-linkfile.example.com
```

也支持简写：

```bash
linkfile login -s https://my-linkfile.example.com
```

如果用户不指定 `--server`，默认使用 LinkFile 官方服务端。例如：

```bash
linkfile login
```

等价于：

```bash
linkfile login --server https://api.linkfile.nyaku.moe
```

具体官方域名可在正式发布前确定，这里以 `https://api.linkfile.nyaku.moe` 作为占位。

### 5.1 Token 登录

```bash
linkfile login --server https://my-linkfile.example.com --token lf_xxxxx
```

如果不写 `--server`：

```bash
linkfile login --token lf_xxxxx
```

等价于：

```bash
linkfile login --server https://api.linkfile.nyaku.moe --token lf_xxxxx
```

### 5.2 浏览器登录

```bash
linkfile login --server https://my-linkfile.example.com --browser
```

如果不写 `--server`：

```bash
linkfile login --browser
```

默认使用官方服务端。

### 5.3 登录后写入配置

登录成功后，CLI 将实际使用的服务端地址写入本地 `config.json`：

```json
{
  "server": {
    "url": "https://api.linkfile.nyaku.moe",
    "enabled": true,
    "name": "LinkFile Official"
  },
  "auth": {
    "token": "lf_xxxxx",
    "token_type": "api_token"
  }
}
```

自托管用户登录后则可能是：

```json
{
  "server": {
    "url": "https://linkfile.my-domain.com",
    "enabled": true,
    "name": "My LinkFile Server"
  },
  "auth": {
    "token": "lf_xxxxx",
    "token_type": "api_token"
  }
}
```

### 5.4 相关配置命令

查看当前服务端：

```bash
linkfile config get server.url
```

切换服务端但不登录：

```bash
linkfile config set server.url https://my-linkfile.example.com
```

退出登录但保留服务端地址：

```bash
linkfile logout
```

退出登录并禁用在线模式：

```bash
linkfile logout --disable-server
```

---

## 6. 分享链接类型

LinkFile 中建议区分多种交付方式。

### 6.1 public_url

长期公开链接。例如：

```text
https://files.example.com/uploads/report.pdf
```

适合：

1. S3 / R2 / OSS + 自定义域名。
2. 公开 bucket。
3. CDN 域名。
4. 长期可访问资源。

特点：

1. 长期有效。
2. 不需要服务端凭证。
3. 不能精确控制过期。
4. 不能严格限制下载次数。
5. 不隐藏最终域名，但可以用自定义域名美化。

### 6.2 presigned_url

临时直链。例如：

```text
https://storage.example.com/file.pdf?X-Amz-Signature=...
```

适合：

1. S3。
2. R2。
3. MinIO。
4. 对象存储。
5. 部分 OneDrive 临时下载链接。

特点：

1. 可过期。
2. 不需要 LinkFile 代理流量。
3. 会暴露最终存储链接。
4. 过期后需要重新生成。
5. 不落库。

### 6.3 cloudreve_direct_url

Cloudreve 返回的直链。适合已经部署 Cloudreve 的用户通过 LinkFile CLI 快速上传并分享文件。

特点：

1. 由 Cloudreve 实例提供。
2. 是否长期有效、是否需要登录、是否支持过期取决于 Cloudreve 实例配置和 SDK 能力。
3. LinkFile 将 Cloudreve 视为普通 storage backend，不把它视为 LinkFile Web 的替代品。

### 6.4 cloudreve_share_url

Cloudreve 分享链接。例如：

```text
https://cloudreve.example.com/s/abcdef
```

特点：

1. 由 Cloudreve SDK 创建。
2. 适合 Local Only v0.1 快速实现网盘式分享能力。
3. 是否支持过期、密码、目录分享取决于 Cloudreve 版本和 SDK 能力。

### 6.5 linkfile_redirect

LinkFile 域名跳转链接。例如：

```text
https://linkfile.example.com/r/abc123
```

流程：

```text
检查分享是否有效
→ 检查密码 / 次数 / 过期时间
→ 即时生成底层 direct URL 或获取底层分享 URL
→ 302 redirect
```

特点：

1. 用户最初看到的是 LinkFile 链接。
2. 服务端不承担大流量。
3. 最终会暴露底层下载地址。
4. 需要 LinkFile Online Share。
5. 临时链接不落库。

### 6.6 linkfile_proxy

LinkFile 域名代理链接。例如：

```text
https://linkfile.example.com/r/abc123
```

流程：

```text
检查分享是否有效
→ 访问底层存储
→ 服务端流式返回文件
```

特点：

1. 不暴露源地址。
2. 全程使用 LinkFile 域名。
3. 支持访问控制、限次、日志、Range。
4. 服务端承担带宽和性能压力。
5. 需要 LinkFile Online Share。

### 6.7 local_server_public_url

local-server 的长期公开链接。例如：

```text
https://linkfile.example.com/files/report.pdf
```

特点：

1. 文件实际保存在 LinkFile 服务端磁盘。
2. URL 由 LinkFile API 或反向代理提供。
3. 仅适用于 API Only / Web + API / Self-hosted 场景。
4. 如果需要访问控制，推荐通过 LinkFile `/r/{token}` 入口进行权限检查后再交给反向代理传输。

---

## 7. 存储方式设计

### 7.1 支持的存储方式

完全体支持：

1. S3-compatible。
2. Cloudreve。
3. local-server。
4. Cloudflare R2。
5. AWS S3。
6. MinIO。
7. Backblaze B2。
8. WebDAV。
9. OneDrive。
10. Google Drive。
11. 阿里云 OSS。
12. 腾讯 COS。
13. 七牛云。
14. 又拍云。

推荐实现顺序：

```text
v0.1: S3-compatible + Cloudreve
v0.2: local-server + Cloudflare R2 / MinIO 优化
v0.3: WebDAV
v0.4: OneDrive
v0.5: Google Drive / 其他对象存储
```

### 7.2 Storage Method 通用字段

```text
id
user_id，可选
name
type
mode
is_default
created_at
updated_at
```

其中 `type` 可以是：

```text
s3
cloudreve
local-server
webdav
onedrive
google_drive
```

### 7.3 统一 StorageBackend 抽象

Cloudreve 在 LinkFile 中是一种普通 storage backend，地位类似 S3-compatible。区别在于：S3 通过对象存储 API 操作，Cloudreve 通过 Cloudreve SDK 操作。

```python
class StorageBackend(Protocol):
    def upload_file(self, local_path: Path, remote_path: str) -> UploadResult:
        ...

    def download_file(self, remote_path: str, local_path: Path) -> None:
        ...

    def delete_file(self, remote_path: str) -> None:
        ...

    def list_files(self, remote_dir: str) -> list[RemoteFile]:
        ...

    def get_direct_url(
        self,
        remote_path: str,
        expire: str | None = None,
    ) -> DirectUrlResult | None:
        ...

    def create_share(
        self,
        remote_path: str,
        expire: str | None = None,
        password: str | None = None,
    ) -> ShareResult | None:
        ...
```

v0.1 要求：

- **S3-compatible**：必须实现 `upload_file`、`download_file`、`delete_file`、`list_files`、`get_direct_url`。`create_share` 可为空。
- **Cloudreve**：必须实现 `upload_file`、`download_file`、`delete_file`、`list_files`。如果 SDK 支持直链，则实现 `get_direct_url`；如果 SDK 支持分享链接，则实现 `create_share`。

### 7.4 Storage capabilities

每个 storage backend 应暴露能力，CLI / API 根据能力决定上传后输出什么。

```python
class StorageCapabilities(BaseModel):
    can_upload: bool
    can_download: bool
    can_list: bool
    can_delete: bool
    can_generate_public_url: bool
    can_generate_temporary_url: bool
    can_create_share: bool
    can_proxy: bool
```

示例：

| Storage method | can_generate_public_url | can_generate_temporary_url | can_create_share | can_proxy |
|---|---:|---:|---:|---:|
| S3-compatible | 取决于 public_base_url | 是 | 否 | Online Share 时可由服务端 proxy |
| Cloudreve | 取决于实例能力 | 取决于实例能力 | 是 | Online Share 时可由服务端 proxy |
| local-server | 取决于 public_base_url | 否 | 是 | 是 |

### 7.5 S3-compatible 配置

```json
{
  "type": "s3",
  "name": "my-r2",
  "config": {
    "endpoint_url": "https://xxxx.r2.cloudflarestorage.com",
    "region": "auto",
    "bucket": "linkfile",
    "access_key_id": "...",
    "secret_access_key": "...",
    "prefix": "uploads/",
    "public_base_url": "https://files.example.com",
    "use_path_style": false
  }
}
```

字段说明：

- `endpoint_url`：S3-compatible API endpoint。
- `region`：AWS / R2 / MinIO 所需 region。
- `bucket`：bucket 名称。
- `access_key_id` / `secret_access_key`：存储访问凭证。
- `prefix`：上传对象前缀。
- `public_base_url`：自定义公开域名，可用于长期 public_url。
- `use_path_style`：是否使用 path-style endpoint。

### 7.6 Cloudreve 配置

Cloudreve 在 LinkFile 中是一种普通 storage backend。LinkFile 不把 Cloudreve 视为独立 Web 端，而是通过 Cloudreve SDK 调用用户指定的 Cloudreve 实例，用于上传、下载、删除、列目录、获取直链或创建分享链接。

```json
{
  "id": "my-cloudreve",
  "name": "My Cloudreve",
  "type": "cloudreve",
  "is_default": false,
  "config": {
    "base_url": "https://cloudreve.example.com",
    "auth_type": "password",
    "username": "user@example.com",
    "password_ref": "keyring:cloudreve:my-cloudreve",
    "root_path": "/LinkFile",
    "default_expire": "24h",
    "prefer_direct_url": true
  }
}
```

相关命令：

```bash
linkfile storage add cloudreve
linkfile storage test my-cloudreve
linkfile upload report.pdf --storage my-cloudreve --expire 24h
```

在 Local Only 模式下，CLI 直接调用 Cloudreve SDK 完成文件上传和链接生成，不经过 LinkFile Web/API。

### 7.7 local-server 配置

`local-server` 是 LinkFile 自托管 Web/API 服务端使用的本地磁盘存储方式。

它不是 CLI 本机目录存储，而是指：

> 文件保存在 LinkFile API 服务端所在机器的指定目录中，并由 LinkFile API 或反向代理通过服务端域名提供访问。

因此，`local-server` 只在 API Only / Web + API / Self-hosted 场景下可用，不适用于纯 CLI Local Only 模式。

```json
{
  "id": "server-local-main",
  "name": "Server Local Storage",
  "type": "local-server",
  "is_default": true,
  "config": {
    "root_path": "/var/lib/linkfile/storage",
    "public_base_url": "https://linkfile.example.com/files",
    "serve_mode": "api"
  }
}
```

字段说明：

- `root_path`：文件实际存储在服务端磁盘上的路径。
- `public_base_url`：可选。若配置，则可以直接生成长期公开链接。
- `serve_mode`：`api`、`nginx`、`hybrid`。

`serve_mode` 说明：

- `api`：由 LinkFile API 读取文件并返回。
- `nginx`：由 Nginx / Caddy 等反向代理直接暴露静态文件。
- `hybrid`：小文件走 API，大文件走反向代理或 `X-Accel-Redirect` / `X-Sendfile`。

生产环境推荐：

```text
用户访问 /r/abc123
→ LinkFile 检查权限
→ 返回 X-Accel-Redirect / X-Sendfile
→ Nginx / Caddy 发送本地文件
```

### 7.8 S3、Cloudreve、local-server 对比

| Storage method | 存储位置 | 底层操作方式 | 链接生成方式 | 是否适合 CLI Local Only |
|---|---|---|---|---:|
| S3-compatible | 对象存储 | S3 API | public_url / presigned_url | 是 |
| Cloudreve | Cloudreve 实例 | Cloudreve SDK | Cloudreve 直链 / Cloudreve 分享链接 | 是 |
| local-server | LinkFile 服务端磁盘 | LinkFile API / 反向代理 | linkfile_redirect / linkfile_proxy / public_url | 否 |

### 7.9 WebDAV 配置

```json
{
  "type": "webdav",
  "name": "my-webdav",
  "config": {
    "base_url": "https://dav.example.com",
    "username": "...",
    "password": "...",
    "root_path": "/linkfile",
    "public_base_url": null
  }
}
```

### 7.10 OneDrive 配置

```json
{
  "type": "onedrive",
  "name": "my-onedrive",
  "config": {
    "tenant": "common",
    "client_id": "...",
    "refresh_token": "...",
    "drive_id": "...",
    "root_path": "/LinkFile"
  }
}
```

OneDrive 特殊点：

1. 长期稳定的 LinkFile 域名分享几乎必须使用 Online Share。
2. 服务端需要 refresh_token 刷新 access_token。
3. 服务端需要通过 Microsoft Graph 获取临时下载地址。
4. E2EE 模式下服务端无法刷新 OneDrive 链接。

---

## 8. 文件模型

### 8.1 File Entry

```text
id
owner_id
name
original_name
mime_type
size
sha256
storage_method_id
storage_type
storage_key
folder_id
public_url
thumbnail_url
metadata_json
created_at
updated_at
deleted_at
```

说明：

- `storage_method_id`：文件所在的存储方式。
- `storage_type`：例如 `s3`、`cloudreve`、`local-server`、`webdav`。
- `storage_key`：文件在底层存储中的 key/path。
- `public_url`：可选，长期公开链接或长期分享链接。
- `thumbnail_url`：可选，缩略图链接。
- `metadata_json`：扩展元数据。

### 8.2 Folder Entry

```text
id
owner_id
name
parent_id
created_at
updated_at
```

文件夹可以是逻辑文件夹，不一定等于底层存储中的真实目录。

### 8.3 Share Link

```text
id
owner_id
file_id
folder_id
token
share_type
delivery_mode
expires_at
password_hash
max_downloads
download_count
allow_preview
created_at
revoked_at
```

其中：

- `share_type`：`page`、`raw`、`direct`。
- `delivery_mode`：`public_url`、`presigned_url`、`cloudreve_direct_url`、`cloudreve_share_url`、`local_server_public_url`、`linkfile_redirect`、`linkfile_proxy`。

注意：

- `presigned_url` 本身不落库。
- 临时 Cloudreve 直链本身不落库。
- `delivery_mode` 只记录分享交付方式。

### 8.4 本地索引字段建议

本地 `files` 表建议包括：

```text
id
name
original_path
storage_method_id
storage_type
storage_key
size
mime_type
sha256
access_url_type
access_url_expires_at
created_at
updated_at
synced_at
remote_file_id
```

对于临时链接，不保存完整 `access_url`。对于长期 public_url 或 Cloudreve 永久分享链接，可以按需记录。

---

## 9. 核心功能说明

### 9.1 文件上传

支持：

1. 单文件上传。
2. 多文件上传。
3. 文件夹上传。
4. 文件夹打包为 zip 上传。
5. 保持目录结构上传。
6. CLI 上传。
7. Web 上传。
8. SDK 上传。
9. 拖拽上传。

CLI 示例：

```bash
linkfile upload report.pdf
linkfile upload image.png --expire 24h
linkfile upload ./dist --zip --expire 7d
linkfile upload ./assets --recursive
linkfile upload report.pdf --storage my-cloudreve --expire 24h
```

### 9.2 文件分享

支持：

1. 分享页链接。
2. Raw 下载链接。
3. Direct 直链。
4. Cloudreve 分享链接。
5. Markdown 链接。
6. 二维码。

链接控制：

1. 过期时间。
2. 访问密码。
3. 最大下载次数。
4. 一次性链接。
5. 撤销链接。
6. 重新生成分享 token。
7. 访问日志。
8. 下载次数统计。

### 9.3 文件管理

支持：

1. 查看文件列表。
2. 查看文件详情。
3. 搜索文件。
4. 按名称、大小、上传时间、下载次数排序。
5. 按存储方式过滤。
6. 按 MIME 类型过滤。
7. 创建文件夹。
8. 移动文件。
9. 重命名文件。
10. 下载文件。
11. 删除文件。
12. 批量删除。
13. 批量生成分享链接。
14. 查看真实存储位置。

### 9.4 预览与缩略图

完全体支持：

1. 图片缩略图。
2. PDF 预览。
3. 文本预览。
4. Markdown 预览。
5. 代码高亮。
6. 视频封面。
7. 音频信息。
8. 压缩包内容列表。

不同模式下能力不同：

- **Local Only**：CLI 可本地生成缩略图，可选上传到 S3 / Cloudreve。
- **E2EE Synced**：CLI / 浏览器本地生成缩略图更合适。
- **LinkFile Online Share**：服务端可以异步生成缩略图。

### 9.5 账户与安全

Web 在线模式支持：

1. 注册、登录、退出登录。
2. 修改昵称、头像、邮箱、密码。
3. 删除账户。
4. 2FA。
5. 登录设备管理。
6. 登录历史。
7. API Token 管理。

Token scope：

```text
files:read
files:write
files:delete
shares:read
shares:write
storage:read
storage:write
user:read
```

---

## 10. CLI 设计

### 10.1 技术栈

```text
Python
Typer
Rich
httpx
pydantic
platformdirs
keyring
boto3 / aioboto3
cloudreve-sdk
webdav client
cryptography
textual，可选
```

### 10.2 CLI 目录结构

```text
apps/cli/
├─ linkfile_cli/
│  ├─ __init__.py
│  ├─ main.py
│  ├─ commands/
│  │  ├─ setup.py
│  │  ├─ upload.py
│  │  ├─ files.py
│  │  ├─ shares.py
│  │  ├─ storage.py
│  │  ├─ auth.py
│  │  ├─ config.py
│  │  ├─ sync.py
│  │  ├─ crypto.py
│  │  └─ tui.py
│  ├─ core/
│  │  ├─ config.py
│  │  ├─ context.py
│  │  ├─ output.py
│  │  ├─ errors.py
│  │  ├─ clipboard.py
│  │  └─ mode.py
│  ├─ client/
│  │  ├─ api_client.py
│  │  └─ auth.py
│  └─ tests/
│     ├─ test_upload.py
│     ├─ test_config.py
│     ├─ test_crypto.py
│     └─ test_local_index.py
```

通用逻辑建议放在 `packages/py-core`：

```text
packages/py-core/
├─ linkfile_core/
│  ├─ crypto/
│  ├─ local/
│  ├─ storage/
│  │  ├─ base.py
│  │  ├─ registry.py
│  │  ├─ s3.py
│  │  ├─ cloudreve.py
│  │  ├─ local_server.py
│  │  ├─ webdav.py
│  │  └─ errors.py
│  └─ utils/
```

### 10.3 CLI 配置文件

位置：

```text
Linux/macOS:
~/.config/linkfile/config.json

Windows:
%APPDATA%\LinkFile\config.json
```

示例：

```json
{
  "server": {
    "url": "https://api.linkfile.nyaku.moe",
    "enabled": false,
    "name": "LinkFile Official"
  },
  "auth": {
    "token": null,
    "token_type": null
  },
  "defaults": {
    "storage_method": "my-r2",
    "expire": "24h",
    "format": "text",
    "copy": false
  },
  "crypto": {
    "mode": "local",
    "default_key_id": null,
    "key_store": "system_keyring"
  },
  "device": {
    "device_id": null,
    "device_private_key_ref": null
  },
  "storage_methods": [
    {
      "id": "my-r2",
      "name": "My Cloudflare R2",
      "type": "s3",
      "is_default": true,
      "config": {
        "endpoint_url": "https://xxxx.r2.cloudflarestorage.com",
        "region": "auto",
        "bucket": "linkfile",
        "access_key_id": "xxxx",
        "secret_access_key": "xxxx",
        "prefix": "uploads/",
        "public_base_url": "https://files.example.com",
        "use_path_style": false
      }
    },
    {
      "id": "my-cloudreve",
      "name": "My Cloudreve",
      "type": "cloudreve",
      "is_default": false,
      "config": {
        "base_url": "https://cloudreve.example.com",
        "auth_type": "password",
        "username": "user@example.com",
        "password_ref": "keyring:cloudreve:my-cloudreve",
        "root_path": "/LinkFile",
        "default_expire": "24h",
        "prefer_direct_url": true
      }
    }
  ],
  "local_index": {
    "enabled": true,
    "path": "~/.local/share/linkfile/index.sqlite3"
  },
  "sync": {
    "enabled": false,
    "last_sync_at": null,
    "strategy": "manual"
  }
}
```

### 10.4 CLI 命令设计

#### 初始化 / 设置

```bash
linkfile setup
```

含义：

1. 配置本机 LinkFile 环境。
2. 创建 `config.json`。
3. 创建 `index.sqlite3`。
4. 设置默认 storage method。
5. 可选登录 Web/API。
6. 可选初始化 E2EE 主密钥。

`linkfile setup` 不是强制前置命令。如果用户直接执行如下命令，CLI 可以自动创建必要目录和默认配置：

```bash
linkfile storage add s3
linkfile storage add cloudreve
linkfile upload report.pdf
```

#### 登录

默认连接官方服务端：

```bash
linkfile login
```

等价于：

```bash
linkfile login --server https://api.linkfile.nyaku.moe
```

指定自托管服务端：

```bash
linkfile login --server https://linkfile.my-domain.com
```

Token 登录：

```bash
linkfile login --server https://linkfile.my-domain.com --token lf_xxxxx
```

浏览器登录：

```bash
linkfile login --server https://linkfile.my-domain.com --browser
```

#### 退出登录

```bash
linkfile logout
linkfile logout --disable-server
```

#### 配置存储

```bash
linkfile storage add s3
linkfile storage add cloudreve
linkfile storage list
linkfile storage test my-r2
linkfile storage test my-cloudreve
linkfile storage set-default my-r2
linkfile storage remove my-r2
```

`local-server` 不属于 CLI Local Only 存储方式，不建议通过离线 CLI 添加。它应在 API/Web 端或自托管配置中添加。

#### 上传文件

```bash
linkfile upload report.pdf
linkfile upload report.pdf --storage my-r2
linkfile upload report.pdf --storage my-cloudreve
linkfile upload report.pdf --expire 24h
linkfile upload report.pdf --raw
linkfile upload report.pdf --format markdown
linkfile upload report.pdf --format json
linkfile upload report.pdf --copy
```

#### 上传文件夹

```bash
linkfile upload ./dist --zip --expire 7d
linkfile upload ./assets --recursive
```

#### 文件管理

```bash
linkfile list
linkfile list --local
linkfile list --remote
linkfile info file_xxx
linkfile download file_xxx ./downloads/
linkfile delete file_xxx
linkfile delete file_xxx --index-only
linkfile delete file_xxx --with-object
```

#### 同步

```bash
linkfile sync
linkfile sync pull
linkfile sync push
linkfile sync status
```

#### 加密密钥管理

```bash
linkfile crypto status
linkfile crypto init --mode e2ee
linkfile crypto export
linkfile crypto import ./linkfile-master-key.txt
linkfile crypto rotate
linkfile crypto reencrypt
```

### 10.5 CLI 输出格式

支持：

- `text`
- `json`
- `markdown`
- `raw`
- `share`

**text**：

```text
File: report.pdf
Share: https://linkfile.example.com/s/lf_abc123
Raw:   https://linkfile.example.com/r/lf_abc123
Expire: 24h
```

**Cloudreve Local Only 输出示例**：

```text
File: report.pdf
Storage: my-cloudreve
Share: https://cloudreve.example.com/s/abcdef
Expire: 24h
```

**markdown**：

```markdown
[report.pdf](https://linkfile.example.com/r/lf_abc123)
```

**json**：

```json
{
  "file_id": "file_xxx",
  "name": "report.pdf",
  "size": 2410081,
  "mime_type": "application/pdf",
  "storage_method_id": "my-cloudreve",
  "storage_type": "cloudreve",
  "storage_key": "/LinkFile/report.pdf",
  "share_url": "https://cloudreve.example.com/s/abcdef",
  "raw_url": null,
  "public_url": null,
  "expires_at": "2026-04-25T12:00:00Z"
}
```

Local Only 下如果输出临时直链，CLI 可以显示：

```text
Temporary URL:
https://storage.example.com/file.pdf?X-Amz-Signature=...

This temporary URL is not stored by LinkFile.
```

---

## 11. FastAPI 后端设计

### 11.1 后端职责

FastAPI 后端负责在线模式：

1. 用户认证。
2. API Token 管理。
3. 文件元数据管理。
4. 文件上传协调。
5. 分享链接生成。
6. Raw 下载 redirect / proxy。
7. Storage Method 管理。
8. Storage Method 加密存储。
9. 用户数据密钥管理。
10. 设备密钥分发。
11. 同步接口。
12. 访问日志。
13. 下载次数限制。
14. 密码访问。
15. OpenAPI 文档。
16. local-server 文件服务。

### 11.2 后端目录结构

```text
apps/api/
├─ linkfile_api/
│  ├─ __init__.py
│  ├─ main.py
│  ├─ core/
│  │  ├─ config.py
│  │  ├─ security.py
│  │  ├─ database.py
│  │  ├─ logging.py
│  │  ├─ exceptions.py
│  │  └─ dependencies.py
│  ├─ crypto/
│  │  ├─ envelope.py
│  │  ├─ key_manager.py
│  │  ├─ device_key.py
│  │  ├─ server_key_rotation.py
│  │  └─ errors.py
│  ├─ models/
│  ├─ schemas/
│  ├─ api/
│  │  ├─ router.py
│  │  └─ routes/
│  │     ├─ auth.py
│  │     ├─ users.py
│  │     ├─ devices.py
│  │     ├─ tokens.py
│  │     ├─ storage_methods.py
│  │     ├─ files.py
│  │     ├─ folders.py
│  │     ├─ shares.py
│  │     ├─ download.py
│  │     ├─ sync.py
│  │     ├─ crypto.py
│  │     └─ health.py
│  ├─ services/
│  │  ├─ auth_service.py
│  │  ├─ user_service.py
│  │  ├─ device_service.py
│  │  ├─ token_service.py
│  │  ├─ file_service.py
│  │  ├─ folder_service.py
│  │  ├─ share_service.py
│  │  ├─ storage_service.py
│  │  ├─ storage_crypto_service.py
│  │  ├─ sync_service.py
│  │  ├─ thumbnail_service.py
│  │  └─ audit_service.py
│  ├─ storage/
│  │  ├─ base.py
│  │  ├─ registry.py
│  │  ├─ s3.py
│  │  ├─ cloudreve.py
│  │  ├─ local_server.py
│  │  ├─ webdav.py
│  │  ├─ onedrive.py
│  │  └─ errors.py
│  ├─ tasks/
│  └─ utils/
├─ alembic/
├─ pyproject.toml
├─ alembic.ini
├─ .env.example
├─ Dockerfile
└─ README.md
```

### 11.3 重点模块

- **`main.py`**：FastAPI 入口。
- **`core/config.py`**：配置管理。
- **`crypto/envelope.py`**：Envelope encryption，负责生成/解包用户数据密钥。
- **`crypto/device_key.py`**：设备密钥封装及管理。
- **`crypto/server_key_rotation.py`**：主密钥轮换。
- **`services/storage_crypto_service.py`**：处理存储配置加密逻辑。
- **`services/share_service.py`**：负责创建分享、验证过期、密码等，不保存临时 URL。
- **`storage/cloudreve.py`**：Online Share 下通过 Cloudreve SDK 调用 Cloudreve 实例。
- **`storage/local_server.py`**：处理服务端磁盘文件存储、权限检查和传输策略。

---

## 12. 后端 API 设计

### 12.1 Auth API

```text
POST /api/auth/register
POST /api/auth/login
POST /api/auth/logout
GET  /api/auth/me
POST /api/auth/refresh
```

说明：不提供 `unlock-vault` / `lock-vault`，因为 Online Share 模式下服务端始终具备运行时解密能力。

### 12.2 Device API

用于 Online Share 下的新 CLI 登录和设备密钥分发。

```text
GET    /api/devices
POST   /api/devices/register
POST   /api/devices/{id}/approve
DELETE /api/devices/{id}
POST   /api/devices/{id}/wrapped-user-key
```

### 12.3 Token API

```text
GET    /api/tokens
POST   /api/tokens
DELETE /api/tokens/{token_id}
```

### 12.4 Storage Method API

```text
GET    /api/storage-methods
POST   /api/storage-methods
GET    /api/storage-methods/{id}
PATCH  /api/storage-methods/{id}
DELETE /api/storage-methods/{id}
POST   /api/storage-methods/{id}/test
POST   /api/storage-methods/{id}/reencrypt
```

Online Share 创建 S3 请求示例：

```json
{
  "name": "My R2",
  "type": "s3",
  "encryption_mode": "server_managed",
  "config": {
    "endpoint_url": "https://xxxx.r2.cloudflarestorage.com",
    "region": "auto",
    "bucket": "linkfile",
    "access_key_id": "...",
    "secret_access_key": "...",
    "prefix": "uploads/",
    "public_base_url": "https://files.example.com",
    "use_path_style": false
  }
}
```

Online Share 创建 Cloudreve 请求示例：

```json
{
  "name": "My Cloudreve",
  "type": "cloudreve",
  "encryption_mode": "server_managed",
  "config": {
    "base_url": "https://cloudreve.example.com",
    "auth_type": "password",
    "username": "user@example.com",
    "password": "...",
    "root_path": "/LinkFile",
    "prefer_direct_url": true
  }
}
```

创建 local-server 请求示例：

```json
{
  "name": "Server Local Storage",
  "type": "local-server",
  "encryption_mode": "server_managed",
  "config": {
    "root_path": "/var/lib/linkfile/storage",
    "public_base_url": "https://linkfile.example.com/files",
    "serve_mode": "hybrid"
  }
}
```

E2EE 创建请求示例：

```json
{
  "name": "My R2",
  "type": "s3",
  "encryption_mode": "e2ee",
  "key_id": "key_abc123",
  "config_ciphertext": "...",
  "config_nonce": "..."
}
```

### 12.5 File API

```text
GET    /api/files
POST   /api/files/upload
GET    /api/files/{file_id}
PATCH  /api/files/{file_id}
DELETE /api/files/{file_id}
```

### 12.6 Share API

```text
GET    /api/shares
POST   /api/shares
GET    /api/shares/{share_id}
PATCH  /api/shares/{share_id}
DELETE /api/shares/{share_id}
```

### 12.7 Public Download API

```text
GET  /s/{token}
GET  /r/{token}
HEAD /r/{token}
GET  /d/{token}
```

说明：

- `/s/{token}`：分享页。
- `/r/{token}`：raw 访问，适合 AI / 脚本。
- `/d/{token}`：强制下载。

### 12.8 Sync API

```text
GET  /api/sync/state
POST /api/sync/pull
POST /api/sync/push
POST /api/sync/resolve-conflict
```

同步对象：storage methods、files、folders、shares、default settings、crypto metadata、device metadata。

---

## 13. 数据库设计

### 13.1 users

```text
id
username
email
nickname
avatar_url
password_hash
two_factor_enabled
created_at
updated_at
```

### 13.2 user_keys

```text
id
user_id
key_id
key_type
encryption_mode
encrypted_user_data_key
server_key_id
public_metadata_json
created_at
revoked_at
```

说明：

- Online Share：保存 `encrypted_user_data_key`。
- E2EE：不保存 LMK 明文，只保存 `key_id` 和元数据。

### 13.3 devices

```text
id
user_id
device_name
client_type
device_public_key
approved_at
last_used_at
created_at
revoked_at
```

### 13.4 api_tokens

```text
id
user_id
name
token_hash
scopes
expires_at
last_used_at
created_at
revoked_at
```

### 13.5 storage_methods

```text
id
user_id
name
type
encryption_mode
key_id
config_ciphertext
config_nonce
config_tag
is_default
created_at
updated_at
```

### 13.6 folders

```text
id
user_id
parent_id
name
created_at
updated_at
```

### 13.7 files

```text
id
user_id
folder_id
storage_method_id
storage_type
name
original_name
mime_type
size
sha256
storage_key
public_url
thumbnail_url
metadata_json
local_origin_id
created_at
updated_at
deleted_at
```

### 13.8 shares

```text
id
user_id
file_id
folder_id
token
share_type
delivery_mode
expires_at
password_hash
max_downloads
download_count
allow_preview
created_at
revoked_at
```

注意：

- 不存储 `presigned_url`。
- 不存储 OneDrive temporary download URL。
- 不存储完整临时直链。

### 13.9 sync_states

```text
id
user_id
client_id
last_pull_at
last_push_at
last_cursor
created_at
updated_at
```

### 13.10 audit_logs

```text
id
user_id
action
target_type
target_id
ip
user_agent
metadata_json
created_at
```

审计日志不记录 secret、token、完整临时直链。

---

## 14. Web 端设计

### 14.1 技术栈

```text
Astro
React islands
TypeScript
Zustand
lucide-react
CSS variables
Web Crypto API
```

Web Crypto API 用于：

1. E2EE 模式下在浏览器本地加密 / 解密 storage config。
2. 导入 LMK。
3. 初始化 E2EE。

### 14.2 Web 页面

#### 首页

项目简介、核心功能、CLI 安装说明、使用示例、登录 / 注册入口、自托管说明入口。

#### 文件页

文件列表、文件夹列表、上传、搜索、排序、列表 / 大图视图切换、右键菜单、文件属性、分享链接管理。

右键菜单：复制分享页链接、复制 Raw 链接、生成新链接、查看文件属性、查看存储方式、重命名、移动、删除。

#### 存储方式页

新增 / 编辑 storage method、选择加密模式、测试连接、设为默认、删除。创建 storage method 时，用户选择 E2EE Synced 或 LinkFile Online Share。

#### 设备页

查看已登录设备、查看 CLI 设备、审批新设备、撤销设备、查看设备最后使用时间。

#### 加密与密钥页

查看当前加密模式、初始化 E2EE、导入主密钥、导出主密钥、轮换密钥、重新加密 storage method、查看 storage method 使用的 key_id。

#### Token 页

创建 Token、设置 scope、设置过期时间、复制 Token、撤销 Token。

#### 个人页

头像、昵称、用户名、邮箱、个人简介、文件数量、分享次数、注册时间。

#### 安全页

修改密码、设置 2FA、登录历史、活跃设备、退出所有设备。

#### 分享页

文件名、文件大小、文件类型、上传者、过期时间、下载按钮、密码输入、失效提示、预览区域。

### 14.3 Web UI 风格

参考用户博客截图，视觉风格建议：

1. 浅米粉色背景。
2. 柔和奶茶棕主题色。
3. 大圆角卡片。
4. 衬线体标题。
5. 低对比阴影。
6. 半透明顶部导航。
7. 宽松排版。
8. 个人博客式温和气质。

主题变量示例：

```css
:root {
  --lf-bg: #f8ebe6;
  --lf-card: #fffaf7;
  --lf-text: #6f5a50;
  --lf-muted: #a48d82;
  --lf-border: #ead8d0;
  --lf-primary: #b9967d;
  --lf-primary-soft: #e9d2c4;
  --lf-danger: #b96b6b;
  --lf-radius-lg: 24px;
  --lf-radius-xl: 32px;
  --lf-shadow-soft: 0 16px 40px rgba(132, 92, 72, 0.12);
}
```

字体建议：

- 标题：Noto Serif SC / LXGW WenKai / Playfair Display。
- 正文：Inter / Noto Sans SC。
- 代码：JetBrains Mono。

---

## 15. Python SDK 设计

### 15.1 SDK 定位

Python SDK 面向 Python 脚本、自动化任务、AI Agent、个人工具链和服务端集成。

SDK 提供两种客户端：

- `LinkFileClient`：在线 API 客户端。
- `LocalLinkFileClient`：本地离线客户端。

### 15.2 SDK 目录结构

```text
packages/py-sdk/
├─ linkfile/
│  ├─ __init__.py
│  ├─ client.py
│  ├─ async_client.py
│  ├─ local_client.py
│  ├─ models.py
│  ├─ exceptions.py
│  ├─ transport.py
│  ├─ config.py
│  ├─ utils.py
│  ├─ crypto/
│  ├─ resources/
│  └─ py.typed
├─ tests/
├─ pyproject.toml
└─ README.md
```

存储、加密、本地索引等公共逻辑放在 `packages/py-core` 中。

### 15.3 在线 SDK

```python
from linkfile import LinkFileClient

client = LinkFileClient(
    base_url="https://linkfile.example.com",
    token="lf_xxxxx",
)

result = client.upload_file(
    "report.pdf",
    expire="24h",
)

print(result.raw_url)
```

能力：API 上传、获取远端文件列表、创建分享链接、删除远端文件、管理 storage method、管理设备、Online Share 下获取设备封装后的用户数据密钥、E2EE 下本地加密后同步。

### 15.4 离线 SDK

```python
from linkfile import LocalLinkFileClient

client = LocalLinkFileClient.from_config()

result = client.upload_file(
    "report.pdf",
    expire="24h",
)

print(result.raw_url)
```

能力：

1. 读取 CLI config。
2. 读取本地密钥。
3. 直接上传到 S3 / Cloudreve / WebDAV。
4. 即时生成 presigned URL、Cloudreve 直链或分享链接。
5. 写入本地 index。
6. 无需登录。

注意：离线 SDK 不支持普通本机目录作为正式可分享存储，也不支持 local-server。local-server 只能通过在线 API 使用。

### 15.5 SDK 数据模型

```python
class UploadResult(BaseModel):
    file_id: str
    name: str
    size: int
    mime_type: str | None = None
    share_url: str | None = None
    raw_url: str | None = None
    public_url: str | None = None
    expires_at: datetime | None = None
    storage_method_id: str
    storage_type: str
    storage_key: str
```

---

## 16. 配置文件汇总

### 16.1 后端 `.env.example`

```env
LINKFILE_APP_ENV=development
LINKFILE_PUBLIC_BASE_URL=http://localhost:8000
LINKFILE_DATABASE_URL=sqlite:///./linkfile.db
LINKFILE_JWT_SECRET=change-me
LINKFILE_JWT_ALGORITHM=HS256
LINKFILE_ACCESS_TOKEN_EXPIRE_MINUTES=1440
LINKFILE_SERVER_LOCAL_ROOT=/var/lib/linkfile/storage
LINKFILE_CORS_ORIGINS=["http://localhost:4321"]
LINKFILE_SERVER_MASTER_KEY=change-me-32-bytes-key
LINKFILE_DEFAULT_STORAGE_ENCRYPTION_MODE=server_managed
```

### 16.2 前端 `.env.example`

```env
PUBLIC_LINKFILE_API_BASE_URL=http://localhost:8000
PUBLIC_LINKFILE_APP_NAME=LinkFile
PUBLIC_LINKFILE_ENABLE_E2EE=true
```

### 16.3 CLI `config.json`

参见第 10.3 节。v0.1 至少需要支持 S3-compatible 和 Cloudreve 两类 storage method。

---

## 17. 开发路线

### v0.1：CLI 离线核心版

目标：

1. 不依赖 Web。
2. 不依赖登录。
3. 本地配置 S3 / R2 / MinIO。
4. 本地配置 Cloudreve。
5. 上传文件。
6. 生成 `public_url`、`presigned_url`、Cloudreve 直链或 Cloudreve 分享链接。
7. 维护本地 `index.sqlite3`。

功能：

```bash
linkfile setup
linkfile storage add s3
linkfile storage add cloudreve
linkfile storage test my-r2
linkfile storage test my-cloudreve
linkfile upload file.pdf --storage my-r2 --expire 24h
linkfile upload file.pdf --storage my-cloudreve --expire 24h
linkfile list
linkfile info
linkfile download file_xxx ./downloads/
linkfile delete file_xxx
```

这是最应该先做的版本，因为它能最快验证 LinkFile 的核心价值。S3 覆盖对象存储直链 / 预签名链接场景，Cloudreve 覆盖已有自托管网盘用户的快速上传和分享场景。

### v0.2：API Only 基础版

加入：

1. FastAPI 后端。
2. 用户注册登录。
3. API Token。
4. 文件索引 API。
5. Storage Method API。
6. Share API。
7. CLI 登录指定服务端。
8. Python SDK 初步支持。
9. local-server 初步支持。

此阶段即使没有 Web 前端，也能通过 CLI / SDK / HTTP API 使用在线能力。

### v0.3：Web 在线基础版

加入：

1. Astro Web 前端。
2. Web 登录注册。
3. 文件列表。
4. Web 上传。
5. 分享页 `/s/{token}`。
6. raw 链接 `/r/{token}`。
7. Token 管理。

### v0.4：加密体系完善版

加入：

1. 用户数据密钥。
2. 主密钥加密用户数据密钥。
3. server_managed 加密配置。
4. E2EE storage config。
5. CLI master key。
6. crypto export / import。
7. storage method reencrypt。
8. server master key rotation。

### v0.5：设备同步版

加入：

1. CLI 登录。
2. CLI 生成设备密钥对。
3. 服务端设备注册。
4. 服务端用设备公钥封装用户数据密钥。
5. CLI 保存设备私钥 / 用户数据密钥到 keyring。
6. 新设备自动同步 Online Share 配置。

### v0.6：CLI + Web 同步版

加入：

1. CLI push 本地索引。
2. CLI pull 云端配置。
3. storage method 同步。
4. 文件列表同步。
5. 冲突检测。

### v0.7：Web 完整管理版

加入：

1. Storage Method 图形化编辑。
2. Token scope。
3. 分享密码。
4. 下载次数限制。
5. 下载日志。
6. 文件预览。
7. 缩略图。
8. 批量操作。

### v0.8：生态版

加入：

1. Python SDK 完整版。
2. LocalLinkFileClient。
3. Async SDK。
4. WebDAV。
5. OneDrive。
6. Google Drive。
7. TUI。
8. 2FA。
9. 管理后台。
10. 多用户配额。

---

## 18. 最小闭环

实际开工时建议先完成这个闭环：

1. `linkfile setup` 生成本地配置。
2. `linkfile storage add s3` 配置 R2 / MinIO。
3. `linkfile storage add cloudreve` 配置 Cloudreve。
4. `linkfile upload report.pdf --storage my-r2 --expire 24h`。
5. CLI 上传到 S3 并即时生成 presigned URL。
6. `linkfile upload report.pdf --storage my-cloudreve --expire 24h`。
7. CLI 通过 Cloudreve SDK 上传并生成 Cloudreve 直链或分享链接。
8. CLI 写入本地 `index.sqlite3`，但不保存临时 URL。
9. `linkfile list` 能看到上传记录。
10. 浏览器 / AI / curl 能访问链接下载。

这个闭环完成后，LinkFile 的核心价值已经成立：

- 给 AI 分享文件。
- 给他人临时下载。
- CLI 不登录也能用。
- 用户自带存储。
- 支持对象存储和 Cloudreve。
- 临时链接不落库。

---

## 19. 最终产品语义

LinkFile 的最终形态是：

> **一个轻量、漂亮、CLI 优先、可离线运行、支持自带存储、支持自托管 Web/API、支持加密配置同步的文件分享工具。**

核心价值：

1. 上传很快。
2. 链接干净。
3. 适合 AI。
4. 适合临时分享。
5. 存储归用户自己。
6. CLI 不依赖 Web。
7. v0.1 即支持 S3-compatible 和 Cloudreve。
8. Web/API 可自行部署。
9. Web/API 可提供在线分享。
10. local-server 作为自托管服务端磁盘存储能力存在。
11. 存储配置可加密。
12. E2EE 模式下服务端不可见凭证。
13. Online Share 模式下支持完整 LinkFile 域名分享。
14. 临时链接永远不持久化保存。

README 可以这样写：

> **LinkFile is a lightweight BYOS file sharing tool for AI workflows, temporary downloads, and personal direct links, with an offline-first CLI, self-hostable Web/API, S3/Cloudreve support, local-server storage, and encrypted storage configuration sync.**

中文概括：

> **LinkFile 是一个面向 AI 工作流、临时下载和个人直链发布的轻量自带存储文件分享工具，提供离线优先的 CLI、S3/Cloudreve 支持、可自托管的 Web/API、local-server 服务端存储、加密的存储配置同步，以及可选的 LinkFile 在线分享能力。**
