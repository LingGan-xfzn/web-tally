"""
SocketIO WebSocket 事件处理
"""

from flask import request
from flask_socketio import emit
from .app import (
    socketio, get_state, update_state,
    assign_channel, release_channel_by_sid,
    force_release_channel, get_channel_list, MAX_CHANNELS,
)


@socketio.on("connect")
def on_connect():
    """客户端连接，立即发送当前状态"""
    state = get_state()
    emit("tally_update", {
        "pgm": state["pgm"],
        "pvw": state["pvw"],
    })
    emit("connection_status", {
        "connected": state["switcher_connected"],
    })
    broadcast_channel_list()


@socketio.on("disconnect")
def on_disconnect():
    """客户端断开，释放其占用的机位"""
    sid = request.sid
    released = release_channel_by_sid(sid)
    if released:
        print(f"[WebSocket] {sid[:8]}... 断开，释放机位 {released}")
        broadcast_channel_list()


@socketio.on("select_channel")
def on_select_channel(data):
    """用户请求占用机位（1-4，独占），tally页重连时带 force=true"""
    sid = request.sid
    channel = data.get("channel", 0)
    force = data.get("force", False)

    if not isinstance(channel, int) or channel < 1 or channel > MAX_CHANNELS:
        emit("channel_error", {"reason": f"无效的机位号，请选择 1-{MAX_CHANNELS}"})
        return

    ok, err = assign_channel(channel, sid, force=force)
    if ok:
        print(f"[WebSocket] {sid[:8]}... 占用机位 {channel}" + (" (force)" if force else ""))
        emit("channel_assigned", {"channel": channel})
        broadcast_channel_list()
    else:
        emit("channel_rejected", {"reason": err})


@socketio.on("force_release")
def on_force_release(data):
    """导播位管理员强制释放指定机位"""
    channel = data.get("channel", 0)
    if channel < 1 or channel > MAX_CHANNELS:
        emit("force_release_result", {"ok": False, "reason": "无效机位号"})
        return
    if force_release_channel(channel):
        print(f"[管理] 强制释放机位 {channel}")
        broadcast_channel_list()
        emit("force_release_result", {"ok": True, "channel": channel})
    else:
        emit("force_release_result", {"ok": False, "reason": "机位未被占用"})


@socketio.on("release_channel")
def on_release_channel(data=None):
    """用户主动释放机位"""
    sid = request.sid
    released = release_channel_by_sid(sid)
    if released:
        print(f"[WebSocket] {sid[:8]}... 释放机位 {released}")
        emit("channel_released", {"channels": released})
        broadcast_channel_list()


@socketio.on("get_channel_list")
def on_get_channel_list(data=None):
    """客户端请求机位列表"""
    emit("channel_list", {"owners": get_channel_list()})


def broadcast_tally_update(pgm, pvw, transition=0):
    """向所有客户端广播 PGM/PVW 状态"""
    socketio.emit("tally_update", {
        "pgm": pgm,
        "pvw": pvw,
        "transition": transition,
    })


def broadcast_connection_status(connected):
    """向所有客户端广播导播台连接状态"""
    socketio.emit("connection_status", {"connected": connected})


def broadcast_channel_list():
    """向所有客户端广播机位占用列表（仅 1-4）"""
    socketio.emit("channel_list", {"owners": get_channel_list()})
