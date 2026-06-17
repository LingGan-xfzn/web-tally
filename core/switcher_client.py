"""
导播台 TCP 客户端 - 连接导播台端口 19010，实时解析 JSON 获取 PGM/PVW 状态

参考 OmniTally 固件中的 Switcher_OSEE_PreJson() 方法:
- 接收原始 TCP 字节流
- 过滤不可打印字符（保留 {}[]）
- 提取完整的 {...} JSON 对象
- 解析 "id":"pgmIndex" / "id":"pvwIndex"
"""

import socket
import json
import threading
import time


class SwitcherClient:
    """导播台 TCP 客户端，后台线程持续监控 PGM/PVW 状态"""

    def __init__(self, ip, port=19010):
        self.ip = ip
        self.port = port
        self._socket = None
        self._thread = None
        self._stop_event = threading.Event()
        self._connected = False
        self._lock = threading.Lock()

        # 当前状态
        self.pgm = 0  # 0 = 未知
        self.pvw = 0
        self.transition = 0  # 0=空闲, 1=过渡中

        # 状态变化回调: callback(pgm, pvw, connected, transition)
        self.on_state_change = None

        # 接收缓冲区
        self._buffer = ""

    @property
    def connected(self):
        with self._lock:
            return self._connected

    @connected.setter
    def connected(self, val):
        with self._lock:
            self._connected = val

    def start(self):
        """启动后台监听线程"""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        """停止监听线程"""
        self._stop_event.set()
        self._disconnect()
        if self._thread:
            self._thread.join(timeout=3)

    def _disconnect(self):
        """断开 TCP 连接"""
        try:
            if self._socket:
                self._socket.close()
        except OSError:
            pass
        self._socket = None
        was_connected = self.connected
        self.connected = False
        if was_connected:
            self._notify()

    def _connect(self):
        """建立 TCP 连接"""
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(3)
            self._socket.connect((self.ip, self.port))
            self._socket.settimeout(0.5)  # 读超时设为 0.5 秒，方便检查 stop_event
            self.connected = True
            self._notify()
            return True
        except OSError:
            self._socket = None
            return False

    def _notify(self):
        """触发状态变化回调"""
        if self.on_state_change:
            try:
                self.on_state_change(self.pgm, self.pvw, self.connected, self.transition)
            except Exception as e:
                print(f"[错误] 回调异常: {e}")

    def _parse_json_objects(self, data):
        """
        从原始 TCP 数据中提取完整的 JSON 对象
        参考 OmniTally Switcher_OSEE_PreJson()
        """
        # 过滤不可打印字符，保留 JSON 关键字符
        filtered = ""
        for ch in data:
            if ch.isprintable() or ch in "{}[]":
                filtered += ch

        self._buffer += filtered

        # 循环提取完整的 {...} 对象
        while True:
            start = self._buffer.find("{")
            if start < 0:
                break
            end = self._buffer.find("}", start)
            if end < 0:
                break
            json_str = self._buffer[start:end + 1]
            self._buffer = self._buffer[end + 1:]
            self._process_json(json_str)

    def _process_json(self, json_str):
        """解析单个 JSON 对象，提取 pgmIndex / pvwIndex"""
        try:
            obj = json.loads(json_str)
        except json.JSONDecodeError:
            return  # 忽略无法解析的 JSON

        obj_id = obj.get("id", "")
        value_arr = obj.get("value", [])

        if not value_arr or not isinstance(value_arr, list):
            return

        raw_val = int(value_arr[0])
        channel = raw_val  # 直接使用 value[0]，不做偏移

        changed = False

        if obj_id == "pgmIndex":
            if self.pgm != channel:
                self.pgm = channel
                changed = True
        elif obj_id == "pvwIndex":
            if self.pvw != channel:
                self.pvw = channel
                changed = True
        elif obj_id == "transitionStatus":
            ts = raw_val
            if self.transition != ts:
                self.transition = ts
                changed = True

        if changed:
            self._notify()

    def _run(self):
        """后台线程主循环：连接 → 接收 → 解析 → 重连"""
        while not self._stop_event.is_set():
            if not self.connected:
                print(f"[导播台] 正在连接 {self.ip}:{self.port}...")
                if self._connect():
                    print(f"[导播台] 已连接 {self.ip}:{self.port}")
                else:
                    print(f"[导播台] 连接失败，3秒后重试...")
                    self._stop_event.wait(3)
                    continue

            try:
                data = self._socket.recv(4096)
                if data:
                    self._parse_json_objects(data.decode("utf-8", errors="replace"))
                else:
                    # 空数据 = 对方关闭连接
                    print("[导播台] 连接断开，3秒后重连...")
                    self._disconnect()
                    self._stop_event.wait(3)

            except socket.timeout:
                # 读超时，正常情况，继续循环
                continue
            except (ConnectionResetError, BrokenPipeError, OSError) as e:
                print(f"[导播台] 连接异常: {e}，3秒后重连...")
                self._disconnect()
                self._stop_event.wait(3)
