"""
Flask + SocketIO 应用创建，全局状态管理
导播位（director）不锁定，可多人同时选择
机位 1-4 独占，一人一位
"""

import os
import threading
from flask import Flask
from flask_socketio import SocketIO

# 项目根目录
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------------------
# 全局状态（内存存储，线程安全）
# ---------------------------------------------------------------------------
_state_lock = threading.Lock()
MAX_CHANNELS = 4

# 导播位专属通道（不分配、不锁定、仅监看）
# {value: "显示名称"}
SPECIAL_CHANNELS = {
    3010: "Still1",
    3020: "Still2",
    4001: "AUX",
    5001: "S/SRC",
}

_state = {
    "switcher_ip": "",
    "switcher_connected": False,
    "pgm": 0,        # 当前 PGM 通道号，0=未知
    "pvw": 0,        # 当前 PVW 通道号，0=未知
    "transition": 0,  # 0=空闲, 1=过渡中（AUTO 按下时 PGM+PVW 同时红）
    "owners": {},    # {channel: socketio_sid}，仅 1-4 机位锁定，导播位不在此
    "web_ip": "",
    "web_port": 7210,
}


def get_state():
    with _state_lock:
        return dict(_state)


def update_state(**kwargs):
    with _state_lock:
        _state.update(kwargs)


def set_switcher_state(pgm, pvw, connected, transition=0):
    with _state_lock:
        changed = (
            _state["pgm"] != pgm
            or _state["pvw"] != pvw
            or _state["switcher_connected"] != connected
            or _state["transition"] != transition
        )
        _state["pgm"] = pgm
        _state["pvw"] = pvw
        _state["switcher_connected"] = connected
        _state["transition"] = transition
        return changed


def assign_channel(channel, sid, force=False):
    """
    为用户分配机位（仅 1-4，独占）
    导播位不需要调用此函数（无需锁定）
    force=True 时强制覆盖（用于 tally 页重连）
    返回: (成功bool, 错误信息str)
    """
    with _state_lock:
        if channel < 1 or channel > MAX_CHANNELS:
            return False, f"机位号必须在 1-{MAX_CHANNELS} 之间"

        # 先释放该用户之前占用的机位
        for ch, owner in list(_state["owners"].items()):
            if owner == sid:
                _state["owners"][ch] = None

        # 检查目标机位是否空闲
        current_owner = _state["owners"].get(channel)
        if current_owner and current_owner != sid:
            if force:
                # 强制释放旧占用者（tally 页重连场景）
                _state["owners"][channel] = sid
                return True, ""
            return False, "该机位已被占用"

        _state["owners"][channel] = sid
        return True, ""


def force_release_channel(channel):
    """管理员强制释放指定机位"""
    with _state_lock:
        if channel in _state["owners"]:
            _state["owners"][channel] = None
            return True
    return False


def release_channel_by_sid(sid):
    """释放指定 session 占用的所有机位"""
    released = []
    with _state_lock:
        for ch, owner in list(_state["owners"].items()):
            if owner == sid:
                _state["owners"][ch] = None
                released.append(ch)
    return released


def get_channel_of_sid(sid):
    """获取指定 session 当前占用的机位号，没有则返回 None"""
    with _state_lock:
        for ch, owner in _state["owners"].items():
            if owner == sid:
                return ch
    return None


def get_channel_list():
    """获取所有机位占用情况（仅 1-4）"""
    with _state_lock:
        return {
            ch: _state["owners"].get(ch)
            for ch in range(1, MAX_CHANNELS + 1)
        }


# ---------------------------------------------------------------------------
# Flask 应用创建
# ---------------------------------------------------------------------------
app = Flask(
    __name__,
    template_folder=os.path.join(ROOT_DIR, "templates"),
    static_folder=os.path.join(ROOT_DIR, "static"),
)
app.config["SECRET_KEY"] = "omnitally-secret-key-2024"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")
