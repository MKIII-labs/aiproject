# -*- coding: utf-8 -*-
"""
AI桌面助手 —— 基于大模型API的智能聊天与图像识别软件
人工智能通识课 期末项目
作者：石小龙
"""

import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog
import threading
import requests
import json
import os
import base64
import sys
import formula_renderer as fr

# ============================================================
# 配置区（请替换为你的真实API密钥）
# ============================================================
#对话LLMAPI
import os
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "请设置环境变量")
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
#图像识别api
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "请设置环境变量")

PROFILE_FILE = "user_profile.json"
HISTORY_FILE = "chat_history.txt"

# ============================================================
# 对话历史（内存中维护，用于多轮对话记忆）
# ============================================================

conversation_history = []  # 存储 {"role": "user"/"assistant", "content": ...}

# ============================================================
# 默认学习指令
# ============================================================

DEFAULT_LEARNING_PROMPT = """你是一个用户画像学习助手。请分析以下对话，判断是否发现了用户的新偏好、习惯或规则。
如果发现了新的、有价值的偏好信息，请用简洁的一句话总结出来，格式为："用户偏好：xxx"。
如果没有发现新的信息，请只回复"无更新"。

当前已知的自动画像：
{current_auto}

本次对话：
用户说：{user_input}
AI回复：{ai_reply}

请判断是否有新信息需要添加到用户画像中。"""

# ============================================================
# 用户画像读写
# ============================================================

def load_profile():
    """加载用户画像，兼容旧版本"""
    default = {
        "manual": "",
        "auto": "",
        "auto_learn_enabled": True,
        "learning_prompt_custom": ""
    }
    if os.path.exists(PROFILE_FILE):
        try:
            with open(PROFILE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "preference" in data and "manual" not in data:
                    data["manual"] = data.pop("preference")
                for key in default:
                    if key not in data:
                        data[key] = default[key]
                return data
        except:
            return default
    return default

def save_profile(manual=None, auto=None, auto_learn_enabled=None, learning_prompt_custom=None):
    current = load_profile()
    if manual is not None:
        current["manual"] = manual
    if auto is not None:
        current["auto"] = auto
    if auto_learn_enabled is not None:
        current["auto_learn_enabled"] = auto_learn_enabled
    if learning_prompt_custom is not None:
        current["learning_prompt_custom"] = learning_prompt_custom
    with open(PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(current, f, ensure_ascii=False, indent=2)

def load_chat_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return f.read()
    return ""

# ============================================================
# DeepSeek API 调用（支持完整对话历史）
# ============================================================

def call_deepseek(messages, system_prompt=""):
    """
    调用 DeepSeek API，传入完整的 messages 列表
    messages: [{"role": "user"/"assistant", "content": "..."}]
    system_prompt: 用户画像（作为 system 角色消息）
    """
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json; charset=utf-8"
    }
    
    # 构建完整的消息列表
    full_messages = []
    if system_prompt:
        full_messages.append({"role": "system", "content": system_prompt})
    full_messages.extend(messages)
    
    data = {
        "model": "deepseek-chat",
        "messages": full_messages,
        "stream": False
    }
    json_data = json.dumps(data, ensure_ascii=False).encode('utf-8')
    try:
        response = requests.post(DEEPSEEK_URL, headers=headers, data=json_data, timeout=30)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except requests.exceptions.Timeout:
        return "⏰ 请求超时，请检查网络连接"
    except Exception as e:
        return f"❌ 调用出错：{str(e)}"

# ============================================================
# 自动学习
# ============================================================

def update_profile_from_conversation(user_input, ai_reply):
    profile = load_profile()
    if not profile.get("auto_learn_enabled", True):
        print("[画像学习] 自动学习已禁用")
        return False

    current_auto = profile.get("auto", "")
    custom_prompt_template = profile.get("learning_prompt_custom", "").strip()

    if custom_prompt_template:
        try:
            learning_prompt = custom_prompt_template.format(
                current_auto=current_auto if current_auto else "（暂无）",
                user_input=user_input,
                ai_reply=ai_reply
            )
        except KeyError:
            learning_prompt = f"{custom_prompt_template}\n\n当前已知自动画像：{current_auto if current_auto else '（暂无）'}\n用户说：{user_input}\nAI回复：{ai_reply}"
    else:
        # 使用新的默认学习指令（包含删除+增加逻辑）
        learning_prompt = f"""你是一个用户画像学习助手。请分析以下对话，判断用户是否对之前的偏好进行了修正或否定。

操作规则：
1. 如果用户明确否定了之前的某条偏好（如"我不打游戏"否定"我喜欢打csgo"），请输出：
   "删除偏好：xxx"（其中 xxx 是旧偏好的完整内容）
2. 如果用户在否定旧偏好的同时，提供了新的替代偏好（如"其实我喜欢游泳"），请额外输出：
   "增加偏好：yyy"
3. 如果用户只是提出全新的偏好（没有否定旧偏好），请输出：
   "增加偏好：zzz"
4. 如果没有任何变化，输出："无更新"

当前已知的自动画像（每条用换行分隔）：
{current_auto if current_auto else "（暂无）"}

本次对话：
用户说：{user_input}
AI回复：{ai_reply}

请严格按照上述格式输出操作指令，每条指令占一行。如果同时有删除和增加，分别输出两行。"""

    try:
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json; charset=utf-8"
        }
        data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "你是一个用户画像管理助手，只输出操作指令。"},
                {"role": "user", "content": learning_prompt}
            ],
            "max_tokens": 300,
            "temperature": 0.3
        }
        json_data = json.dumps(data, ensure_ascii=False).encode('utf-8')
        response = requests.post(DEEPSEEK_URL, headers=headers, data=json_data, timeout=15)
        response.raise_for_status()
        result = response.json()
        learning_result = result["choices"][0]["message"]["content"].strip()
        print(f"[画像学习] 原始输出：{learning_result}")

        if "无更新" in learning_result:
            print("[画像学习] 无新信息")
            return False

        # 解析操作
        lines = learning_result.split("\n")
        deletions = []
        additions = []
        for line in lines:
            line = line.strip()
            if line.startswith("删除偏好："):
                deletions.append(line.replace("删除偏好：", "").strip())
            elif line.startswith("增加偏好："):
                additions.append(line.replace("增加偏好：", "").strip())

        if not deletions and not additions:
            print("[画像学习] 未解析到有效操作")
            return False

        # 处理删除
        current_lines = current_auto.split("\n") if current_auto else []
        # 如果当前画像为空，删除操作无意义，直接跳过
        if deletions and current_lines:
            # 对每个要删除的条目，在 current_lines 中移除匹配的行（支持部分匹配或精确匹配）
            for del_text in deletions:
                # 优先精确匹配整行，否则尝试包含匹配
                found = False
                for i, line in enumerate(current_lines):
                    if line.strip() == del_text or del_text in line:
                        current_lines.pop(i)
                        found = True
                        print(f"[画像学习] 已删除：{del_text}")
                        break
                if not found:
                    print(f"[画像学习] 未找到要删除的条目：{del_text}")
            # 删除后可能有空行
            current_lines = [ln for ln in current_lines if ln.strip()]

        # 处理增加
        for add_text in additions:
            # 避免重复增加相同内容
            if add_text not in current_lines:
                current_lines.append(add_text)
                print(f"[画像学习] 已增加：{add_text}")
            else:
                print(f"[画像学习] 已存在，不重复增加：{add_text}")

        # 保存更新后的画像
        updated_auto = "\n".join(current_lines)
        save_profile(auto=updated_auto, auto_learn_enabled=profile["auto_learn_enabled"])
        return True

    except Exception as e:
        print(f"[画像学习] 出错：{e}")
        return False

# ============================================================
# 图像识别（通义千问VL）- 支持公式识别和LaTeX输出
# ============================================================

def recognize_image(image_path):
    try:
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        return f"❌ 读取图片失败：{str(e)}"
    
    ext = os.path.splitext(image_path)[1].lower()
    mime_type = "image/jpeg"
    if ext == ".png":
        mime_type = "image/png"
    elif ext == ".bmp":
        mime_type = "image/bmp"
    elif ext == ".gif":
        mime_type = "image/gif"
    image_with_prefix = f"data:{mime_type};base64,{image_data}"
    
    url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
    headers = {
        "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # 增强提示词，支持公式识别
    data = {
        "model": "qwen-vl-plus",
        "input": {
            "messages": [{
                "role": "user",
                "content": [
                    {"image": image_with_prefix},
                    {"text": """请分析这张图片，完成以下任务：
1. 如果图片中包含数学公式，请用 LaTeX 格式输出所有公式
2. 如果图片是物体/场景照片，请识别并描述其中的主要内容
3. 如果图片包含手写文字，请尽可能识别并输出
请用中文回答，公式部分用 $$...$$ 包裹。"""
                    }
                ]
            }]
        }
    }
    json_data = json.dumps(data, ensure_ascii=False).encode('utf-8')
    try:
        response = requests.post(url, headers=headers, data=json_data, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        message_content = result["output"]["choices"][0]["message"]["content"]
        
        if isinstance(message_content, list):
            texts = []
            for item in message_content:
                if isinstance(item, dict) and "text" in item:
                    texts.append(item["text"])
            content = "\n".join(texts)
        else:
            content = message_content
        
        if not content or not content.strip():
            return "⚠️ 识别结果为空，请重试或更换图片"
        
        return content
    except requests.exceptions.Timeout:
        return "⏰ 识别超时，请检查网络"
    except Exception as e:
        if hasattr(e, 'response') and e.response is not None:
            return f"❌ 识别出错：{str(e)}\n响应内容：{e.response.text}"
        return f"❌ 识别出错：{str(e)}"

# ============================================================
# 设置窗口
# ============================================================

def open_settings_window(first_run=False):
    win = tk.Toplevel(root)
    win.title("设置用户偏好" if not first_run else "🎯 欢迎！首次使用请设置偏好")
    win.geometry("850x800")
    win.transient(root)
    win.grab_set()

    profile = load_profile()

    tk.Label(win, text="✏️ 手动偏好（你主动设置的规则）", font=("微软雅黑", 10, "bold")).pack(pady=(10,0), anchor=tk.W, padx=10)
    manual_text = scrolledtext.ScrolledText(win, wrap=tk.WORD, height=6, font=("微软雅黑", 10))
    manual_text.pack(padx=10, pady=5, fill=tk.X)
    manual_text.insert(tk.END, profile.get("manual", ""))

    tk.Label(win, text="🤖 自动偏好（AI从对话中学习到的，可手动编辑）", font=("微软雅黑", 10, "bold")).pack(pady=(10,0), anchor=tk.W, padx=10)
    auto_text = scrolledtext.ScrolledText(win, wrap=tk.WORD, height=5, font=("微软雅黑", 10))
    auto_text.pack(padx=10, pady=5, fill=tk.X)
    auto_text.insert(tk.END, profile.get("auto", ""))

    auto_learn_var = tk.BooleanVar(value=profile.get("auto_learn_enabled", True))
    cb = tk.Checkbutton(win, text="启用自动学习（AI将自动从对话中学习你的偏好）", variable=auto_learn_var, font=("微软雅黑", 10))
    cb.pack(pady=5, anchor=tk.W, padx=10)

    tk.Label(win, text="🧠 自定义学习指令（AI如何从对话中学习你的偏好，支持占位符）", font=("微软雅黑", 10, "bold")).pack(pady=(10,0), anchor=tk.W, padx=10)
    tip2 = "可用占位符：{current_auto} 当前自动画像 | {user_input} 用户消息 | {ai_reply} AI回复\n留空则使用默认指令。"
    tk.Label(win, text=tip2, justify=tk.LEFT, font=("微软雅黑", 9), fg="gray").pack(anchor=tk.W, padx=10)
    
    learning_prompt_text = scrolledtext.ScrolledText(win, wrap=tk.WORD, height=6, font=("微软雅黑", 10))
    learning_prompt_text.pack(padx=10, pady=5, fill=tk.X)
    current_custom = profile.get("learning_prompt_custom", "")
    if current_custom:
        learning_prompt_text.insert(tk.END, current_custom)
    else:
        learning_prompt_text.insert(tk.END, "你是一个用户画像学习助手。请分析以下对话，判断是否发现了用户的新偏好、习惯或规则。\n如果发现了新的、有价值的偏好信息，请用简洁的一句话总结出来，格式为：\"用户偏好：xxx\"。\n如果没有发现新的信息，请只回复\"无更新\"。\n\n当前已知的自动画像：{current_auto}\n本次对话：\n用户说：{user_input}\nAI回复：{ai_reply}")

    def save_and_close():
        manual = manual_text.get("1.0", tk.END).strip()
        auto_content = auto_text.get("1.0", tk.END).strip()
        custom_prompt = learning_prompt_text.get("1.0", tk.END).strip()
        save_profile(
            manual=manual,
            auto=auto_content,
            auto_learn_enabled=auto_learn_var.get(),
            learning_prompt_custom=custom_prompt
        )
        global profile
        profile = load_profile()
        update_status()
        win.destroy()

    btn_frame = tk.Frame(win)
    btn_frame.pack(pady=10)
    tk.Button(btn_frame, text="✅ 保存", command=save_and_close, width=10, bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)
    tk.Button(btn_frame, text="❌ 取消", command=win.destroy, width=10).pack(side=tk.LEFT, padx=5)

    win.wait_window()

# ============================================================
# 主界面
# ============================================================

def update_status():
    profile = load_profile()
    status_text = f"✅ 已就绪 | 聊天：DeepSeek | 识别：通义千问VL | 自动学习：{'开启' if profile.get('auto_learn_enabled', True) else '关闭'}"
    status.config(text=status_text)

def send_message():
    global conversation_history
    
    user_input = entry.get().strip()
    if not user_input:
        return

    chat_area.config(state=tk.NORMAL)
    chat_area.insert(tk.END, f"你：{user_input}\n")
    chat_area.insert(tk.END, "AI：正在思考...\n")
    chat_area.config(state=tk.DISABLED)
    entry.delete(0, tk.END)

    # 将用户消息添加到历史
    conversation_history.append({"role": "user", "content": user_input})
    # 限制历史长度（最近20轮对话）
    if len(conversation_history) > 40:
        conversation_history = conversation_history[-40:]

    profile = load_profile()
    manual = profile.get("manual", "")
    auto = profile.get("auto", "") if profile.get("auto_learn_enabled", True) else ""
    system_prompt = "\n".join(filter(None, [manual, auto]))

    def fetch_reply():
        reply = call_deepseek(conversation_history, system_prompt)
        root.after(0, update_chat_with_reply, reply, user_input)

    threading.Thread(target=fetch_reply, daemon=True).start()

def update_chat_with_reply(reply, user_input):
    global conversation_history
    
    chat_area.config(state=tk.NORMAL)
    chat_area.delete("end-2l", "end-1l")
    chat_area.insert(tk.END, "AI：")
    fr.append_text_with_formula(chat_area, reply, fontsize=14)
    chat_area.insert(tk.END, "\n\n")
    chat_area.insert(tk.END, "─" * 40 + "\n\n")
    chat_area.config(state=tk.DISABLED)
    chat_area.see(tk.END)

    # 将AI回复添加到历史
    conversation_history.append({"role": "assistant", "content": reply})
    if len(conversation_history) > 40:
        conversation_history = conversation_history[-40:]

    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(f"你：{user_input}\nAI：{reply}\n\n")

    def do_learning():
        update_profile_from_conversation(user_input, reply)

    threading.Thread(target=do_learning, daemon=True).start()

def upload_and_recognize():
    global conversation_history
    
    file_path = filedialog.askopenfilename(
        title="选择图片",
        filetypes=[("图片文件", "*.jpg *.jpeg *.png *.bmp *.gif")]
    )
    if not file_path:
        return

    chat_area.config(state=tk.NORMAL)
    chat_area.insert(tk.END, f"📷 已上传图片：{os.path.basename(file_path)}\n")
    chat_area.insert(tk.END, "正在识别...\n")
    chat_area.config(state=tk.DISABLED)

    def do_recognition():
        global conversation_history  # <--- 添加这一行
        result = recognize_image(file_path)
        # 将识别结果以"用户上传的图片"形式存入历史，让AI记住
        if result and not result.startswith("❌") and not result.startswith("⏰"):
            # 将图片识别结果作为助理消息存入历史
            image_context = f"用户上传了一张图片，图片内容为：\n{result}"
            conversation_history.append({"role": "assistant", "content": image_context})
            if len(conversation_history) > 40:
                conversation_history = conversation_history[-40:]
        root.after(0, update_chat_with_recognition, result)

    threading.Thread(target=do_recognition, daemon=True).start()

def update_chat_with_recognition(result):
    chat_area.config(state=tk.NORMAL)
    # 删除 "正在识别..." 行
    chat_area.delete("end-2l", "end-1l")
    chat_area.insert(tk.END, result + "\n")
    chat_area.insert(tk.END, "-" * 40 + "\n\n")
    chat_area.config(state=tk.DISABLED)
    chat_area.see(tk.END)

def clear_history():
    global conversation_history
    if messagebox.askyesno("确认", "确定要清空所有聊天记录吗？"):
        chat_area.config(state=tk.NORMAL)
        chat_area.delete("1.0", tk.END)
        chat_area.config(state=tk.DISABLED)
        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)
        conversation_history = []

# ============================================================
# 主窗口
# ============================================================

root = tk.Tk()
root.title("AI桌面助手 - 智能聊天 + 图像识别")
root.geometry("680x580")
root.minsize(500, 400)

root.grid_rowconfigure(0, weight=1)
root.grid_rowconfigure(1, weight=0)
root.grid_rowconfigure(2, weight=0)
root.grid_rowconfigure(3, weight=0)
root.grid_columnconfigure(0, weight=1)

chat_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, state=tk.DISABLED, font=("微软雅黑", 10))
chat_area.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
chat_area.config(state=tk.NORMAL)
history_text = load_chat_history()
if history_text:
    # 使用公式渲染函数插入历史记录
    fr.insert_formula_text(chat_area, history_text, fontsize=14)
    # 确保末尾换行
    if not history_text.endswith("\n"):
        chat_area.insert(tk.END, "\n")
chat_area.config(state=tk.DISABLED)

frame_input = tk.Frame(root)
frame_input.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
frame_input.grid_columnconfigure(0, weight=1)

entry = tk.Entry(frame_input, font=("微软雅黑", 10))
entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
entry.bind("<Return>", lambda e: send_message())

send_btn = tk.Button(frame_input, text="发送", command=send_message, width=8, bg="#2196F3", fg="white")
send_btn.grid(row=0, column=1, padx=(5, 0))

frame_buttons = tk.Frame(root)
frame_buttons.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
frame_buttons.grid_columnconfigure(0, weight=1)
frame_buttons.grid_columnconfigure(1, weight=1)
frame_buttons.grid_columnconfigure(2, weight=1)

upload_btn = tk.Button(frame_buttons, text="📷 上传图片并识别", command=upload_and_recognize, bg="#FF9800", fg="white")
upload_btn.grid(row=0, column=0, sticky="ew", padx=5)

profile_btn = tk.Button(frame_buttons, text="⚙️ 修改画像", command=lambda: open_settings_window(first_run=False), bg="#9E9E9E", fg="white")
profile_btn.grid(row=0, column=1, sticky="ew", padx=5)

clear_btn = tk.Button(frame_buttons, text="🗑️ 清空记录", command=clear_history, bg="#F44336", fg="white")
clear_btn.grid(row=0, column=2, sticky="ew", padx=5)

status = tk.Label(root, text="", bd=1, relief=tk.SUNKEN, anchor=tk.W)
status.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 5))
update_status()

# ============================================================
# 启动
# ============================================================

if __name__ == "__main__":
    profile = load_profile()
    if not profile.get("manual", "").strip() and not profile.get("auto", "").strip():
        open_settings_window(first_run=True)
    root.mainloop()