#!/usr/bin/env python3

"""
H-Check v1.1
System Information & Diagnostics Tool

Lightweight system diagnostic utility written in Python.
Provides detailed information about system, hardware, storage,
network, processes, services, security and overall system health.

Standard-library only.
"""

from __future__ import annotations

import argparse
import datetime
import getpass
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import time


VERSION = "1.1.0"


# ============================================================
# COLORS
# ============================================================

RESET = "\033[0m"
BOLD = "\033[1m"
CYAN = "\033[96m"
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
WHITE = "\033[97m"
GRAY = "\033[90m"


# ============================================================
# GENERAL HELPERS
# ============================================================

def command_exists(command: str) -> bool:
    return shutil.which(command) is not None


def run_command(command: list[str], timeout: int = 5) -> str:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return result.stdout.strip()
    except (
        subprocess.TimeoutExpired,
        FileNotFoundError,
        PermissionError,
        OSError,
    ):
        return ""


def bytes_to_gb(value: int | float) -> float:
    return value / (1024 ** 3)


def format_bytes(value: int | float) -> str:
    value = float(value)

    units = ["B", "KB", "MB", "GB", "TB", "PB"]

    for unit in units:
        if value < 1024:
            return f"{value:.1f} {unit}"
        value /= 1024

    return f"{value:.1f} PB"


def section(title: str) -> None:
    print()
    print(f"{BOLD}{CYAN}[ {title.upper()} ]{RESET}")
    print("─" * 62)


def item(label: str, value: object) -> None:
    print(f"{WHITE}{label:<22}{RESET}: {value}")


def status(label: str, value: str, level: str = "ok") -> None:
    symbols = {
        "ok": f"{GREEN}✓{RESET}",
        "warning": f"{YELLOW}⚠{RESET}",
        "critical": f"{RED}✗{RESET}",
        "info": f"{CYAN}•{RESET}",
    }

    symbol = symbols.get(level, symbols["info"])
    print(f" {symbol} {label:<20}: {value}")


def banner() -> None:
    print(
        f"""
{BOLD}{CYAN}
╔══════════════════════════════════════════════════════════════╗
║                         H-CHECK                              ║
║              SYSTEM INFORMATION & DIAGNOSTICS               ║
║                         v{VERSION:<29}║
╚══════════════════════════════════════════════════════════════╝
{RESET}"""
    )


# ============================================================
# SYSTEM
# ============================================================

def get_uptime() -> str:
    try:
        with open("/proc/uptime", "r", encoding="utf-8") as file:
            seconds = int(float(file.read().split()[0]))

        days, seconds = divmod(seconds, 86400)
        hours, seconds = divmod(seconds, 3600)
        minutes, _ = divmod(seconds, 60)

        return f"{days}d {hours}h {minutes}m"

    except (FileNotFoundError, ValueError):
        return "Unavailable"


def get_boot_time() -> str:
    try:
        with open("/proc/stat", "r", encoding="utf-8") as file:
            for line in file:
                if line.startswith("btime"):
                    timestamp = int(line.split()[1])
                    return datetime.datetime.fromtimestamp(
                        timestamp
                    ).strftime("%Y-%m-%d %H:%M:%S")
    except (FileNotFoundError, ValueError, OSError):
        pass

    return "Unavailable"


def get_logged_users() -> list[str]:
    output = run_command(["who"])

    if not output:
        return []

    users = []

    for line in output.splitlines():
        parts = line.split()

        if parts:
            users.append(parts[0])

    return sorted(set(users))


def get_shell() -> str:
    return os.environ.get("SHELL", "Unknown")


def get_desktop() -> str:
    for variable in (
        "XDG_CURRENT_DESKTOP",
        "XDG_SESSION_DESKTOP",
        "DESKTOP_SESSION",
    ):
        value = os.environ.get(variable)

        if value:
            return value

    return "Unknown"


def get_virtualization() -> str:
    if command_exists("systemd-detect-virt"):
        result = run_command(["systemd-detect-virt"])

        if result and result != "none":
            return result

        if result == "none":
            return "None detected"

    return "Unknown"


def system_info() -> dict:
    info = {
        "hostname": socket.gethostname(),
        "user": getpass.getuser(),
        "os": platform.system(),
        "distribution": platform.platform(),
        "kernel": platform.release(),
        "architecture": platform.machine(),
        "processor": platform.processor() or "Unknown",
        "python": platform.python_version(),
        "uptime": get_uptime(),
        "boot_time": get_boot_time(),
        "shell": get_shell(),
        "desktop": get_desktop(),
        "virtualization": get_virtualization(),
        "logged_users": get_logged_users(),
        "timezone": time.strftime("%Z"),
    }

    section("System")

    item("Hostname", info["hostname"])
    item("Operating System", info["os"])
    item("Distribution", info["distribution"])
    item("Kernel", info["kernel"])
    item("Architecture", info["architecture"])
    item("Processor", info["processor"])
    item("Python", info["python"])
    item("Uptime", info["uptime"])
    item("Boot time", info["boot_time"])
    item("Current user", info["user"])
    item("Shell", info["shell"])
    item("Desktop", info["desktop"])
    item("Virtualization", info["virtualization"])
    item("Timezone", info["timezone"])

    users = info["logged_users"]

    if users:
        item("Logged users", ", ".join(users))
    else:
        item("Logged users", "None detected")

    return info


# ============================================================
# HARDWARE
# ============================================================

def get_cpu_info() -> dict:
    cpu = {
        "model": platform.processor() or "Unknown",
        "cores": os.cpu_count() or 0,
        "threads": os.cpu_count() or 0,
        "frequency": "Unknown",
    }

    output = run_command(["lscpu"])

    if output:
        for line in output.splitlines():
            if ":" not in line:
                continue

            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()

            if key == "Model name":
                cpu["model"] = value

            elif key == "CPU(s)":
                cpu["threads"] = value

            elif key == "Core(s) per socket":
                cpu["cores_per_socket"] = value

            elif key == "CPU MHz":
                cpu["frequency"] = f"{value} MHz"

    return cpu


def get_memory_info() -> dict:
    result = {
        "total": 0,
        "available": 0,
        "used": 0,
        "swap_total": 0,
        "swap_free": 0,
    }

    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as file:
            values = {}

            for line in file:
                parts = line.split()

                if len(parts) >= 2:
                    values[parts[0].rstrip(":")] = int(parts[1]) * 1024

        total = values.get("MemTotal", 0)
        available = values.get("MemAvailable", 0)

        result["total"] = total
        result["available"] = available
        result["used"] = total - available
        result["swap_total"] = values.get("SwapTotal", 0)
        result["swap_free"] = values.get("SwapFree", 0)

    except (FileNotFoundError, ValueError):
        pass

    return result


def get_gpu_info() -> list[str]:
    gpus = []

    if command_exists("lspci"):
        output = run_command(["lspci"])

        for line in output.splitlines():
            lower = line.lower()

            if (
                "vga compatible controller" in lower
                or "3d controller" in lower
                or "display controller" in lower
            ):
                if ":" in line:
                    gpus.append(line.split(":", 1)[1].strip())

    return gpus


def get_board_info() -> dict:
    info = {
        "manufacturer": "Unknown",
        "model": "Unknown",
        "bios": "Unknown",
    }

    paths = {
        "manufacturer": "/sys/class/dmi/id/board_vendor",
        "model": "/sys/class/dmi/id/board_name",
        "bios": "/sys/class/dmi/id/bios_version",
    }

    for key, path in paths.items():
        try:
            with open(path, "r", encoding="utf-8") as file:
                info[key] = file.read().strip()
        except (FileNotFoundError, PermissionError, OSError):
            pass

    return info


def hardware_info() -> dict:
    cpu = get_cpu_info()
    memory = get_memory_info()
    gpus = get_gpu_info()
    board = get_board_info()

    section("Hardware")

    print(f"{BOLD}CPU{RESET}")
    item("Model", cpu["model"])
    item("Threads", cpu["threads"])
    item("Frequency", cpu["frequency"])

    print()
    print(f"{BOLD}MEMORY{RESET}")

    total = memory["total"]
    used = memory["used"]
    available = memory["available"]

    item("Total", format_bytes(total))
    item("Used", format_bytes(used))
    item("Available", format_bytes(available))

    if total:
        item("Usage", f"{(used / total) * 100:.1f}%")

    print()
    print(f"{BOLD}GPU{RESET}")

    if gpus:
        for index, gpu in enumerate(gpus, 1):
            item(f"GPU {index}", gpu)
    else:
        item("GPU", "Not detected")

    print()
    print(f"{BOLD}MOTHERBOARD / BIOS{RESET}")

    item("Manufacturer", board["manufacturer"])
    item("Model", board["model"])
    item("BIOS", board["bios"])

    return {
        "cpu": cpu,
        "memory": memory,
        "gpu": gpus,
        "board": board,
    }


# ============================================================
# STORAGE
# ============================================================

def storage_info() -> list[dict]:
    disks = []

    if command_exists("lsblk"):
        output = run_command(
            [
                "lsblk",
                "-J",
                "-o",
                "NAME,MODEL,SIZE,TYPE,FSTYPE,MOUNTPOINTS",
            ]
        )

        try:
            data = json.loads(output)

            for device in data.get("blockdevices", []):
                if device.get("type") == "disk":
                    disks.append(device)

        except json.JSONDecodeError:
            pass

    section("Storage")

    if not disks:
        item("Devices", "Unable to detect")
        return []

    for disk in disks:
        print()

        item("Device", disk.get("name", "Unknown"))
        item("Model", disk.get("model") or "Unknown")
        item("Type", disk.get("type", "Unknown"))
        item("Capacity", disk.get("size", "Unknown"))

    print()
    print(f"{BOLD}FILESYSTEM USAGE{RESET}")

    mounts = []

    try:
        output = run_command(["df", "-h"])

        for line in output.splitlines()[1:]:
            parts = line.split()

            if len(parts) >= 6:
                filesystem = parts[0]
                size = parts[1]
                used = parts[2]
                available = parts[3]
                percentage = parts[4]
                mountpoint = " ".join(parts[5:])

                if filesystem.startswith("/dev/"):
                    mounts.append(
                        {
                            "filesystem": filesystem,
                            "size": size,
                            "used": used,
                            "available": available,
                            "usage": percentage,
                            "mountpoint": mountpoint,
                        }
                    )

                    level = "ok"

                    try:
                        usage = int(percentage.rstrip("%"))

                        if usage >= 90:
                            level = "critical"
                        elif usage >= 80:
                            level = "warning"

                    except ValueError:
                        pass

                    status(
                        mountpoint,
                        f"{used} / {size} ({percentage})",
                        level,
                    )

    except OSError:
        pass

    return {
        "devices": disks,
        "filesystems": mounts,
    }


# ============================================================
# NETWORK
# ============================================================

def get_default_gateway() -> str:
    output = run_command(["ip", "route"])

    for line in output.splitlines():
        if line.startswith("default"):
            parts = line.split()

            if "via" in parts:
                index = parts.index("via")

                if index + 1 < len(parts):
                    return parts[index + 1]

    return "Unknown"


def get_dns_servers() -> list[str]:
    servers = []

    try:
        with open("/etc/resolv.conf", "r", encoding="utf-8") as file:
            for line in file:
                if line.startswith("nameserver"):
                    parts = line.split()

                    if len(parts) >= 2:
                        servers.append(parts[1])

    except (FileNotFoundError, PermissionError):
        pass

    return servers


def network_info() -> dict:
    interfaces = []

    output = run_command(["ip", "-j", "addr"])

    try:
        data = json.loads(output)

        for interface in data:
            name = interface.get("ifname")

            if not name:
                continue

            mac = interface.get("address", "Unknown")
            state = interface.get("operstate", "Unknown")

            ipv4 = []
            ipv6 = []

            for address in interface.get("addr_info", []):
                family = address.get("family")
                local = address.get("local")

                if family == "inet":
                    ipv4.append(local)

                elif family == "inet6":
                    ipv6.append(local)

            interfaces.append(
                {
                    "name": name,
                    "state": state,
                    "mac": mac,
                    "ipv4": ipv4,
                    "ipv6": ipv6,
                }
            )

    except json.JSONDecodeError:
        pass

    gateway = get_default_gateway()
    dns = get_dns_servers()

    section("Network")

    for interface in interfaces:
        print()
        item("Interface", interface["name"])
        item("Status", interface["state"])
        item("MAC", interface["mac"])

        item(
            "IPv4",
            ", ".join(interface["ipv4"]) or "None",
        )

        item(
            "IPv6",
            ", ".join(interface["ipv6"]) or "None",
        )

    print()
    item("Default gateway", gateway)
    item("DNS servers", ", ".join(dns) if dns else "Unknown")

    connectivity = {
        "gateway": False,
        "internet": False,
        "dns": False,
        "latency": None,
    }

    if gateway != "Unknown":
        gateway_test = run_command(
            ["ping", "-c", "1", "-W", "2", gateway]
        )

        connectivity["gateway"] = bool(gateway_test)

        if gateway_test:
            match = re.search(
                r"time[=<]([0-9.]+)\s*ms",
                gateway_test,
            )

            if match:
                connectivity["latency"] = float(match.group(1))

    internet_test = run_command(
        ["ping", "-c", "1", "-W", "2", "1.1.1.1"]
    )

    connectivity["internet"] = bool(internet_test)

    try:
        socket.gethostbyname("example.com")
        connectivity["dns"] = True
    except socket.gaierror:
        connectivity["dns"] = False

    print()
    print(f"{BOLD}CONNECTIVITY{RESET}")

    status(
        "Gateway",
        "Reachable" if connectivity["gateway"] else "Unreachable",
        "ok" if connectivity["gateway"] else "critical",
    )

    status(
        "Internet",
        "Online" if connectivity["internet"] else "Offline",
        "ok" if connectivity["internet"] else "critical",
    )

    status(
        "DNS",
        "Working" if connectivity["dns"] else "Failed",
        "ok" if connectivity["dns"] else "warning",
    )

    if connectivity["latency"] is not None:
        item("Latency", f"{connectivity['latency']:.1f} ms")

    return {
        "interfaces": interfaces,
        "gateway": gateway,
        "dns": dns,
        "connectivity": connectivity,
    }


# ============================================================
# PROCESSES
# ============================================================

def processes_info() -> list[dict]:
    processes = []

    if command_exists("ps"):
        output = run_command(
            [
                "ps",
                "-eo",
                "pid,user,pcpu,pmem,comm",
                "--sort=-pcpu",
            ]
        )

        for line in output.splitlines()[1:16]:
            parts = line.split(None, 4)

            if len(parts) >= 5:
                processes.append(
                    {
                        "pid": parts[0],
                        "user": parts[1],
                        "cpu": parts[2],
                        "memory": parts[3],
                        "command": parts[4],
                    }
                )

    section("Processes")

    if not processes:
        item("Processes", "Unable to read process list")
        return []

    print(
        f"{'PID':<8}"
        f"{'USER':<16}"
        f"{'CPU':<9}"
        f"{'MEM':<9}"
        f"COMMAND"
    )

    print("─" * 62)

    for process in processes:
        print(
            f"{process['pid']:<8}"
            f"{process['user'][:15]:<16}"
            f"{process['cpu']:<9}"
            f"{process['memory']:<9}"
            f"{process['command'][:25]}"
        )

    return processes


# ============================================================
# SERVICES
# ============================================================

def services_info() -> dict:
    running = []
    stopped = []
    failed = []

    if command_exists("systemctl"):
        output = run_command(
            [
                "systemctl",
                "list-units",
                "--type=service",
                "--all",
                "--no-pager",
                "--no-legend",
            ]
        )

        for line in output.splitlines():
            parts = line.split()

            if len(parts) < 4:
                continue

            service = parts[0]
            state = parts[2]

            if state == "running":
                running.append(service)

            elif state == "failed":
                failed.append(service)

            elif state in ("dead", "exited"):
                stopped.append(service)

    section("Services")

    print(f"{BOLD}RUNNING{RESET}")

    for service in running[:20]:
        status(service, "RUNNING", "ok")

    if not running:
        item("Running", "None detected")

    print()
    print(f"{BOLD}FAILED{RESET}")

    for service in failed:
        status(service, "FAILED", "critical")

    if not failed:
        status("Services", "No failed services detected", "ok")

    print()
    print(f"{BOLD}SUMMARY{RESET}")

    item("Running", len(running))
    item("Stopped", len(stopped))
    item("Failed", len(failed))

    return {
        "running": running,
        "stopped": stopped,
        "failed": failed,
    }


# ============================================================
# SECURITY
# ============================================================

def firewall_status() -> tuple[str, str]:
    if command_exists("ufw"):
        output = run_command(["ufw", "status"])

        if "Status: active" in output:
            return "Enabled", "ok"

        if "Status: inactive" in output:
            return "Disabled", "warning"

    if command_exists("firewall-cmd"):
        output = run_command(["firewall-cmd", "--state"])

        if output == "running":
            return "Enabled", "ok"

    if command_exists("nft"):
        output = run_command(["nft", "list", "ruleset"])

        if output:
            return "Rules detected", "ok"

    return "Unknown", "warning"


def ssh_security() -> dict:
    result = {
        "installed": False,
        "running": False,
        "root_login": "Unknown",
        "password_auth": "Unknown",
    }

    config = "/etc/ssh/sshd_config"

    if os.path.exists(config):
        result["installed"] = True

        if command_exists("systemctl"):
            state = run_command(
                ["systemctl", "is-active", "ssh"]
            )

            if state == "active":
                result["running"] = True
            else:
                state = run_command(
                    ["systemctl", "is-active", "sshd"]
                )
                result["running"] = state == "active"

        try:
            with open(config, "r", encoding="utf-8") as file:
                text = file.read()

            root_match = re.search(
                r"^\s*PermitRootLogin\s+(\S+)",
                text,
                re.MULTILINE,
            )

            password_match = re.search(
                r"^\s*PasswordAuthentication\s+(\S+)",
                text,
                re.MULTILINE,
            )

            if root_match:
                result["root_login"] = root_match.group(1)

            if password_match:
                result["password_auth"] = password_match.group(1)

        except (PermissionError, OSError):
            pass

    return result


def failed_logins() -> int:
    if command_exists("journalctl"):
        output = run_command(
            [
                "journalctl",
                "--since",
                "24 hours ago",
                "--no-pager",
                "-q",
            ],
            timeout=10,
        )

        count = 0

        for line in output.splitlines():
            lower = line.lower()

            if (
                "failed password" in lower
                or "authentication failure" in lower
                or "failed login" in lower
            ):
                count += 1

        return count

    return 0


def security_info() -> dict:
    firewall, firewall_level = firewall_status()
    ssh = ssh_security()
    failed = failed_logins()

    section("Security")

    status(
        "Firewall",
        firewall,
        firewall_level,
    )

    print()
    print(f"{BOLD}SSH{RESET}")

    if ssh["installed"]:
        status(
            "SSH service",
            "Running" if ssh["running"] else "Stopped",
            "ok" if ssh["running"] else "info",
        )

        status(
            "Root login",
            ssh["root_login"],
            "warning"
            if ssh["root_login"].lower() in ("yes", "without-password")
            else "ok",
        )

        status(
            "Password auth",
            ssh["password_auth"],
            "warning"
            if ssh["password_auth"].lower() == "yes"
            else "ok",
        )
    else:
        status(
            "SSH",
            "Not detected",
            "info",
        )

    print()
    print(f"{BOLD}AUTHENTICATION{RESET}")

    status(
        "Failed logins (24h)",
        str(failed),
        "warning" if failed > 0 else "ok",
    )

    print()
    print(f"{BOLD}SYSTEM SECURITY{RESET}")

    secure_boot = "Unknown"

    if command_exists("mokutil"):
        output = run_command(["mokutil", "--sb-state"])

        if "SecureBoot enabled" in output:
            secure_boot = "Enabled"

        elif "SecureBoot disabled" in output:
            secure_boot = "Disabled"

    status(
        "Secure Boot",
        secure_boot,
        "ok"
        if secure_boot == "Enabled"
        else "warning"
        if secure_boot == "Disabled"
        else "info",
    )

    return {
        "firewall": firewall,
        "ssh": ssh,
        "failed_logins_24h": failed,
        "secure_boot": secure_boot,
    }


# ============================================================
# HEALTH
# ============================================================

def health_info(
    hardware: dict,
    storage: dict | list,
    network: dict,
    services: dict,
    security: dict,
) -> dict:

    checks = []

    memory = hardware.get("memory", {})

    if memory.get("total"):
        usage = (
            memory["used"] / memory["total"]
        ) * 100

        if usage >= 90:
            checks.append(("RAM", "Critical", "critical"))
        elif usage >= 80:
            checks.append(("RAM", "High usage", "warning"))
        else:
            checks.append(("RAM", "Normal", "ok"))

    filesystems = []

    if isinstance(storage, dict):
        filesystems = storage.get("filesystems", [])

    for filesystem in filesystems:
        try:
            usage = int(
                filesystem["usage"].rstrip("%")
            )

            if filesystem["mountpoint"] == "/":
                if usage >= 90:
                    checks.append(
                        ("Root storage", "Critical", "critical")
                    )
                elif usage >= 80:
                    checks.append(
                        ("Root storage", "High usage", "warning")
                    )
                else:
                    checks.append(
                        ("Root storage", "Normal", "ok")
                    )

        except (KeyError, ValueError):
            pass

    connectivity = network.get("connectivity", {})

    if connectivity.get("internet"):
        checks.append(
            ("Network", "Online", "ok")
        )
    else:
        checks.append(
            ("Network", "Offline", "critical")
        )

    failed_services = services.get("failed", [])

    if failed_services:
        checks.append(
            (
                "Services",
                f"{len(failed_services)} failed",
                "warning",
            )
        )
    else:
        checks.append(
            ("Services", "Normal", "ok")
        )

    failed_logins_count = security.get(
        "failed_logins_24h",
        0,
    )

    if failed_logins_count >= 20:
        checks.append(
            (
                "Authentication",
                f"{failed_logins_count} failures",
                "warning",
            )
        )
    else:
        checks.append(
            (
                "Authentication",
                f"{failed_logins_count} failures",
                "ok",
            )
        )

    section("System Health")

    for label, value, level in checks:
        status(label, value, level)

    critical = sum(
        1 for _, _, level in checks
        if level == "critical"
    )

    warnings = sum(
        1 for _, _, level in checks
        if level == "warning"
    )

    if critical:
        overall = "CRITICAL"
        overall_level = "critical"
    elif warnings:
        overall = "ATTENTION REQUIRED"
        overall_level = "warning"
    else:
        overall = "HEALTHY"
        overall_level = "ok"

    print()
    status(
        "Overall health",
        overall,
        overall_level,
    )

    return {
        "checks": checks,
        "critical": critical,
        "warnings": warnings,
        "overall": overall,
    }


# ============================================================
# SUMMARY
# ============================================================

def summary(
    health: dict,
    security: dict,
    services: dict,
) -> dict:

    section("Summary")

    status(
        "System",
        health["overall"],
        "critical"
        if health["critical"]
        else "warning"
        if health["warnings"]
        else "ok",
    )

    status(
        "Security",
        security["firewall"],
        "ok"
        if security["firewall"] == "Enabled"
        else "warning",
    )

    status(
        "Services",
        "All healthy"
        if not services["failed"]
        else f"{len(services['failed'])} failed",
        "ok"
        if not services["failed"]
        else "warning",
    )

    print()
    item("Critical issues", health["critical"])
    item("Warnings", health["warnings"])

    print()
    print(
        f"{BOLD}{CYAN}"
        "══════════════════════════════════════════════════════════════"
        f"{RESET}"
    )

    if health["critical"]:
        status(
            "SYSTEM STATUS",
            "CRITICAL",
            "critical",
        )

    elif health["warnings"]:
        status(
            "SYSTEM STATUS",
            "ATTENTION REQUIRED",
            "warning",
        )

    else:
        status(
            "SYSTEM STATUS",
            "HEALTHY",
            "ok",
        )

    print()
    print(
        f"{GRAY}"
        f"Report generated: "
        f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        f"{RESET}"
    )

    return {
        "critical": health["critical"],
        "warnings": health["warnings"],
        "status": health["overall"],
    }


# ============================================================
# REPORT
# ============================================================

def full_report() -> dict:
    report = {
        "version": VERSION,
        "timestamp": datetime.datetime.now().isoformat(),
    }

    report["system"] = system_info()
    report["hardware"] = hardware_info()
    report["storage"] = storage_info()
    report["network"] = network_info()
    report["processes"] = processes_info()
    report["services"] = services_info()
    report["security"] = security_info()

    report["health"] = health_info(
        report["hardware"],
        report["storage"],
        report["network"],
        report["services"],
        report["security"],
    )

    report["summary"] = summary(
        report["health"],
        report["security"],
        report["services"],
    )

    return report


# ============================================================
# CLI
# ============================================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "H-Check - System information "
            "and diagnostics tool"
        )
    )

    parser.add_argument(
        "--system",
        action="store_true",
        help="Show system information",
    )

    parser.add_argument(
        "--hardware",
        action="store_true",
        help="Show hardware information",
    )

    parser.add_argument(
        "--storage",
        action="store_true",
        help="Show storage information",
    )

    parser.add_argument(
        "--network",
        action="store_true",
        help="Show network information",
    )

    parser.add_argument(
        "--processes",
        action="store_true",
        help="Show running processes",
    )

    parser.add_argument(
        "--services",
        action="store_true",
        help="Show system services",
    )

    parser.add_argument(
        "--security",
        action="store_true",
        help="Show security information",
    )

    parser.add_argument(
        "--health",
        action="store_true",
        help="Show system health",
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all diagnostic modules",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output complete report as JSON",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"H-Check {VERSION}",
    )

    return parser.parse_args()


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    args = parse_args()

    selected = any(
        [
            args.system,
            args.hardware,
            args.storage,
            args.network,
            args.processes,
            args.services,
            args.security,
            args.health,
            args.all,
            args.json,
        ]
    )

    if not selected:
        banner()
        full_report()
        return

    if args.json:
        report = full_report()
        print(json.dumps(report, indent=4, default=str))
        return

    banner()

    if args.all:
        full_report()
        return

    if args.system:
        system_info()

    if args.hardware:
        hardware_info()

    if args.storage:
        storage_info()

    if args.network:
        network_info()

    if args.processes:
        processes_info()

    if args.services:
        services_info()

    if args.security:
        security_info()

    if args.health:
        print(
            f"{YELLOW}"
            "Health requires the full diagnostic context. "
            "Running complete checks..."
            f"{RESET}"
        )

        report = full_report()

        return


if __name__ == "__main__":
    try:
        main()

    except KeyboardInterrupt:
        print(
            f"\n{YELLOW}"
            "H-Check interrupted by user."
            f"{RESET}"
        )
        sys.exit(130)

    except PermissionError:
        print(
            f"\n{RED}"
            "Permission denied. Try running with appropriate privileges."
            f"{RESET}"
        )
        sys.exit(1)

    except Exception as error:
        print(
            f"\n{RED}"
            f"H-Check error: {error}"
            f"{RESET}"
        )
        sys.exit(1)
