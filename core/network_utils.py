"""
网络工具模块 - 本机IP获取、端口检测、导播台连通性测试
"""

import sys
import socket
import ipaddress


def get_all_local_ips():
    """
    获取本机所有 IPv4 地址（排除回环地址）

    Returns:
        list[str]: IP 地址列表
    """
    ips = []
    hostname = socket.gethostname()
    try:
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127.") and ip not in ips:
                ips.append(ip)
    except socket.gaierror:
        pass
    return ips


def get_local_ip(switcher_ip=None):
    """
    获取本机与导播台同一网段的 IP 地址

    Args:
        switcher_ip: 导播台 IP，用于匹配同一网段

    Returns:
        str: 本机 IP 地址
    """
    # 如果提供了导播台 IP，优先找同网段的
    if switcher_ip:
        try:
            sw_network = ipaddress.IPv4Network(switcher_ip + "/24", strict=False)
            for ip in get_all_local_ips():
                try:
                    if ipaddress.IPv4Address(ip) in sw_network:
                        return ip
                except ipaddress.AddressValueError:
                    continue
        except (ipaddress.AddressValueError, ValueError):
            pass

    # 回退方案1：用 UDP 连接探测出口 IP
    ips = get_all_local_ips()
    if ips:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(1)
            s.connect(("8.8.8.8", 80))
            candidate = s.getsockname()[0]
            s.close()
            # 如果候选 IP 在本机 IP 列表中就用它，否则用列表第一个
            if candidate in ips:
                return candidate
        except OSError:
            pass
        return ips[0]

    # 回退方案2：hostname 解析
    try:
        return socket.gethostbyname(socket.gethostname())
    except OSError:
        return "127.0.0.1"


def find_available_port(start_port=7210, max_attempts=10):
    """
    从指定端口开始查找第一个可用端口

    Args:
        start_port: 起始端口号
        max_attempts: 最大尝试次数

    Returns:
        int: 可用端口号，如果都不可用则返回 start_port（后续启动会报错提示用户）
    """
    for offset in range(max_attempts):
        port = start_port + offset
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("0.0.0.0", port))
            s.close()
            return port
        except OSError:
            continue
    return start_port  # 都不可用，返回默认值让后续错误提示


def test_connection(ip, port=19010, timeout=3):
    """
    测试导播台 TCP 连接是否可达

    Args:
        ip: 导播台 IP 地址
        port: 导播台端口，默认 19010
        timeout: 连接超时秒数

    Returns:
        tuple: (成功bool, 错误信息str)
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((ip, port))
        s.close()
        return True, ""
    except socket.timeout:
        return False, f"连接超时（{timeout}秒），请检查 IP 地址和网络连接"
    except ConnectionRefusedError:
        return False, f"连接被拒绝，导播台可能未开机或端口 {port} 未开放"
    except socket.gaierror:
        return False, f"无效的 IP 地址: {ip}"
    except OSError as e:
        return False, f"网络错误: {e}"


def _cleanup_port(port):
    """Windows: 杀掉占用指定端口的残留进程"""
    import subprocess
    if sys.platform != "win32":
        return
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True, timeout=10
        )
        pids = set()
        for line in result.stdout.splitlines():
            if f":{port}" in line and "LISTENING" in line:
                parts = line.strip().split()
                pids.add(parts[-1])
        for pid in pids:
            subprocess.run(["taskkill", "/F", "/PID", pid],
                           capture_output=True, timeout=5)
    except Exception:
        pass
