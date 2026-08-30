import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import threading
import os
import sys

class MergeApp:
    def __init__(self, root):
        self.root = root
        root.title("视频音频合并工具")
        root.geometry("500x260")
        root.resizable(False, False)

        # 变量
        self.video1_path = tk.StringVar()
        self.video2_path = tk.StringVar()
        self.output_path = tk.StringVar()

        # 界面布局
        tk.Label(root, text="视频1（无声音，仅画面）:").grid(row=0, column=0, padx=10, pady=10, sticky='w')
        tk.Entry(root, textvariable=self.video1_path, width=40).grid(row=0, column=1, padx=5)
        tk.Button(root, text="浏览...", command=self.select_video1).grid(row=0, column=2, padx=5)

        tk.Label(root, text="视频2（提供音频）:").grid(row=1, column=0, padx=10, pady=10, sticky='w')
        tk.Entry(root, textvariable=self.video2_path, width=40).grid(row=1, column=1, padx=5)
        tk.Button(root, text="浏览...", command=self.select_video2).grid(row=1, column=2, padx=5)

        tk.Label(root, text="输出文件:").grid(row=2, column=0, padx=10, pady=10, sticky='w')
        tk.Entry(root, textvariable=self.output_path, width=40).grid(row=2, column=1, padx=5)
        tk.Button(root, text="浏览...", command=self.select_output).grid(row=2, column=2, padx=5)

        self.merge_btn = tk.Button(root, text="开始合并", command=self.start_merge, bg="#4CAF50", fg="white", height=2)
        self.merge_btn.grid(row=3, column=0, columnspan=3, pady=20, padx=10, sticky='we')

        self.status_label = tk.Label(root, text="就绪", fg="blue")
        self.status_label.grid(row=4, column=0, columnspan=3)

    def select_video1(self):
        path = filedialog.askopenfilename(
            title="选择视频1（画面来源）",
            filetypes=[("视频文件", "*.mp4 *.avi *.mkv *.mov *.flv"), ("所有文件", "*.*")]
        )
        if path:
            self.video1_path.set(path)

    def select_video2(self):
        path = filedialog.askopenfilename(
            title="选择视频2（音频来源）",
            filetypes=[("视频文件", "*.mp4 *.avi *.mkv *.mov *.flv"), ("所有文件", "*.*")]
        )
        if path:
            self.video2_path.set(path)

    def select_output(self):
        path = filedialog.asksaveasfilename(
            title="保存输出文件",
            defaultextension=".mp4",
            filetypes=[("MP4 文件", "*.mp4")]
        )
        if path:
            self.output_path.set(path)

    def start_merge(self):
        v1 = self.video1_path.get().strip()
        v2 = self.video2_path.get().strip()
        out = self.output_path.get().strip()

        if not v1 or not v2 or not out:
            messagebox.showerror("错误", "请完整填写所有文件路径")
            return

        # 检查 ffmpeg 是否可用
        if not self.check_ffmpeg():
            messagebox.showerror("错误", "未找到 FFmpeg，请确保已安装并加入系统 PATH")
            return

        # 获取视频1的时长
        try:
            duration = self.get_video_duration(v1)
            if duration is None:
                raise ValueError("无法获取视频时长")
        except Exception as e:
            messagebox.showerror("错误", f"获取视频1时长失败:\n{e}")
            return

        # 构建 ffmpeg 命令
        cmd = [
            "ffmpeg",
            "-i", v1,
            "-i", v2,
            "-map", "0:v:0",      # 只取视频1的视频轨
            "-map", "1:a:0",      # 只取视频2的音频轨
            "-c:v", "copy",       # 视频流直接复制，不重新编码
            "-c:a", "aac",        # 音频编码为 AAC（兼容性好）
            "-t", str(duration),  # 限制输出时长为视频1时长
            "-y",                 # 覆盖输出文件
            out
        ]

        # 禁用按钮，显示状态
        self.merge_btn.config(state=tk.DISABLED)
        self.status_label.config(text="正在合并，请稍候...", fg="orange")

        # 在子线程中执行，避免界面卡死
        threading.Thread(target=self.run_ffmpeg, args=(cmd,), daemon=True).start()

    def run_ffmpeg(self, cmd):
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )
            stdout, stderr = process.communicate()

            def on_finish():
                self.merge_btn.config(state=tk.NORMAL)
                if process.returncode == 0:
                    self.status_label.config(text="合并完成！", fg="green")
                    messagebox.showinfo("成功", "视频音频合并完成！")
                else:
                    self.status_label.config(text="合并失败", fg="red")
                    # 显示错误信息的前500字符
                    error_msg = stderr[-500:] if stderr else "未知错误"
                    messagebox.showerror("错误", f"合并失败:\n{error_msg}")

            self.root.after(0, on_finish)

        except Exception as e:
            def on_error():
                self.merge_btn.config(state=tk.NORMAL)
                self.status_label.config(text="发生异常", fg="red")
                messagebox.showerror("错误", f"执行过程中发生异常:\n{e}")
            self.root.after(0, on_error)

    def check_ffmpeg(self):
        """检查 ffmpeg 和 ffprobe 是否可用"""
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            subprocess.run(["ffprobe", "-version"], capture_output=True, check=True)
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def get_video_duration(self, video_path):
        """使用 ffprobe 获取视频时长（秒）"""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        if result.returncode == 0:
            return result.stdout.strip()
        return None


if __name__ == "__main__":
    root = tk.Tk()
    app = MergeApp(root)
    root.mainloop()