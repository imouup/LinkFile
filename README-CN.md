# LinkFile

版本：`0.1.1`

LinkFile 是一个轻量的 BYOS 文件分享工具，面向 AI 工作流、临时下载和个人直链发布。

当前版本以 CLI 为核心，只实现 Local Only 模式。你可以使用自己的存储，在本地配置后通过命令行上传文件，并得到适合发给 AI 工具、脚本或他人的直链。

当前支持的存储：

- S3-compatible 存储，包括 Cloudflare R2 和 MinIO
- Cloudreve v3/4

## 开始使用

### 安装
#### 1.源代码安装
安装整个 workspace 的依赖：

```bash
git clone https://github.com/imouup/LinkFile.git
cd I:\Project\LinkFile
uv sync --all-packages
```

检查 CLI：

```bash
uv run --package linkfile-cli linkfile --help
```

如果 workspace 包已经安装到当前虚拟环境，也可以直接运行：

```bash
linkfile --help
```

#### 2.uv/pip安装

```bash
uv pip install linkfile-cli
```

## 初次使用

初始化本地配置和 SQLite ：

```bash
linkfile setup
```

添加 Cloudflare R2 或其他 S3-compatible 存储：

```bash
linkfile storage add s3 `
  --name linkfile-r2 `
  --endpoint-url https://<account-id>.r2.cloudflarestorage.com `
  --region auto `
  --bucket linkfile `
  --prefix uploads `
  --public-base-url https://files.example.com `
  --access-key-id <access-key-id> `
  --secret-access-key <secret-access-key>
```

添加 Cloudreve：

```bash
linkfile storage add cloudreve `
  --name cloudreve-test `
  --base-url https://pan.example.com `
  --username user@example.com `
  --password <password> `
  --root-path /LinkFile `
  --prefer-direct-url
```

测试存储：

```bash
linkfile storage test cloudreve-test
```

上传文件：

```bash
linkfile upload test/test.jpg --storage cloudreve-test
```

输出会包含文件 id：

```text
ID: file_xxx
File: test.jpg
Raw:
https://...
```

使用文件 id 下载和删除：

```bash
linkfile download file_xxx
linkfile delete file_xxx --yes
```

## CLI 文档

### `linkfile setup`

创建本地配置文件和本地 SQLite 索引。

配置文件会保存 storage method 和凭证。`0.1.1` 中，凭证会以明文保存在 `config.json`。

### `linkfile storage add s3`

添加 S3-compatible 存储。

常用参数：

- `--name`
- `--endpoint-url`
- `--region`
- `--bucket`
- `--prefix`
- `--public-base-url`
- `--path-style`
- `--access-key-id`
- `--secret-access-key`

Cloudflare R2 endpoint 会自动使用 path-style 地址和 `auto` region 来生成签名 URL。

### `linkfile storage add cloudreve`

添加 Cloudreve v4 存储。

常用参数：

- `--name`
- `--base-url`
- `--username`
- `--password`
- `--root-path`
- `--prefer-direct-url`

Cloudreve 直链不支持 LinkFile 侧过期时间。如果上传时对 Cloudreve direct link 使用 `--expire`，CLI 会提示该参数将被忽略。

### `linkfile storage test <name>`

测试某个已配置的存储是否可用。

### `linkfile storage delete <name> --yes`

从本地配置中删除 storage method。

如果删除的是默认 storage，LinkFile 会自动选择剩余的第一个 storage 作为默认值。

### `linkfile upload <path>`

通过配置好的 storage 上传本地文件。

常用参数：

- `--storage`, `-s`
- `--expire`, `-e`
- `--format`, `-f`：`text` 或 `json`

临时链接只会即时生成，不会写入本地索引。

### `linkfile list`

从本地 SQLite 索引中列出文件记录。

### `linkfile info <file_id>`

显示本地文件记录的元数据，并在支持时即时生成新的临时链接。

### `linkfile download <file_id> [destination]`

通过本地文件 id 下载文件。

如果不指定 `destination`，文件会下载到当前目录。

### `linkfile delete <file_id> --yes`

在支持时删除远端文件，并删除本地索引记录。

使用 `--local-only` 可以只删除本地索引记录。

## TODO

- `v0.2`：API 基础版，包括登录认证、API Token、文件元数据 API、Storage Method API、Share API 和 local-server 存储。
- `v0.3`：Web 基础版，包括登录、文件列表、Web 上传、公开分享页、Raw 链接和 Token 管理。
- `v0.4`：加密体系，包括 server-managed 加密配置、E2EE storage config、主密钥导入导出、重新加密和服务端主密钥轮换。
- `v0.5`：设备同步，包括 CLI 设备密钥、设备审批和用户数据密钥封装。
- `v0.6`：CLI 与 Web 同步，包括 push/pull、storage method 同步、文件索引同步和冲突处理。
- `v0.7`：完整 Web 管理，包括 storage 图形化编辑、Token scope、分享密码、下载次数限制、下载日志、预览、缩略图和批量操作。
- `v0.8`：生态扩展，包括更完整的 Python SDK、异步 SDK、WebDAV、OneDrive、Google Drive、TUI、2FA、管理后台和配额。

## License

MIT
