# AI 桌面助手

基于大模型 API 的智能聊天与图像识别桌面软件  
—— 人工智能通识课 期末项目

---

## 📖 项目简介

**AI 桌面助手** 是一个使用 Python + tkinter 构建的轻量级桌面应用，集成了：

- 💬 **智能聊天**（DeepSeek API，支持多轮对话记忆）
- 🖼️ **图像识别**（通义千问 VL，支持物体识别、公式识别、LaTeX 输出）
- 🧠 **双用户画像系统**（手动 + 自动，自动学习支持删除与增加）
- 📐 **LaTeX 公式渲染**（聊天中显示数学公式）

项目的核心设计理念是：**让 AI 主动适应用户，而不是让用户反复调教 AI**。

---

## ✨ 主要功能

| 功能 | 说明 |
|------|------|
| **智能聊天** | 接入 DeepSeek 大模型，支持多轮对话，带对话历史记忆 |
| **用户画像（手动）** | 用户可自由设置回答规则（如"回答数学题时要给出证明"） |
| **用户画像（自动）** | AI 从对话中自动提取你的偏好，支持**删除旧偏好 + 增加新偏好**的智能修正机制 |
| **自动学习开关** | 可随时开启或关闭自动学习功能 |
| **自定义学习指令** | 高级用户可修改 AI 提取偏好的"观察规则" |
| **图像识别** | 上传图片，调用通义千问 VL 模型识别物体、公式、手写文字 |
| **公式 LaTeX 输出** | 识别图片中的数学公式，自动输出 LaTeX 格式 |
| **图像记忆** | 识别结果自动存入对话历史，后续可基于图片内容追问 |
| **公式渲染** | 聊天中自动识别 `$...$`、`\[...\]`、`\(...\)` 公式并显示为图片 |
| **本地数据存储** | 聊天记录和画像数据保存在本地，隐私可控 |

---

## 📁 项目结构

```
AI桌面助手/
├── main.py                 # 主程序
├── formula_renderer.py     # LaTeX 公式渲染模块
├── requirements.txt        # Python 依赖清单
├── .env                    # 环境变量（需自行创建，不提交）
├── .env.example            # 环境变量示例（提交到仓库）
├── user_profile.json       # 用户画像数据（运行后自动生成）
├── chat_history.txt        # 聊天记录（运行后自动生成）
└── README.md               # 本文件
```

---

## 🚀 快速开始

### 1. 安装 Python

本项目需要 Python 3.8 或更高版本。  
如果没有安装，请访问 [python.org](https://www.python.org/) 下载并安装。

### 2. 安装依赖

在项目文件夹中打开终端（或命令提示符），运行：

```bash
pip install -r requirements.txt
```

如果没有 `requirements.txt`，手动安装以下库：

```bash
pip install requests pillow matplotlib python-dotenv
```

> 注：`tkinter` 是 Python 内置模块，无需额外安装。

### 3. 配置环境变量

在项目根目录下创建 `.env` 文件，填入你的 API 密钥：

```
DEEPSEEK_API_KEY=sk-你的DeepSeek API Key
DASHSCOPE_API_KEY=你的通义千问API Key
```

或复制 `.env.example` 为 `.env` 再填入：

```bash
cp .env.example .env
```

**获取方式**：
- **DeepSeek API**：访问 [platform.deepseek.com](https://platform.deepseek.com/) 注册获取
- **通义千问 API**：访问 [阿里云百炼平台](https://bailian.console.aliyun.com/) 开通 `qwen-vl-plus` 服务后获取

> 如不使用图像识别，`DASHSCOPE_API_KEY` 可留空，但点击"上传图片并识别"会报错。

### 4. 运行程序

在终端中执行：

```bash
python main.py
```

首次启动会自动弹出"设置偏好"窗口，填写你的回答偏好后即可开始使用。

---

## 🧪 使用示例

### 聊天 + 手动偏好

在"修改画像"中填写：

> "回答数学问题时，请先给出结论，再给出证明过程。"

之后提问数学问题，AI 会自动按此规则回答。

### 自动学习与修正

当你对 AI 说：

> "我喜欢打 csgo。"

AI 会自动记录：`用户偏好：用户喜欢打 csgo`

当你纠正：

> "骗你的，我不打游戏。"

AI 会自动**删除**旧记录 `用户喜欢打 csgo`，画像中不再保留该条信息。

> 自动学习支持"删除 + 增加"机制，用户可随时在设置窗口中查看和手动编辑自动画像。

### 图像识别与公式提取

点击"上传图片并识别"，选择一张包含数学公式的图片，AI 会返回 LaTeX 格式的公式：

```
$$
\int_0^\infty e^{-x^2} dx = \frac{\sqrt{\pi}}{2}
$$
```

识别结果会自动存入对话历史，你可以继续追问：

> "这个积分的几何意义是什么？"

AI 会基于之前识别出的公式进行回答。

---

## 🛠️ 技术栈

| 层级 | 技术 |
|------|------|
| 前端界面 | Python tkinter |
| 聊天模型 | DeepSeek API（`deepseek-chat`） |
| 图像识别 | 通义千问 VL（`qwen-vl-plus`） |
| 公式渲染 | Matplotlib + Pillow |
| 数据存储 | JSON（画像）+ TXT（聊天记录） |
| 并发处理 | threading（多线程） |

---

## ⚙️ 配置文件说明

### `user_profile.json`

```json
{
  "manual": "用户手动设置的规则",
  "auto": "AI从对话中学习到的偏好（支持删除+增加）",
  "auto_learn_enabled": true,
  "learning_prompt_custom": "用户自定义的学习指令（可选）"
}
```

- `manual`：在设置窗口中编辑，优先级高于自动偏好。
- `auto`：由 AI 自动学习生成，**支持删除旧记录 + 增加新记录**，也可在设置窗口中手动编辑。
- `auto_learn_enabled`：是否允许 AI 继续学习。
- `learning_prompt_custom`：自定义学习指令，控制 AI 的学习角度。

### `chat_history.txt`

纯文本格式，记录所有对话历史，重启程序后自动加载。

---

## ❓ 常见问题

### Q1：提示"❌ 调用出错：401"  
**A**：API Key 无效或未填写，请检查 `.env` 中的 `DEEPSEEK_API_KEY` 是否正确。

### Q2：图像识别提示"400 Bad Request"  
**A**：请确认 `DASHSCOPE_API_KEY` 已正确填写，且在阿里云百炼控制台中已开通 `qwen-vl-plus` 模型服务。

### Q3：公式显示为纯文本（如 `$E=mc^2$`）  
**A**：请确认已安装 `matplotlib` 和 `pillow`，且 `formula_renderer.py` 与 `main.py` 在同一目录下。

### Q4：自动画像中有些内容我不想要，怎么删除？  
**A**：有两种方式：
1. 在对话中明确否定（如"我不打游戏"），AI 会自动删除旧记录。
2. 打开"修改画像"窗口，在"自动偏好"文本框中手动删除，点击保存即可。

### Q5：窗口卡住不动  
**A**：检查网络是否正常，API 调用超时可能导致界面短暂无响应。如频繁出现，可检查 API 余额是否充足。

---

## 🙏 致谢

- [DeepSeek](https://www.deepseek.com/) —— 提供强大的大语言模型 API
- [通义千问](https://bailian.console.aliyun.com/) —— 提供多模态图像识别能力
- [Matplotlib](https://matplotlib.org/) —— 用于 LaTeX 公式渲染

---

## 📄 许可证

本项目仅供学习交流使用，请勿用于商业用途。

---

**作者**：mkiii-labs  
**课程**：人工智能通识课  
**日期**：2026 年 6 月
