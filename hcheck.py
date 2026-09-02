#!/usr/bin/env python3

"""
H-Check
-------
Lightweight hardware and system analyzer.

Features:
- User and hostname information
- Operating system and kernel
- CPU information
- RAM information
- GPU detection
- Disk information
- Network interfaces
- Battery status
- BIOS / motherboard information
- System uptime
- Environment information
- Human-readable and JSON output

Standard-library only.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


# ============================================================
# CONFIG
# ============================================================

VERSION = "1.0.0"


# ============================================================
# COLORS
# ============================================================

RESET = "\033[0m"
BOLD = "\033[1m"
CYAN = "\033[96m"
WHITE = "\033[97m"
GRAY = "\033[90m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"


# ============================================================
# ASCII
# ============================================================

BANNER = f"""
{CYAN}
 _   _        ____ _               _
| | | |      / ___| |__   ___  ___| | __
| |_| |_____| |   | '_ \\ / _ \\/ __| |/ /
|  _  |_____| |___| | | |  __/ (__|   <
|_| |_|      \\____|_| |_|\\___|\\___|_|\\_\\
{RESET}
{GRAY}Hardware & System Analyzer v{VERSION}{RESET}
"""


# ============================================================
# HELPERS
# ============================================================

def run_command(command: list[str]) -> str:
    """Execute a command safely and return stdout."""
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=3,
            check=False,
        )
        return result.stdout.strip()
    except (FileNotFoundError, subprocess.SubprocessError, OSError):
        return ""


def read_file(path: str) -> str:
    """Read a text file safely."""
    try:
        return Path(path).read_text(errors="ignore").strip()
    except (OSError, PermissionError):
        return ""


def format_bytes(value: int | float) -> str:
    """Convert bytes to human-readable units."""
    value = float(value)

    units = ["B", "KB", "MB", "GB", "TB", "PB"]

    for unit in units:
        if value < 1024:
            return f"{value:.1f} {unit}"
        value /= 1024

    return f"{value:.1f} EB"


def format_uptime(seconds: int) -> str:
    """Format uptime."""
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    parts = []

    if days:
        parts.append(f"{days}d")

    if hours:
        parts.append(f"{hours}h")

    if minutes:
        parts.append(f"{minutes}m")

    if not parts:
        parts.append(f"{seconds}s")

    return " ".join(parts)


def clean(value: str | None, default: str = "Unknown") -> str:
    """Clean empty values."""
    if value is None:
        return default

    value = str(value).strip()

    return value if value else default


# ============================================================
# USER / SYSTEM
# ============================================================

def get_user_info() -> dict[str, Any]:
    username = os.environ.get("USER") or os.environ.get("USERNAME")

    try:
        hostname = socket.gethostname()
    except OSError:
        hostname = "Unknown"

    try:
        home = str(Path.home())
    except RuntimeError:
        home = "Unknown"

    return {
        "username": clean(username),
        "hostname": clean(hostname),
        "home": home,
        "uid": os.getuid() if hasattr(os, "getuid") else None,
    }


def get_os_info() -> dict[str, Any]:
    system = platform.system()

    return {
        "system": clean(system),
        "distribution": clean(platform.platform()),
        "release": clean(platform.release()),
        "version": clean(platform.version()),
        "kernel": clean(platform.uname().release),
        "architecture": clean(platform.machine()),
        "processor": clean(platform.processor()),
        "python": platform.python_version(),
    }


# ============================================================
# CPU
# ============================================================

def get_cpu_info() -> dict[str, Any]:
    info: dict[str, Any] = {
        "model": "Unknown",
        "cores_physical": os.cpu_count(),
        "cores_logical": os.cpu_count(),
        "frequency": "Unknown",
        "architecture": platform.machine(),
    }

    if sys.platform.startswith("linux"):
        cpuinfo = read_file("/proc/cpuinfo")

        models = re.findall(
            r"^model name\s*:\s*(.+)$",
            cpuinfo,
            re.MULTILINE,
        )

        if models:
            info["model"] = models[0].strip()

        physical_ids = re.findall(
            r"^physical id\s*:\s*(\d+)",
            cpuinfo,
            re.MULTILINE,
        )

        cores = re.findall(
            r"^cpu cores\s*:\s*(\d+)",
            cpuinfo,
            re.MULTILINE,
        )

        if cores:
            try:
                info["cores_physical"] = int(cores[0])
            except ValueError:
                pass

        freq = re.findall(
            r"^cpu MHz\s*:\s*(.+)$",
            cpuinfo,
            re.MULTILINE,
        )

        if freq:
            try:
                info["frequency"] = f"{float(freq[0]):.0f} MHz"
            except ValueError:
                info["frequency"] = freq[0].strip()

        if physical_ids:
            info["sockets"] = len(set(physical_ids))

    elif sys.platform == "win32":
        model = os.environ.get("PROCESSOR_IDENTIFIER")
        info["model"] = clean(model, platform.processor())

        freq = run_command(
            ["wmic", "cpu", "get", "MaxClockSpeed"]
        )

        values = [
            line.strip()
            for line in freq.splitlines()
            if line.strip().isdigit()
        ]

        if values:
            info["frequency"] = f"{values[0]} MHz"

    elif sys.platform == "darwin":
        model = run_command(["sysctl", "-n", "machdep.cpu.brand_string"])
        info["model"] = clean(model, platform.processor())

        freq = run_command(["sysctl", "-n", "hw.cpufrequency"])

        if freq.isdigit():
            info["frequency"] = f"{int(freq) / 1_000_000:.0f} MHz"

    return info


# ============================================================
# MEMORY
# ============================================================

def get_memory_info() -> dict[str, Any]:
    info = {
        "total": 0,
        "available": 0,
        "used": 0,
        "usage_percent": 0,
    }

    if sys.platform.startswith("linux"):
        meminfo = read_file("/proc/meminfo")

        total_match = re.search(
            r"^MemTotal:\s+(\d+)",
            meminfo,
            re.MULTILINE,
        )

        available_match = re.search(
            r"^MemAvailable:\s+(\d+)",
            meminfo,
            re.MULTILINE,
        )

        if total_match:
            info["total"] = int(total_match.group(1)) * 1024

        if available_match:
            info["available"] = int(available_match.group(1)) * 1024

    elif sys.platform == "win32":
        output = run_command(
            ["wmic", "OS", "get", "TotalVisibleMemorySize,FreePhysicalMemory"]
        )

        numbers = re.findall(r"\d+", output)

        if len(numbers) >= 2:
            info["total"] = int(numbers[-2]) * 1024
            info["available"] = int(numbers[-1]) * 1024

    elif sys.platform == "darwin":
        total = run_command(["sysctl", "-n", "hw.memsize"])

        if total.isdigit():
            info["total"] = int(total)

    if info["total"]:
        info["used"] = info["total"] - info["available"]

        info["usage_percent"] = round(
            (info["used"] / info["total"]) * 100,
            1,
        )

    return info


# ============================================================
# GPU
# ============================================================

def get_gpu_info() -> list[dict[str, Any]]:
    gpus = []

    if sys.platform.startswith("linux"):
        output = run_command(
            [
                "lspci",
                "-nn",
            ]
        )

        for line in output.splitlines():
            if re.search(
                r"(VGA compatible controller|3D controller|Display controller)",
                line,
                re.IGNORECASE,
            ):
                device = line.split(":", 2)[-1].strip()

                gpus.append({
                    "device": device,
                    "source": "lspci",
                })

        if not gpus:
            drm_path = Path("/sys/class/drm")

            if drm_path.exists():
                for card in sorted(drm_path.glob("card[0-9]")):
                    vendor = read_file(
                        str(card / "device/vendor")
                    )

                    device = read_file(
                        str(card / "device/device")
                    )

                    if vendor or device:
                        gpus.append({
                            "device": f"{vendor} {device}".strip(),
                            "source": "sysfs",
                        })

    elif sys.platform == "win32":
        output = run_command(
            [
                "wmic",
                "path",
                "win32_VideoController",
                "get",
                "Name",
            ]
        )

        for line in output.splitlines():
            line = line.strip()

            if line and line.lower() != "name":
                gpus.append({
                    "device": line,
                    "source": "wmic",
                })

    elif sys.platform == "darwin":
        output = run_command(
            ["system_profiler", "SPDisplaysDataType"]
        )

        for line in output.splitlines():
            if "Chipset Model:" in line:
                name = line.split(":", 1)[1].strip()

                gpus.append({
                    "device": name,
                    "source": "system_profiler",
                })

    return gpus


# ============================================================
# STORAGE
# ============================================================

def get_storage_info() -> list[dict[str, Any]]:
    disks = []

    partitions = []

    try:
        partitions = shutil.disk_usage("/")
    except OSError:
        pass

    if partitions:
        total, used, free = partitions

        disks.append({
            "mount": "/",
            "total": total,
            "used": used,
            "free": free,
            "usage_percent": round(
                (used / total) * 100,
                1,
            ) if total else 0,
        })

    if sys.platform.startswith("linux"):
        mounts = set()

        mount_file = read_file("/proc/mounts")

        for line in mount_file.splitlines():
            parts = line.split()

            if len(parts) >= 2:
                mount = parts[1]

                if (
                    mount.startswith("/proc")
                    or mount.startswith("/sys")
                    or mount.startswith("/dev")
                    or mount.startswith("/run")
                ):
                    continue

                mounts.add(mount)

        for mount in sorted(mounts):
            try:
                usage = shutil.disk_usage(mount)
            except OSError:
                continue

            total, used, free = usage

            if mount == "/":
                continue

            disks.append({
                "mount": mount,
                "total": total,
                "used": used,
                "free": free,
                "usage_percent": round(
                    (used / total) * 100,
                    1,
                ) if total else 0,
            })

    return disks


# ============================================================
# NETWORK
# ============================================================

def get_network_info() -> list[dict[str, Any]]:
    interfaces = []

    try:
        names = socket.if_nameindex()
    except (AttributeError, OSError):
        names = []

    for _, name in names:
        interface = {
            "name": name,
            "mac": "Unknown",
            "ipv4": [],
        }

        if sys.platform.startswith("linux"):
            mac = read_file(
                f"/sys/class/net/{name}/address"
            )

            interface["mac"] = clean(mac)

            addr_output = run_command(
                ["ip", "-4", "addr", "show", "dev", name]
            )

            addresses = re.findall(
                r"inet\s+(\d+\.\d+\.\d+\.\d+/\d+)",
                addr_output,
            )

            interface["ipv4"] = addresses

        interfaces.append(interface)

    return interfaces


# ============================================================
# BATTERY
# ============================================================

def get_battery_info() -> list[dict[str, Any]]:
    batteries = []

    if sys.platform.startswith("linux"):
        power_path = Path("/sys/class/power_supply")

        if power_path.exists():
            for battery in power_path.glob("BAT*"):
                capacity = read_file(
                    str(battery / "capacity")
                )

                status = read_file(
                    str(battery / "status")
                )

                batteries.append({
                    "name": battery.name,
                    "capacity": f"{capacity}%" if capacity else "Unknown",
                    "status": clean(status),
                })

    elif sys.platform == "darwin":
        output = run_command(
            ["pmset", "-g", "batt"]
        )

        match = re.search(
            r"(\d+)%.*?;\s*(\w+)",
            output,
        )

        if match:
            batteries.append({
                "name": "Battery",
                "capacity": f"{match.group(1)}%",
                "status": match.group(2),
            })

    elif sys.platform == "win32":
        output = run_command(
            [
                "wmic",
                "path",
                "Win32_Battery",
                "get",
                "EstimatedChargeRemaining,BatteryStatus",
            ]
        )

        numbers = re.findall(r"\d+", output)

        if numbers:
            batteries.append({
                "name": "Battery",
                "capacity": f"{numbers[0]}%",
                "status": clean(
                    numbers[1] if len(numbers) > 1 else None
                ),
            })

    return batteries


# ============================================================
# MOTHERBOARD / BIOS
# ============================================================

def get_firmware_info() -> dict[str, Any]:
    info = {
        "manufacturer": "Unknown",
        "product": "Unknown",
        "bios_vendor": "Unknown",
        "bios_version": "Unknown",
        "bios_date": "Unknown",
    }

    if sys.platform.startswith("linux"):
        base = Path("/sys/class/dmi/id")

        mapping = {
            "manufacturer": "sys_vendor",
            "product": "product_name",
            "bios_vendor": "bios_vendor",
            "bios_version": "bios_version",
            "bios_date": "bios_date",
        }

        for key, filename in mapping.items():
            value = read_file(str(base / filename))

            if value:
                info[key] = value

    elif sys.platform == "darwin":
        output = run_command(
            ["system_profiler", "SPHardwareDataType"]
        )

        for line in output.splitlines():
            line = line.strip()

            if "Model Name:" in line:
                info["product"] = line.split(":", 1)[1].strip()

    elif sys.platform == "win32":
        output = run_command(
            [
                "wmic",
                "computersystem",
                "get",
                "Manufacturer,Model",
            ]
        )

        lines = [
            line.strip()
            for line in output.splitlines()
            if line.strip()
        ]

        if len(lines) >= 2:
            parts = lines[1].split()

            if parts:
                info["manufacturer"] = parts[0]

                if len(parts) > 1:
                    info["product"] = " ".join(parts[1:])

        bios = run_command(
            [
                "wmic",
                "bios",
                "get",
                "Manufacturer,SMBIOSBIOSVersion,ReleaseDate",
            ]
        )

        lines = [
            line.strip()
            for line in bios.splitlines()
            if line.strip()
        ]

        if len(lines) >= 2:
            parts = lines[1].split()

            if len(parts) >= 1:
                info["bios_vendor"] = parts[0]

            if len(parts) >= 2:
                info["bios_version"] = parts[1]

            if len(parts) >= 3:
                info["bios_date"] = parts[2]

    return info


# ============================================================
# UPTIME
# ============================================================

def get_uptime() -> str:
    if sys.platform.startswith("linux"):
        uptime = read_file("/proc/uptime")

        if uptime:
            try:
                seconds = int(float(uptime.split()[0]))
                return format_uptime(seconds)
            except (ValueError, IndexError):
                pass

    if sys.platform == "darwin":
        output = run_command(["sysctl", "-n", "kern.boottime"])

        match = re.search(r"sec\s*=\s*(\d+)", output)

        if match:
            boot = int(match.group(1))
            return format_uptime(int(time.time()) - boot)

    return "Unknown"


# ============================================================
# ENVIRONMENT
# ============================================================

def get_environment_info() -> dict[str, Any]:
    desktop = (
        os.environ.get("XDG_CURRENT_DESKTOP")
        or os.environ.get("DESKTOP_SESSION")
        or "Unknown"
    )

    shell = (
        os.environ.get("SHELL")
        or os.environ.get("COMSPEC")
        or "Unknown"
    )

    return {
        "desktop": desktop,
        "shell": shell,
        "terminal": os.environ.get("TERM", "Unknown"),
        "display_server": os.environ.get(
            "XDG_SESSION_TYPE",
            "Unknown",
        ),
    }


# ============================================================
# FULL SCAN
# ============================================================

def collect_hardware(quick: bool = False) -> dict[str, Any]:
    data = {
        "hcheck": {
            "version": VERSION,
            "timestamp": time.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        },

        "user": get_user_info(),
        "system": get_os_info(),
        "cpu": get_cpu_info(),
        "memory": get_memory_info(),
        "gpu": get_gpu_info(),
        "storage": get_storage_info(),
        "network": get_network_info(),
        "firmware": get_firmware_info(),
        "environment": get_environment_info(),
        "uptime": get_uptime(),
    }

    if not quick:
        data["battery"] = get_battery_info()

    return data


# ============================================================
# DISPLAY
# ============================================================

def section(title: str) -> None:
    print()
    print(f"{BOLD}{CYAN}┌─ {title}{RESET}")


def item(label: str, value: Any) -> None:
    print(
        f"{GRAY}│{RESET} "
        f"{WHITE}{label:<20}{RESET} "
        f"{value}"
    )


def display_report(data: dict[str, Any]) -> None:

    print(BANNER)

    # USER
    section("USER")

    user = data["user"]

    item("Username", user["username"])
    item("Hostname", user["hostname"])
    item("Home", user["home"])

    if user["uid"] is not None:
        item("UID", user["uid"])

    # SYSTEM
    section("SYSTEM")

    system = data["system"]

    item("OS", system["system"])
    item("Distribution", system["distribution"])
    item("Release", system["release"])
    item("Kernel", system["kernel"])
    item("Architecture", system["architecture"])
    item("Python", system["python"])
    item("Uptime", data["uptime"])

    # CPU
    section("CPU")

    cpu = data["cpu"]

    item("Model", cpu["model"])
    item("Architecture", cpu["architecture"])
    item("Physical cores", cpu["cores_physical"])
    item("Logical cores", cpu["cores_logical"])
    item("Frequency", cpu["frequency"])

    if "sockets" in cpu:
        item("CPU sockets", cpu["sockets"])

    # MEMORY
    section("MEMORY")

    memory = data["memory"]

    item("Total", format_bytes(memory["total"]))
    item("Used", format_bytes(memory["used"]))
    item("Available", format_bytes(memory["available"]))
    item("Usage", f'{memory["usage_percent"]}%')

    # GPU
    section("GPU")

    gpus = data["gpu"]

    if gpus:
        for index, gpu in enumerate(gpus, 1):
            item(f"GPU {index}", gpu["device"])
    else:
        item("GPU", "Not detected")

    # STORAGE
    section("STORAGE")

    storage = data["storage"]

    if storage:
        for disk in storage:
            print(
                f"{GRAY}│{RESET} "
                f"{WHITE}{disk['mount']:<20}{RESET} "
                f"{format_bytes(disk['used'])} / "
                f"{format_bytes(disk['total'])} "
                f"({disk['usage_percent']}%)"
            )
    else:
        item("Storage", "Not detected")

    # NETWORK
    section("NETWORK")

    network = data["network"]

    if network:
        for interface in network:
            print(
                f"{GRAY}│{RESET} "
                f"{WHITE}{interface['name']:<20}{RESET} "
                f"MAC: {interface['mac']}"
            )

            for ip in interface["ipv4"]:
                print(
                    f"{GRAY}│{RESET} "
                    f"{'':20} "
                    f"IPv4: {ip}"
                )
    else:
        item("Interfaces", "Not detected")

    # FIRMWARE
    section("MOTHERBOARD / BIOS")

    firmware = data["firmware"]

    item("Manufacturer", firmware["manufacturer"])
    item("Product", firmware["product"])
    item("BIOS vendor", firmware["bios_vendor"])
    item("BIOS version", firmware["bios_version"])
    item("BIOS date", firmware["bios_date"])

    # BATTERY
    if "battery" in data:
        section("BATTERY")

        battery = data["battery"]

        if battery:
            for bat in battery:
                item("Battery", bat["name"])
                item("Charge", bat["capacity"])
                item("Status", bat["status"])
        else:
            item("Battery", "Not detected")

    # ENVIRONMENT
    section("ENVIRONMENT")

    environment = data["environment"]

    item("Desktop", environment["desktop"])
    item("Shell", environment["shell"])
    item("Terminal", environment["terminal"])
    item("Display server", environment["display_server"])

    print()
    print(
        f"{GRAY}└─ H-Check finished{RESET}"
    )
    print()


# ============================================================
# ARGUMENTS
# ============================================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="h-check",
        description=(
            "H-Check - Lightweight hardware and system analyzer"
        ),
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )

    parser.add_argument(
        "--quick",
        action="store_true",
        help="Skip battery detection",
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

def main() -> int:
    args = parse_args()

    data = collect_hardware(
        quick=args.quick
    )

    if args.json:
        print(
            json.dumps(
                data,
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        display_report(data)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
