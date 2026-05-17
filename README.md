# AirType

<div align="center">

**语音输入，精准注入**

一款 Windows 桌面语音输入工具，按下快捷键说话，识别文字自动输入到当前应用。

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2B-lightgrey)]()
[![Tauri](https://img.shields.io/badge/Tauri%202-React%20Free-ffc131)]()

</div>

---

## 这是什么？

AirType 是一款 **Windows 桌面语音输入工具**，让你在任何应用中通过语音快速输入文字。

**核心功能：**
- 按住快捷键说话，松开自动识别并输入文字
- 支持本地 ASR（语音识别）引擎，离线可用，隐私安全
- 可选 AI 文字润色，自动去除口吃、添加标点、修正错字
- 极简胶囊浮动窗设计，不干扰工作流

**适用场景：**
- 写文档、发消息、记笔记时快速语音输入
- 需要 hands-free 输入的场合
- 对隐私有要求，不想使用在线语音服务

---

## 功能特性

- **全局快捷键录音** — 按住 `Ctrl+Win` 说话，松开即识别
- **本地 ASR 引擎** — 支持 Qwen3-ASR 模型，离线可用，隐私安全
- **AI 文字润色** — 可选 LLM 处理，自动去除口吃、添加标点、修正错字
- **文字注入** — 识别结果直接输入到当前光标位置，支持 CJK 输入法
- **胶囊浮动窗** — 极简录音状态指示器，不干扰工作流
- **系统托盘** — 后台运行，右键菜单快速设置
- **Spotify 风格 UI** — 深色主题，圆角胶囊设计

---

## 快速开始

### 环境要求

- Windows 10 或更高版本
- [Rust](https://rustup.rs/) (1.70+)
- [Node.js](https://nodejs.org/) (仅用于图标生成脚本)

### 安装步骤

#### 1. 克隆仓库

```bash
git clone https://github.com/yanghan-cyber/airType.git
cd airType
```

#### 2. 下载 ASR 模型

**推荐模型：Qwen3-ASR-0.6B**

从 [Hugging Face](https://huggingface.co/Qwen/Qwen3-ASR-0.6B) 下载模型文件。

**重要：必须使用 GGUF 格式模型**

AirType 使用 llama.cpp 运行本地 ASR 模型，因此需要 GGUF 格式的模型文件。

**下载方式：**
1. 访问 [Qwen3-ASR-0.6B-GGUF](https://huggingface.co/Qwen/Qwen3-ASR-0.6B-GGUF)
2. 下载 `qwen3-asr-0.6b-q4_k_m.gguf` 文件（推荐 Q4_K_M 量化版本，平衡性能和精度）
3. 将文件放到 `models/` 目录

```
models/
└── qwen3-asr-0.6b-q4_k_m.gguf
```

**其他可选模型：**
- [Qwen3-ASR-1.7B-GGUF](https://huggingface.co/Qwen/Qwen3-ASR-1.7B-GGUF) — 更大模型，精度更高，需要更多内存

#### 3. 启动 ASR 后端

使用 [llama.cpp](https://github.com/ggerganov/llama.cpp) 启动本地 ASR 服务：

```bash
# 下载 llama.cpp
# 从 https://github.com/ggerganov/llama.cpp/releases 下载预编译版本

# 启动 ASR 服务器
llama-server -m models/qwen3-asr-0.6b-q4_k_m.gguf --port 8178
```

**或者使用兼容的 OpenAI API 服务：**

如果你有其他兼容 OpenAI API 的 ASR 服务（如 OpenAI Whisper API、LocalAI 等），也可以直接使用。

#### 4. 构建并运行

```bash
cd src-tauri
cargo run
```

---

## 配置

编辑 `config.json`（首次运行后自动生成）：

```json
{
  "hotkey": "Ctrl+Win",
  "enabled": true,
  "backend_url": "http://localhost:8178/v1",
  "max_recording_secs": 30
}
```

| 字段 | 说明 | 默认值 |
|------|------|--------|
| `hotkey` | 录音快捷键 | `Ctrl+Win` |
| `enabled` | 是否启用 | `true` |
| `backend_url` | ASR 后端地址 | `http://localhost:8178/v1` |
| `max_recording_secs` | 最大录音时长（秒） | `30` |

---

## 使用方法

1. 启动 AirType，系统托盘出现图标
2. 在任意应用中按住 `Ctrl+Win` 开始说话
3. 松开快捷键，语音自动识别并输入到光标位置
4. 右键托盘图标可打开设置、启用/禁用、退出

### 处理模式

| 模式 | 说明 |
|------|------|
| 直接输入 | 跳过 AI，直接使用 ASR 原始文本 |
| 文本润色 | 去除口吃、添加标点、修正错字 |
| 自定义 | 在设置中配置自定义 LLM 提示词 |

---

## 开发

### 项目结构

```
airType/
├── src-tauri/          # Tauri 后端 (Rust)
│   ├── src/
│   │   ├── main.rs     # 应用入口
│   │   ├── asr.rs      # ASR 客户端
│   │   ├── audio.rs    # 音频采集
│   │   ├── commands.rs # Tauri 命令
│   │   ├── config.rs   # 配置管理
│   │   ├── hotkey.rs   # 全局快捷键
│   │   ├── inject.rs   # 文字注入
│   │   ├── llm.rs      # LLM 客户端
│   │   ├── state.rs    # 应用状态
│   │   └── tray.rs     # 系统托盘
│   ├── Cargo.toml
│   └── tauri.conf.json
├── ui/                 # 前端界面 (HTML/CSS/JS)
│   ├── capsule.html    # 胶囊浮动窗
│   └── settings.html   # 设置窗口
├── models/             # ASR 模型 (gitignore)
├── bin/                # 二进制依赖
└── config.json         # 用户配置 (gitignore)
```

### 技术栈

| 组件 | 技术 |
|------|------|
| 框架 | [Tauri 2](https://tauri.app/) |
| 后端语言 | Rust |
| 前端 | HTML + CSS + JavaScript (无框架) |
| 音频采集 | [cpal](https://github.com/RustAudio/cpal) |
| 全局快捷键 | [rdev](https://github.com/Narsil/rdev) |
| 文字注入 | Windows SendInput API |
| ASR | Qwen3-ASR (OpenAI 兼容 API) |
| LLM | OpenAI 兼容 API |

### 构建

```bash
# 开发模式
cd src-tauri
cargo run

# 构建安装包
cargo tauri build
```

### 测试

```bash
cd src-tauri
cargo test
```

---

## 常见问题

**Q: 录音没有反应？**
A: 检查 ASR 后端是否启动，确认 `backend_url` 配置正确。

**Q: 文字没有输入到目标应用？**
A: 确保目标应用处于前台且支持 Unicode 输入。某些游戏或全屏应用可能不兼容。

**Q: 如何修改快捷键？**
A: 编辑 `config.json` 中的 `hotkey` 字段，格式为 `Modifier+Key`，如 `Alt+Space`。

**Q: 支持哪些 ASR 模型？**
A: 支持任何 OpenAI 兼容的 ASR API。推荐使用 Qwen3-ASR-0.6B 或 Qwen3-ASR-1.7B（GGUF 格式）。

**Q: 为什么需要 GGUF 格式？**
A: AirType 使用 llama.cpp 运行本地 ASR 模型，llama.cpp 只支持 GGUF 格式的模型文件。

---

## 许可证

本项目基于 [MIT 许可证](LICENSE) 开源。

## 致谢

- [Tauri](https://tauri.app/) — 轻量级跨平台应用框架
- [Qwen3-ASR](https://github.com/QwenLM/Qwen3-ASR) — 语音识别模型
- [llama.cpp](https://github.com/ggerganov/llama.cpp) — 本地 LLM 推理引擎
