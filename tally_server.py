"""
Tally Web 系统 - 主程序入口
============================
双击 start.bat 或 python tally_server.py 启动

功能：
1. 输入导播台 IP，测试连接
2. 在本机 LAN IP 上开放 Web 网站（端口默认 7210）
3. 后台监控导播台 PGM/PVW 状态
4. 手机/iPad 打开网站选择机位，实时显示 Tally 指示
"""

import sys
import os
import atexit
import signal
import threading
# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.network_utils import get_local_ip, find_available_port, test_connection, _cleanup_port
from core.switcher_client import SwitcherClient
from web.app import (
    app, socketio, get_state, update_state,
    set_switcher_state,
)
from web.socket_events import (
    broadcast_tally_update,
    broadcast_connection_status,
)
from web import routes  # noqa: F401 - 注册路由
from web import socket_events  # noqa: F401 - 注册 SocketIO 事件

# ---------------------------------------------------------------------------
# 全局变量
# ---------------------------------------------------------------------------
switcher_client = None
last_pgm = 0
last_pvw = 0



def on_switcher_state_change(pgm, pvw, connected, transition=0):
    """导播台状态变化回调（在 switcher_client 的工作线程中调用）"""
    global last_pgm, last_pvw

    changed = set_switcher_state(pgm, pvw, connected, transition)

    # 推送到所有 WebSocket 客户端
    if changed:
        if last_pgm != pgm or last_pvw != pvw:
            if transition:
                print(f"[状态] PGM={pgm}, PVW={pvw} (过渡中)")
            else:
                print(f"[状态] PGM={pgm}, PVW={pvw}")
            last_pgm = pgm
            last_pvw = pvw
        broadcast_tally_update(pgm, pvw, transition)

    # 连接状态变化
    broadcast_connection_status(connected)


def main():
    global switcher_client

    # -----------------------------------------------------------------------
    # 1. 启动横幅
    # -----------------------------------------------------------------------
    print("=" * 50)
    print("    Tally Web 系统 v1.0")
    print("    导播台 Tally 监看 + Web 显示")
    print("=" * 50)
    print()

    # -----------------------------------------------------------------------
    # 2. 输入导播台 IP
    # -----------------------------------------------------------------------
    while True:
        ip = input("请输入导播台 IP 地址: ").strip()
        if not ip:
            print("[提示] IP 地址不能为空，请重新输入\n")
            continue

        print(f"\n正在测试连接 {ip}:19010 ...")
        ok, err = test_connection(ip)
        if ok:
            print(f"[成功] 导播台 {ip}:19010 连接正常！\n")
            break
        else:
            print(f"[失败] {err}")
            retry = input("是否重新输入？(y/n，默认 y): ").strip().lower()
            if retry == "n":
                print("已取消，程序退出。")
                return
            print()

    update_state(switcher_ip=ip)

    # -----------------------------------------------------------------------
    # 3. 获取本机 IP 和可用端口
    # -----------------------------------------------------------------------
    local_ip = get_local_ip(switcher_ip=ip)
    web_port = find_available_port(7210)

    if web_port != 7210:
        print(f"[端口] 7210 已被占用，自动使用端口 {web_port}")

    update_state(web_ip=local_ip, web_port=web_port)

    web_url = f"http://{local_ip}:{web_port}"
    print(f"[网站] Tally Web 已启动:")
    print(f"       电脑导播位: {web_url}/director")
    print(f"       手机选机位: {web_url}")
    print()

    # -----------------------------------------------------------------------
    # 4. 启动导播台监听客户端
    # -----------------------------------------------------------------------
    switcher_client = SwitcherClient(ip, port=19010)
    switcher_client.on_state_change = on_switcher_state_change
    switcher_client.start()

    # -----------------------------------------------------------------------
    # 5. 启动 Flask + SocketIO 服务（先清理旧进程）
    # -----------------------------------------------------------------------
    _cleanup_port(web_port)
    print("[服务] 正在启动 Web 服务器...")
    print("[提示] 按 Ctrl+C 可停止服务\n")

    def _shutdown():
        """确保退出时清理资源"""
        if switcher_client:
            switcher_client.stop()

    atexit.register(_shutdown)

    try:
        socketio.run(
            app,
            host="0.0.0.0",
            port=web_port,
            debug=True,
            allow_unsafe_werkzeug=True,
            use_reloader=False,
        )
    except KeyboardInterrupt:
        print("\n[服务] 正在停止...")
    finally:
        _shutdown()
        print("[服务] 已停止。")

if __name__ == "__main__":
    main()
