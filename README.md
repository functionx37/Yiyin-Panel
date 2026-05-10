# Yiyin-Panel

本项目为 [**Yiyin-Bot**](https://github.com/functionx37/Yiyin-Bot) 项目的一个数据展示与管理网站，前端使用 **Vue.js** 框架，后端使用 **FastAPI** 框架，使用 **uv** 管理依赖，使用 **nginx** 进行反向代理到 `/yiyin` 下。

## 网站功能

* 网页可视化群聊功能开关
  * 访问 `/yiyin/admin`
  * 输入 `.env` 中配置的 `ADMIN_PASSWORD`
  * 即可在网页管理各项功能在各个群聊的开关情况
* 群聊食物与语录展示
  * 在群聊中使用 `/web` 指令获取本日群聊展示网址
  * 只展示非隐藏食物
  * 网址当日有效

## 环境变量

复制 `.env.example` 为 `.env`：

```bash
cp .env.example .env
```

其中 `SITE_BASE_URL` 与 `WEB_TOKEN_SECRET` 需要和 `Yiyin-Bot` 的运行环境保持一致，否则 `/web` 生成的链接无法被本站正确校验。

## 本地开发

### 1. 启动后端

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 2. 启动前端

```bash
cd frontend
npm install
npm run dev
```

### 3. 访问开发地址

访问 `http://127.0.0.1:5173/yiyin/admin` 进行预览

## 生产部署

### 1. 构建前端

```bash
cd frontend
npm install
npm run build
sudo cp -r dist/* /var/www/yiyin/dist/
```

可以直接使用脚本在本地构建并推送到远程：

```bash
./scripts/deploy-frontend-dist.sh
```

### 2. 启动后端

```bash
cd backend
uv sync --frozen
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 3. 配置 nginx

首次部署时，先安装 nginx

```bash
sudo apt update
sudo apt install -y nginx gettext-base rsync
```

然后执行

```bash
sudo ./scripts/setup-nginx.sh
```

该脚本可以自动生成反向代理配置。
