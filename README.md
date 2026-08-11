# 🕷️ E.V. Agent — AI Personal Assistant (Web & Desktop)

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.0+-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

> **E.V. Agent (Enhanced Virtual Assistant)** — An intelligent, voice-enabled AI personal assistant featuring a modern dark-mode glassmorphism Web UI, PyWebView native desktop mode, automatic wake-word activation, multi-LLM fallback routing, and persistent memory.
>
> Inspired by **E.V.** from *Spider-Man: Brand New Day (2026)*.

---

🌐 **Language / Ngôn ngữ:** [English](#english) | [Tiếng Việt](#tiếng-việt)

---

<a name="english"></a>
## 🇬🇧 English

### ✨ Features

- 🎤 **Voice-to-Text Speech Recognition**: Built-in browser speech recognition (Web Speech API) via a single-click microphone button.
- 🗣️ **Edge TTS Voice Feedback**: Natural voice synthesis using Microsoft Edge TTS (`vi-VN-HoaiMyNeural` default).
- 🧠 **Multi-LLM Fallback Architecture**: Intelligent API routing (`OpenRouter` → `Groq` → `Gemini` → `DeepSeek`). If the primary model fails or rate-limits, E.V. automatically fails over to secondary providers without interrupting the user.
- 🔧 **13 ReAct Agent Tools**:
  - `web_search`: Search Google / DuckDuckGo for live info.
  - `python_executor`: Safely run Python code snippets.
  - `shell_executor`: Execute system terminal commands (PowerShell / CMD).
  - `file_manager`: Create, read, write, delete, and list local files.
  - `app_automation`: Launch Windows desktop applications.
  - `vision`: Capture screens or process images for multimodal visual reasoning.
  - `reminder`: Schedule local reminders and notifications.
  - `guardrail`: Input validation and safety checks.
- 💾 **Dual-Layer Persistent Memory**:
  - **Short-Term Memory**: Conversation context buffer.
  - **Long-Term Memory**: Semantic vector search with ChromaDB & structured SQLite storage.
- 🖥️ **Dual Interface Modes**:
  - **Native Desktop Window**: Powered by `PyWebView` for an app-like experience.
  - **Web Application**: Accessible in any browser at `http://127.0.0.1:5000`.
- 🎙️ **Hands-Free Wake Word Activation**: Background voice listener detecting *"Hey EV"*, *"EV ơi"*, or *"Mở EV"*.

---

### 📁 Project Structure

```
ev-agent-web/
├── server.py              # Flask Web backend & API endpoints
├── main_desktop.py        # PyWebView native window launcher
├── wake_word_listener.py  # Background wake-word voice detection
├── config.py              # Configuration manager & env loader
├── run_app.vbs            # Portable background launcher for Desktop App
├── run_wake_word.vbs      # Portable background launcher for Wake Word Listener
├── brain/                 # LLM Client, fallback engine & ReAct decision loop
│   ├── llm_client.py      # Unified API wrapper (OpenRouter, Groq, Gemini, DeepSeek)
│   ├── llm_fallback.py    # Fallback chain controller
│   └── react_loop.py      # Tool execution agent loop
├── memory/                # Memory persistence layers (ChromaDB + SQLite)
├── tools/                 # Tool implementations (Web, Python, Shell, Vision, Apps...)
├── static/                # Frontend Web UI (HTML5, CSS3 Glassmorphism, Vanilla JS)
├── .env.example           # Environment template (NO SECRETS)
└── README.md              # Project documentation
```

---

### 🚀 Quick Start & Installation

#### 1. Clone the Repository
```bash
git clone https://github.com/thinhphucnguyenvo11102006-pixel/ev-agent-web.git
cd ev-agent-web
```

#### 2. Set Up Virtual Environment & Dependencies
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Install required packages
pip install -r requirements.txt
```

#### 3. Configure API Keys
Copy `.env.example` to `.env` and fill in your API key(s):
```bash
cp .env.example .env
```
Edit `.env`:
```env
OPENROUTER_API_KEY=your_openrouter_api_key_here
GROQ_API_KEY=your_groq_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
DEEPSEEK_API_KEY=your_deepseek_api_key_here
```
> **Note**: You only need at least one valid API key (OpenRouter is recommended).

---

### 🏃 Running E.V. Agent

- **Launch Native Desktop App**:
  ```bash
  python main_desktop.py
  ```
- **Launch Web Server Only**:
  ```bash
  python server.py
  ```
  Then open `http://127.0.0.1:5000` in Google Chrome or Microsoft Edge.

- **Start Wake Word Background Listener**:
  ```bash
  python wake_word_listener.py
  ```

- **Silent Windows Launch (VBS scripts)**:
  Double-click `run_app.vbs` or `run_wake_word.vbs` to run in the background without a command line window.

---
---

<a name="tiếng-việt"></a>
## 🇻🇳 Tiếng Việt

### ✨ Tính Năng Nổi Bật

- 🎤 **Nhận Diện Giọng Nói**: Tích hợp Web Speech API trực tiếp trên trình duyệt qua nút Micro 1-click.
- 🗣️ **Phản Hồi Giọng Nói Edge TTS**: Đọc phản hồi bằng giọng nói tự nhiên thông qua Microsoft Edge TTS (`vi-VN-HoaiMyNeural`).
- 🧠 **Hệ Thống Multi-LLM Chuyển Mạch Tự Động**: Tự động luân chuyển API (`OpenRouter` → `Groq` → `Gemini` → `DeepSeek`). Khi provider chính bị lỗi hoặc giới hạn rate-limit, E.V. sẽ tự động chuyển sang provider dự phòng mà không gián đoạn cuộc trò chuyện.
- 🔧 **13 Công Cụ ReAct Agent**:
  - `web_search`: Tìm kiếm thông tin trực tuyến (Google / DuckDuckGo).
  - `python_executor`: Chạy mã Python an toàn.
  - `shell_executor`: Thực thi lệnh hệ thống (PowerShell / CMD).
  - `file_manager`: Tạo, đọc, ghi, xóa và quản lý tập tin local.
  - `app_automation`: Mở và điều khiển ứng dụng Windows.
  - `vision`: Chụp màn hình và xử lý hình ảnh multimodal.
  - `reminder`: Đặt lịch hẹn và nhắc nhở local.
  - `guardrail`: Kiểm tra an toàn và lọc dữ liệu đầu vào.
- 💾 **Bộ Nhớ Lưu Trữ Hai Lớp**:
  - **Bộ nhớ ngắn hạn**: Lưu trữ ngữ cảnh cuộc trò chuyện hiện tại.
  - **Bộ nhớ dài hạn**: Tìm kiếm ngữ nghĩa bằng ChromaDB & lưu trữ cấu trúc bằng SQLite.
- 🖥️ **Giao Diện Kép (Desktop & Web)**:
  - **Ứng dụng Desktop Native**: Chạy qua `PyWebView` tạo cảm giác ứng dụng độc lập.
  - **Trình duyệt Web**: Truy cập linh hoạt tại `http://127.0.0.1:5000`.
- 🎙️ **Kích Hoạt Bằng Giọng Nói (Wake Word)**: Chạy ngầm lắng nghe câu lệnh *"Hey EV"*, *"EV ơi"*, hoặc *"Mở EV"*.

---

### 🚀 Hướng Dẫn Cài Đặt & Khởi Chạy

#### 1. Clone Repository
```bash
git clone https://github.com/thinhphucnguyenvo11102006-pixel/ev-agent-web.git
cd ev-agent-web
```

#### 2. Tạo Môi Trường Ảo & Cài Đặt Thư Viện
```bash
# Tạo virtualenv
python -m venv .venv

# Kích hoạt virtualenv (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Cài đặt thư viện phụ thuộc
pip install -r requirements.txt
```

#### 3. Cấu Hình API Key
Tạo file `.env` từ file `.env.example`:
```bash
cp .env.example .env
```
Cập nhật API Key trong file `.env`:
```env
OPENROUTER_API_KEY=nhap_openrouter_api_key_tai_day
GROQ_API_KEY=nhap_groq_api_key_tai_day
GEMINI_API_KEY=nhap_gemini_api_key_tai_day
DEEPSEEK_API_KEY=nhap_deepseek_api_key_tai_day
```
> **Lưu ý**: Chỉ cần cấu hình ít nhất 1 API key khả dụng (khuyên dùng OpenRouter).

---

### 🏃 Chạy Ứng Dụng

- **Chạy Giao Diện Desktop (PyWebView)**:
  ```bash
  python main_desktop.py
  ```
- **Chạy Web Server**:
  ```bash
  python server.py
  ```
  Sau đó truy cập `http://127.0.0.1:5000` trên Chrome hoặc Edge.

- **Chạy Lắng Nghe Từ Kích Hoạt (Wake Word Listener)**:
  ```bash
  python wake_word_listener.py
  ```

- **Khởi Chạy Ẩn Trên Windows (VBS Script)**:
  Nhấp đúp chuột vào `run_app.vbs` hoặc `run_wake_word.vbs` để chạy ứng dụng trong nền mà không mở cửa sổ CMD/PowerShell.

---

## 📝 License

Distributed under the **MIT License**. Built with ❤️ for AI Automation.
