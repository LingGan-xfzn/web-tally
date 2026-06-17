"""
Tally Web GUI - 潍坊工商融媒体中心
"""

import sys
import os
import json
import time
import threading
import webbrowser
import tkinter as tk
from tkinter import messagebox

# ---- 日志 ----
LOG_FILE = os.path.join(os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__)), "web-telly.log")

def flog(msg):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    except Exception:
        pass

flog("=== 软件启动 ===")

_base = os.path.dirname(os.path.abspath(__file__))
if getattr(sys, "frozen", False):
    _base = sys._MEIPASS
sys.path.insert(0, _base)

from core.network_utils import get_local_ip, test_connection, find_available_port, _cleanup_port
from core.switcher_client import SwitcherClient
from web.app import app, socketio, update_state, set_switcher_state
import web.routes, web.socket_events  # noqa
from web.socket_events import broadcast_tally_update, broadcast_connection_status

flog("模块导入成功")

APP_NAME = "web-telly"
APP_AUTHOR = "潍坊工商融媒体中心"
APP_ICON = os.path.join(_base, "app.ico")
CONFIG_FILE = os.path.join(os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__)), "config.txt")
DEFAULT_CONFIG = {"switcher_ip": "192.168.3.208", "switcher_port": "19010"}


def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            return json.load(open(CONFIG_FILE, "r", encoding="utf-8"))
    except Exception:
        pass
    return dict(DEFAULT_CONFIG)


def save_config(cfg):
    try:
        json.dump(cfg, open(CONFIG_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    except Exception:
        pass


# 全局
switcher_client = None
server_started = False
web_port = 0
local_ip = ""


class TallyApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} - {APP_AUTHOR}")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        if os.path.exists(APP_ICON):
            try:
                self.root.iconbitmap(APP_ICON)
            except Exception:
                pass

        self.config = load_config()
        self.bg = "#1a1a2e"
        self.fg = "#eee"
        self.accent = "#2a8"
        self.root.configure(bg=self.bg)
        self._build()

    def _build(self):
        p = {"padx": 16, "pady": 4}

        tk.Label(self.root, text=APP_NAME, font=("Microsoft YaHei", 18, "bold"),
                 bg=self.bg, fg=self.accent).pack(pady=(16, 0))
        tk.Label(self.root, text=f"\u00a9 {APP_AUTHOR}", font=("Microsoft YaHei", 9),
                 bg=self.bg, fg="#666").pack(pady=(0, 12))

        r1 = tk.Frame(self.root, bg=self.bg)
        r1.pack(fill="x", **p)
        tk.Label(r1, text="导播台 IP:", bg=self.bg, fg=self.fg, width=10, anchor="e").pack(side="left")
        self.ip_var = tk.StringVar(value=self.config["switcher_ip"])
        tk.Entry(r1, textvariable=self.ip_var, width=18, font=("Consolas", 11),
                 bg="#252540", fg=self.fg, insertbackground=self.fg, relief="flat").pack(side="left", padx=(4, 12))
        tk.Label(r1, text="端口:", bg=self.bg, fg=self.fg).pack(side="left")
        self.port_var = tk.StringVar(value=self.config["switcher_port"])
        tk.Entry(r1, textvariable=self.port_var, width=7, font=("Consolas", 11),
                 bg="#252540", fg=self.fg, insertbackground=self.fg, relief="flat").pack(side="left", padx=4)

        bf = tk.Frame(self.root, bg=self.bg)
        bf.pack(pady=(12, 8))
        self.connect_btn = tk.Button(bf, text="连接导播台", command=self.do_connect,
                                     font=("Microsoft YaHei", 11, "bold"),
                                     bg="#2a8", fg="#fff", activebackground="#3b9",
                                     relief="flat", padx=32, pady=6, cursor="hand2")
        self.connect_btn.pack()

        self.status_var = tk.StringVar(value="未连接")
        self.status_label = tk.Label(self.root, textvariable=self.status_var,
                                     font=("Microsoft YaHei", 10), bg=self.bg, fg="#f33")
        self.status_label.pack(pady=(4, 0))

        uf = tk.Frame(self.root, bg=self.bg)
        uf.pack(fill="x", pady=(12, 8), padx=16)

        tk.Label(uf, text="电脑端:", bg=self.bg, fg="#888", font=("Microsoft YaHei", 10)).grid(row=0, column=0, sticky="w", pady=2)
        self.comp_var = tk.StringVar(value="---")
        tk.Entry(uf, textvariable=self.comp_var, font=("Consolas", 10),
                 bg="#252540", fg="#0cf", relief="flat", state="readonly", width=32).grid(row=1, column=0, sticky="w", padx=(0, 8))
        self.open_btn = tk.Button(uf, text="打开", command=lambda: webbrowser.open(self.comp_var.get()) if self.comp_var.get() != "---" else None,
                                  font=("Microsoft YaHei", 9), bg="#2a8", fg="#fff",
                                  relief="flat", padx=12, cursor="hand2", state="disabled")
        self.open_btn.grid(row=1, column=1)

        tk.Label(uf, text="手机端:", bg=self.bg, fg="#888", font=("Microsoft YaHei", 10)).grid(row=2, column=0, sticky="w", pady=(10, 2))
        self.mob_var = tk.StringVar(value="---")
        tk.Entry(uf, textvariable=self.mob_var, font=("Consolas", 10),
                 bg="#252540", fg="#0cf", relief="flat", state="readonly", width=32).grid(row=3, column=0, sticky="w", padx=(0, 8))
        self.copy_btn = tk.Button(uf, text="复制", command=self._copy_mobile,
                                  font=("Microsoft YaHei", 9), bg="#555", fg="#fff",
                                  relief="flat", padx=12, cursor="hand2", state="disabled")
        self.copy_btn.grid(row=3, column=1)

        tk.Label(self.root, text="运行日志", bg=self.bg, fg="#666", font=("Microsoft YaHei", 9)).pack(anchor="w", padx=18, pady=(8, 2))
        self.log_text = tk.Text(self.root, height=8, width=56, font=("Consolas", 9),
                                bg="#111", fg="#aaa", relief="flat", state="disabled")
        self.log_text.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        self.log("软件启动。输入导播台 IP 和端口，点击连接。")

    # -------------------------------------------------------------------
    def do_connect(self):
        global switcher_client, server_started, web_port, local_ip

        # 防止重复点击
        if server_started:
            self.log("服务器已在运行中，请勿重复连接。")
            return

        ip = self.ip_var.get().strip()
        port_str = self.port_var.get().strip()
        if not ip:
            messagebox.showwarning("提示", "请输入导播台 IP")
            return
        try:
            port = int(port_str)
        except ValueError:
            messagebox.showwarning("提示", "端口必须是数字")
            return

        self.config["switcher_ip"] = ip
        self.config["switcher_port"] = port_str
        save_config(self.config)

        server_started = True
        self.connect_btn.config(text="正在连接...", state="disabled", bg="#888")
        self.log(f"测试连接 {ip}:{port} ...")
        flog(f"连接 {ip}:{port}")

        def _run():
            global switcher_client, web_port, local_ip

            ok, err = test_connection(ip, port, timeout=4)
            if not ok:
                self.root.after(0, lambda: self._conn_fail(err))
                return

            flog("TCP OK")
            local_ip = get_local_ip(switcher_ip=ip)
            web_port = find_available_port(7210)
            flog(f"IP={local_ip} Port={web_port}")

            update_state(switcher_ip=ip, web_ip=local_ip, web_port=web_port)

            switcher_client = SwitcherClient(ip, port=port)
            switcher_client.on_state_change = _on_state_change
            switcher_client.start()
            flog("Switcher启动")

            # 清理旧端口
            _cleanup_port(web_port)

            # 界面就绪
            self.root.after(0, self._ready_ui)

            # 启动 Web 服务（阻塞）
            try:
                flog(f"Web启动 port={web_port}")
                socketio.run(app, host="0.0.0.0", port=web_port,
                            debug=False, allow_unsafe_werkzeug=True, use_reloader=False)
            except Exception as e:
                flog(f"Web异常: {e}")
                self.root.after(0, lambda: self.log(f"服务异常: {e}"))

        threading.Thread(target=_run, daemon=True).start()

    def _conn_fail(self, err):
        global server_started
        server_started = False
        self.log(f"连接失败: {err}")
        self.connect_btn.config(text="连接导播台", state="normal", bg="#2a8")
        flog(f"连接失败: {err}")

    def _ready_ui(self):
        comp = f"http://{local_ip}:{web_port}/director"
        mob = f"http://{local_ip}:{web_port}"
        self.comp_var.set(comp)
        self.mob_var.set(mob)
        self.open_btn.config(state="normal")
        self.copy_btn.config(state="normal")
        self.connect_btn.config(text="已连接（运行中）", state="disabled", bg="#555")
        self.status_var.set(f"已连接 {self.config['switcher_ip']}:{self.config['switcher_port']}")
        self.status_label.config(fg="#0f0")
        self.log(f"Web 服务已启动")
        self.log(f"电脑端: {comp}")
        self.log(f"手机端: {mob}")
        flog("UI就绪")

    def _copy_mobile(self):
        url = self.mob_var.get()
        if url and url != "---":
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            self.log("手机端地址已复制")

    def log(self, msg):
        self.log_text.config(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def on_close(self):
        global switcher_client
        if switcher_client:
            switcher_client.stop()
        flog("=== 关闭 ===")
        self.root.destroy()
        os._exit(0)


def _on_state_change(pgm, pvw, connected, transition=0):
    set_switcher_state(pgm, pvw, connected, transition)
    broadcast_tally_update(pgm, pvw, transition)
    broadcast_connection_status(connected)


if __name__ == "__main__":
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    root = tk.Tk()
    TallyApp(root)
    root.mainloop()
