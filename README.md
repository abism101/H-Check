# HCheck

**Lightweight Hardware & System Analyzer for Linux, Windows and macOS.**

HCheck is a lightweight Python utility designed to inspect a computer and display detailed information about its hardware, operating system and current environment.

The goal is simple: **get a complete overview of a machine directly from the terminal, without installing external Python packages.**

---

## ✨ Features

* 👤 **User information**

  * Username
  * Hostname
  * Home directory
  * UID

* 🖥️ **System information**

  * Operating system
  * Distribution
  * Kernel
  * Version
  * Architecture
  * Python version
  * System uptime

* 🧠 **CPU analysis**

  * CPU model
  * Architecture
  * Physical cores
  * Logical cores
  * CPU frequency
  * CPU sockets

* 🧮 **RAM analysis**

  * Total memory
  * Used memory
  * Available memory
  * Usage percentage

* 🎮 **GPU detection**

  * GPU model
  * Multiple GPU detection when available

* 💾 **Storage**

  * Mounted filesystems
  * Total capacity
  * Used space
  * Free space
  * Usage percentage

* 🌐 **Network interfaces**

  * Interface name
  * MAC address
  * IPv4 addresses

* 🔧 **Motherboard / BIOS**

  * Manufacturer
  * Product/model
  * BIOS vendor
  * BIOS version
  * BIOS date

* 🔋 **Battery**

  * Battery detection
  * Charge level
  * Battery status

* 🪟 **Environment**

  * Desktop environment
  * Shell
  * Terminal
  * Display server

* 📦 **JSON output**

  * Export system information in a machine-readable format

---

## 🚀 Installation

Clone the repository:

```bash
git clone https://github.com/USERNAME/hcheck.git
cd hcheck
```

No external Python packages are required.

Make the script executable:

```bash
chmod +x hcheck.py
```

---

## ⚡ Usage

Run HCheck normally:

```bash
python3 hcheck.py
```

Or:

```bash
./hcheck.py
```

Display the available options:

```bash
python3 hcheck.py --help
```

Show the version:

```bash
python3 hcheck.py --version
```

Run a quick scan:

```bash
python3 hcheck.py --quick
```

Output everything as JSON:

```bash
python3 hcheck.py --json
```

Save the JSON output:

```bash
python3 hcheck.py --json > hardware.json
```

---

## 📋 Example

```text
 _   _        ____ _               _
| | | |      / ___| |__   ___  ___| | __
| |_| |_____| |   | '_ \ / _ \/ __| |/ /
|  _  |_____| |___| | | |  __/ (__|   <
|_| |_|      \____|_| |_|\___|\___|_|\_\

Hardware & System Analyzer v1.0.0

┌─ USER
│ Username             jotaeme
│ Hostname             workstation
│ Home                 /home/user
│ UID                  1000

┌─ SYSTEM
│ OS                   Linux
│ Distribution         Debian GNU/Linux
│ Release              6.x
│ Kernel               6.x.x
│ Architecture         x86_64
│ Python               3.x
│ Uptime               2d 4h 32m

┌─ CPU
│ Model                Intel Core i7
│ Architecture         x86_64
│ Physical cores       6
│ Logical cores        12
│ Frequency            3200 MHz

┌─ MEMORY
│ Total                32.0 GB
│ Used                 8.4 GB
│ Available            23.6 GB
│ Usage                26.3%

┌─ GPU
│ GPU 1                AMD Radeon RX 580

┌─ STORAGE
│ /                    84.2 GB / 256.0 GB (32.9%)

┌─ NETWORK
│ eth0                 MAC: xx:xx:xx:xx:xx:xx
│                      IPv4: 192.168.1.20/24

┌─ MOTHERBOARD / BIOS
│ Manufacturer         MSI
│ Product              MAG Series
│ BIOS vendor          American Megatrends
│ BIOS version         xxxx
│ BIOS date            xxxx

└─ HCheck finished
```

---

## 🛠️ Requirements

* Python **3.9+**
* Linux, Windows or macOS
* No third-party Python dependencies

Some hardware information depends on the operating system and available system utilities.

For example, Linux systems may provide additional information through:

```text
/proc
/sys
lspci
ip
```

Running HCheck with appropriate permissions may provide access to additional hardware information.

---

## 📁 Project Structure

```text
hcheck/
├── hcheck.py
├── README.md
└── LICENSE
```

---

## 🎯 Use Cases

HCheck can be useful for:

* 🖥️ Quick hardware inventory
* 🔧 Troubleshooting computers
* 🧰 IT support
* 📊 System auditing
* 💻 Linux administration
* 🧪 Homelabs
* 📦 Hardware documentation
* 🤖 Integrating system information into other scripts

The JSON mode also makes HCheck suitable as a lightweight backend for future inventory or monitoring tools.

---

## 🔐 Privacy

HCheck runs locally and does not send system information to external servers.

All information is collected directly from the machine where the script is executed.

---

## ⚠️ Disclaimer

HCheck is intended for **legitimate system administration, diagnostics and educational purposes**.

Only run it on systems you own or are authorized to inspect.

---

## 📌 Roadmap

Potential future improvements:

* [ ] CPU temperature monitoring
* [ ] GPU temperature and VRAM information
* [ ] RAM module details
* [ ] Individual physical disk detection
* [ ] SMART information
* [ ] Network speed information
* [ ] Fan detection
* [ ] Hardware health checks
* [ ] Hardware score
* [ ] HTML report generation
* [ ] Extended JSON export
* [ ] Cross-platform improvements

---

## 📄 License

MIT License.

---

**HCheck — Know your hardware.**
