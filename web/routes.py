"""
HTTP 路由定义
"""

import re
from flask import render_template, jsonify, redirect, url_for, request
from .app import app, get_state, get_channel_list, MAX_CHANNELS, SPECIAL_CHANNELS


def is_mobile():
    """检测是否手机/平板访问"""
    ua = request.headers.get("User-Agent", "").lower()
    mobile_kw = ["mobile", "android", "iphone", "ipad", "ipod", "blackberry", "windows phone"]
    return any(kw in ua for kw in mobile_kw)


@app.route("/")
def index():
    """手机端机位选择页，电脑自动跳转导播位"""
    if not is_mobile():
        return redirect("/director")
    state = get_state()
    return render_template("index.html", state=state, max_channels=MAX_CHANNELS)


@app.route("/director")
def director():
    """导播监看页 - 同时显示 4 个机位 + 4 个特殊通道的颜色状态"""
    state = get_state()
    return render_template("director.html", state=state,
                           max_channels=MAX_CHANNELS,
                           special_channels=SPECIAL_CHANNELS)


@app.route("/tally/<int:channel>")
def tally(channel):
    """手机端 Tally 全屏显示页（机位 1-4 或导播位 0）"""
    if channel == 0:
        return render_template("tally.html", channel=0, label="导播",
                               special_channels=SPECIAL_CHANNELS)
    if channel < 1 or channel > MAX_CHANNELS:
        return f"机位号必须在 1-{MAX_CHANNELS} 之间", 400
    return render_template("tally.html", channel=channel, label=str(channel))


@app.route("/api/state")
def api_state():
    """返回当前全局状态"""
    state = get_state()
    owners_simple = {ch: (owner[:8] + "..." if owner else None)
                     for ch, owner in state["owners"].items()}
    return jsonify({
        "switcher_ip": state["switcher_ip"],
        "switcher_connected": state["switcher_connected"],
        "pgm": state["pgm"],
        "pvw": state["pvw"],
        "transition": state["transition"],
        "owners": owners_simple,
        "web_ip": state["web_ip"],
        "web_port": state["web_port"],
    })


@app.route("/api/channels")
def api_channels():
    """返回机位占用列表"""
    channels = get_channel_list()
    return jsonify({
        "channels": {ch: bool(owner) for ch, owner in channels.items()}
    })
