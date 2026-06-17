# web-telly

**开源免费的局域网 Tally 灯系统，适用于视频导播切换台。**

用手机、平板或电脑即可实时显示 Tally 指示——无需额外硬件。摄像师打开网页、选择机位，导播切入时自动全屏变红（PGM）或变绿（PVW）。

> © 潍坊工商融媒体中心

---

## 工作原理

```
┌──────────────┐    TCP :19010     ┌──────────────┐   WebSocket    ┌─────────────┐
│   导播切换台   │ ────────────────→ │  web-telly   │ ─────────────→ │  手机/平板   │
│  OSEE / BMD   │   JSON 协议       │  (你的电脑)   │   实时推送      │  (浏览器)    │
└──────────────┘                   └──────────────┘                └─────────────┘
                                         │
                                    GUI 窗口 + EXE
                                     一键启动
```

1. 在 Windows 电脑上**运行 web-telly**，与导播台在同一局域网。
2. **输入导播台 IP**（如 `192.168.3.208`），点击连接。
3. 手机打开生成的网址，**选择机位**即可。
4. 屏幕**红色**=主输出(PGM)，**绿色**=预监(PVW)，**灰色**=待机。

---

## 功能特性

| 功能 | 说明 |
|------|------|
| **零硬件成本** | 手机/平板通过浏览器即可当作 Tally 灯使用 |
| **即开即用 EXE** | 单个 `web-telly.exe`，无需安装 Python 环境 |
| **自动 IP 识别** | 自动找到与导播台同一网段的本机 IP |
| **端口自动选择** | 7210 端口被占用时自动顺延 7211、7212…… |
| **机位独占锁定** | 1-4 号机位一人一位，防止冲突 |
| **导播监看页** | 电脑端同时显示所有通道的实时颜色 |
| **强释放机位** | 导播可强制踢出被占用的机位 |
| **AUTO 过渡检测** | 按 AUTO 时 PGM 和 PVW 机位同时变红 |
| **防手机息屏** | 浏览器保持唤醒，屏幕常亮 |
| **200ms 轮询** | 防止 WebSocket 断开导致显示卡死 |
| **配置持久化** | 导播台 IP 和端口自动保存到 `config.txt` |

---

## 快速开始

### 方式一：便携 EXE（推荐）

1. 从 [Releases](../../releases) 下载 `web-telly.exe`。
2. 双击运行。
3. 输入导播台的 IP 地址和端口。
4. 点击**连接导播台**。
5. 在设备上打开显示的网址即可。

### 方式二：源码运行

```bash
# 需要 Python 3.10+
pip install flask flask-socketio

# 运行 GUI 版本
python gui_server.py

# 或运行命令行版本
python tally_server.py
```

---

## 使用说明

### 导播端（电脑）

- 点击**电脑端**旁边的"打开"按钮（如 `http://192.168.3.96:7210/director`）
- 2×4 网格显示 4 个机位 + 4 个特殊通道
- 红色=PGM，绿色=PVW，灰色=空闲
- 机位被占用时显示**释放按钮**，点击可强制踢出

### 摄像端（手机/平板）

- 打开**手机端**网址（如 `http://192.168.3.96:7210`）
- 点击机位按钮（1-4）选择机位，也可点击**导播位**查看全部
- 自动进入全屏模式：
  - **灰色**背景 + 白色大号数字 = 待机
  - **红色**背景 = 你的机位是 PGM（主输出）
  - **绿色**背景 = 你的机位是 PVW（预监）
  - AUTO 过渡时：PGM 和 PVW 机位同时显示红色

---

## 支持的导播台

| 品牌 | 协议 | 端口 | 状态 |
|------|------|------|------|
| **OSEE 时代奥视** | TCP JSON | 19010 | ✅ 完全支持 |
| **BMD ATEM** | TCP JSON（兼容） | 19010 | ✅ 支持 |
| 其他兼容协议 | TCP JSON | 可配置 | ✅ 理论支持 |

导播台协议使用 JSON 消息，例如：
```json
{"id": "pgmIndex", "type": "set", "value": [1]}
{"id": "pvwIndex", "type": "set", "value": [2]}
{"id": "transitionStatus", "type": "pus", "value": [1]}
```

---

## 项目结构

```
tally-web/
├── gui_server.py           # 主 GUI 程序（tkinter 窗口）
├── tally_server.py         # 命令行版本
├── start.bat               # Windows 启动脚本
├── app.ico                 # 程序图标
├── config.txt              # 保存的配置（自动生成）
│
├── core/
│   ├── network_utils.py    # IP 检测、端口扫描、连接测试
│   └── switcher_client.py  # 导播台 TCP 协议客户端
│
├── web/
│   ├── app.py              # Flask 应用、SocketIO、状态管理
│   ├── routes.py           # HTTP 路由
│   └── socket_events.py    # WebSocket 事件处理
│
├── templates/
│   ├── index.html          # 手机端：机位选择页
│   ├── director.html       # 电脑端：导播监看页
│   └── tally.html          # 全屏 Tally 显示页
│
└── static/
    └── style.css            # 样式表
```

---

## 打包 EXE

```bash
pip install pyinstaller

pyinstaller --onefile --windowed \
  --name "web-telly" \
  --icon "app.ico" \
  --add-data "templates;templates" \
  --add-data "static;static" \
  --add-data "core;core" \
  --add-data "web;web" \
  --hidden-import engineio.async_drivers.threading \
  --collect-all engineio \
  --collect-all socketio \
  gui_server.py
```

生成的 EXE 位于 `dist/web-telly.exe`。

---

## 常见问题

**Q: 手机打不开网页？**
A: 确保手机与运行 web-telly 的电脑在同一 WiFi/局域网。检查防火墙是否拦截了 7210 端口。

**Q: Tally 颜色不更新？**
A: 确认导播台 IP 和端口正确。查看连接状态指示灯是否绿色。

**Q: 自动检测的 IP 不对？**
A: 程序优先选择与导播台同一网段的 IP。如果电脑有多块网卡，请确保正确的那块处于活动状态。

**Q: 机位显示"已占用"但实际没人用？**
A: 用电脑打开导播监看页，点击对应机位的**释放按钮**强制解除占用。

---

## 致谢

- **作者**：潍坊工商融媒体中心
- **灵感来源**：[OmniTally](https://github.com/OmniDamon/OmniTally) by OmniDamon
- **技术栈**：Flask、Flask-SocketIO、tkinter、PyInstaller

---

## 许可证

本项目免费开源，可自由使用、修改和分发。
