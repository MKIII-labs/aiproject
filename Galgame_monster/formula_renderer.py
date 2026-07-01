"""
公式渲染模块 - 将 LaTeX 公式渲染为图片嵌入 tkinter Text 组件
依赖：matplotlib
"""

import re
import io
import matplotlib.pyplot as plt
from PIL import Image, ImageTk
import tkinter as tk

# 全局引用缓存，防止图片被垃圾回收
_image_refs = []


def render_latex_to_image(latex_str, fontsize=14, dpi=100):
    """将 LaTeX 公式渲染为 PIL Image 对象"""
    try:
        fig = plt.figure(figsize=(0.01, 0.01))
        fig.text(0.5, 0.5, f"${latex_str}$", fontsize=fontsize, 
                 ha='center', va='center')
        plt.axis('off')
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', 
                    pad_inches=0.03, transparent=True, dpi=dpi)
        plt.close(fig)
        buf.seek(0)
        return Image.open(buf)
    except Exception as e:
        print(f"[公式渲染警告] {latex_str} -> {e}")
        return None


def insert_formula_text(widget, text, fontsize=14):
    """将文本中的 $...$、\[...\]、\(...\) 公式替换为图片插入到 tkinter Text 组件"""
    global _image_refs
    
    # 支持三种格式：$...$（不跨行）、\[...\]（可跨行）、\(...\)（不跨行）
    pattern = r'\$(.+?)\$|\\\[([\s\S]+?)\\\]|\\\((.+?)\\\)'
    
    last_end = 0
    for match in re.finditer(pattern, text):
        # 插入匹配前的普通文本
        if match.start() > last_end:
            widget.insert(tk.END, text[last_end:match.start()])
        
        # 提取公式内容（三个分组中有一个是非空的）
        formula = match.group(1) or match.group(2) or match.group(3)
        if formula and formula.strip():
            img = render_latex_to_image(formula.strip(), fontsize)
            if img:
                photo = ImageTk.PhotoImage(img)
                _image_refs.append(photo)
                widget.image_create(tk.END, image=photo)
            else:
                # 渲染失败时保留原始公式文本
                widget.insert(tk.END, match.group(0))
        else:
            widget.insert(tk.END, match.group(0))
        
        last_end = match.end()
    
    # 插入剩余的普通文本
    if last_end < len(text):
        widget.insert(tk.END, text[last_end:])


def append_text_with_formula(widget, text, fontsize=14):
    """在 widget 末尾追加带公式的文本，并确保末尾有换行"""
    widget.config(state=tk.NORMAL)
    insert_formula_text(widget, text, fontsize)
    # 强制在末尾添加两个换行，确保下一条消息前有空行
    widget.insert(tk.END, "\n\n")
    widget.config(state=tk.DISABLED)