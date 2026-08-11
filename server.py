#!/usr/bin/env python3
"""
E.V. Agent — Web UI Server
Flask backend serving the web interface and API endpoints.
"""

import sys
import os
import json
import asyncio
import logging
import threading
import queue
from pathlib import Path
from datetime import datetime

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context
import config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("chromadb").setLevel(logging.WARNING)

logger = logging.getLogger("ev.web")

from brain.llm_fallback import LLMFallbackChain
from brain.react_loop import ReActLoop
from tools.registry import ToolRegistry
from tools.python_executor import execute_python
from tools.shell_executor import execute_shell
from tools.file_manager import read_file, write_file, list_files
from tools.web_search import web_search
from tools.reminder import set_reminder, get_reminders
from tools.vision import take_screenshot, analyze_image
from tools.app_automation import automate_app
from memory.memory_manager import MemoryManager


class WebContextAssembler:
    """Context assembler for web mode."""

    def __init__(self, memory: MemoryManager):
        self.memory = memory
        self._system_prompt = self._load_system_prompt()

    def _load_system_prompt(self) -> str:
        prompt_path = PROJECT_ROOT / "brain" / "prompts" / "system_prompt.md"
        try:
            return prompt_path.read_text(encoding="utf-8")
        except Exception:
            return "You are E.V., a helpful and cheerful AI assistant."

    async def assemble(self, user_input: str):
        parts = [self._system_prompt]
        now = datetime.now()
        parts.append(f"\n## Thông tin hiện tại\n- Ngày giờ: {now.strftime('%Y-%m-%d %H:%M:%S (%A)')}")

        memory_context = self.memory.get_context_for_prompt(user_input)
        if memory_context:
            parts.append(memory_context)

        cleaned = user_input.strip().lower()
        trivial = {"chào", "hi", "hello", "xin chào", "ok", "cảm ơn", "bye"}
        if len(cleaned.split()) >= 4 or not any(g in cleaned for g in trivial):
            memories = await self.memory.recall(user_input, top_k=3)
            if memories:
                lines = [f"- {m['text']}" for m in memories if m.get("relevance", 0) >= 0.5]
                if lines:
                    parts.append("\n## Relevant Memories\n" + "\n".join(lines))

        system_content = "\n".join(parts)
        self.memory.short_term.set_system_message(system_content)
        return self.memory.get_messages()


# ===== Lazy Backend State =====
memory = None
llm_chain = None
tool_registry = None
react_loop = None
context_assembler = None
_backend_lock = threading.Lock()


def get_backend():
    """Lazy initialize backend components on demand or in background thread."""
    global memory, llm_chain, tool_registry, react_loop, context_assembler
    if react_loop is not None and tool_registry is not None:
        return memory, llm_chain, tool_registry, react_loop, context_assembler

    with _backend_lock:
        if react_loop is not None and tool_registry is not None:
            return memory, llm_chain, tool_registry, react_loop, context_assembler

        logger.info("Initializing E.V. backend components...")
        _memory = MemoryManager()
        _llm_chain = LLMFallbackChain()
        _tool_registry = ToolRegistry()
        _react_loop = ReActLoop(llm_client=_llm_chain, tool_registry=_tool_registry)
        _react_loop.set_structured_memory(_memory.structured)
        _context_assembler = WebContextAssembler(_memory)

        # Register tools
        _tool_registry.register("execute_python", execute_python, "Execute Python code")
        _tool_registry.register("execute_shell", execute_shell, "Execute shell command")
        _tool_registry.register("read_file", read_file, "Read file contents")
        _tool_registry.register("write_file", write_file, "Write to file")
        _tool_registry.register("list_files", list_files, "List directory contents")
        _tool_registry.register("web_search", web_search, "Search the web")
        _tool_registry.register("set_reminder", set_reminder, "Set a reminder")
        _tool_registry.register("get_reminders", get_reminders, "Get reminders")
        _tool_registry.register("take_screenshot", take_screenshot, "Take screenshot")
        _tool_registry.register("analyze_image", analyze_image, "Analyze image")
        _tool_registry.register("automate_app", automate_app, "Automate app")

        async def _remember_fact(fact: str, category: str = "general") -> str:
            await _memory.remember(fact, category=category)
            return f"Remembered: [{category}] {fact}"

        async def _recall_facts(query: str, category: str = None) -> str:
            memories = await _memory.recall(query, top_k=5)
            if not memories:
                return "No relevant memories found."
            return "\n".join(f"- ({m['relevance']:.0%}) {m['text']}" for m in memories)

        _tool_registry.register("remember_fact", _remember_fact, "Remember a fact")
        _tool_registry.register("recall_facts", _recall_facts, "Recall facts from memory")
        _tool_registry.load_schemas()

        logger.info(f"Registered {len(_tool_registry.list_tools())} tools")
        logger.info(f"LLM chain: {' → '.join(c.name for c in _llm_chain.clients)}")

        memory = _memory
        llm_chain = _llm_chain
        tool_registry = _tool_registry
        context_assembler = _context_assembler
        react_loop = _react_loop

        return memory, llm_chain, tool_registry, react_loop, context_assembler



# Trigger background pre-initialization of ML models
threading.Thread(target=get_backend, daemon=True).start()


# ===== Flask App =====
app = Flask(__name__, static_folder="static", static_url_path="/static")


@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/status", methods=["GET"])
def status():
    """Get system status."""
    if memory is None:
        return jsonify({
            "status": "initializing",
            "tools": 13,
        })

    return jsonify({
        "status": "online",
        "llm": llm_chain.get_status(),
        "memory": memory.get_stats(),
        "tools": len(tool_registry.list_tools()),
    })


@app.route("/api/tools", methods=["GET"])
def get_tools_info():
    """Get list of available tools for UI autocomplete."""
    mem, llms, tools_reg, loop, ctx_asm = get_backend()
    return jsonify({"tools": tools_reg.get_tool_info_list()})


@app.route("/api/chat", methods=["POST"])
def chat():
    """Handle a chat message from the web UI (Non-streaming fallback)."""
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "Missing 'message' field"}), 400

    raw_message = data["message"].strip()
    if not raw_message:
        return jsonify({"error": "Empty message"}), 400

    is_tool_mode = raw_message.startswith("/")
    user_message = raw_message[1:].strip() if is_tool_mode else raw_message
    if not user_message:
        user_message = raw_message

    logger.info(f"User (ToolMode={is_tool_mode}): {user_message[:100]}")

    mem, llms, tools_reg, loop, ctx_asm = get_backend()
    mem.add_user_message(raw_message)

    tools_used = []
    tools_schemas = tools_reg.get_schemas()

    async def _process():
        messages = await ctx_asm.assemble(user_message)

        async def on_tool_call(name, args):
            tools_used.append({"name": name, "args": str(args)[:100]})

        response_text, _ = await loop.run(
            messages=messages,
            tools=tools_schemas,
            on_tool_call=on_tool_call
        )
        return response_text

    try:
        response_text = asyncio.run(_process())
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        response_text = f"Xin lỗi, đã xảy ra lỗi khi xử lý: {e}"

    mem.add_assistant_message(response_text)
    return jsonify({
        "response": response_text,
        "tools_used": tools_used,
        "is_tool_mode": is_tool_mode,
    })


# Uploads folder setup
UPLOAD_DIR = config.DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


@app.route("/uploads/<path:filename>")
def serve_upload(filename):
    """Serve uploaded user files/images."""
    return send_from_directory(UPLOAD_DIR, filename)


@app.route("/api/upload", methods=["POST"])
def upload_file():
    """Handle file & image uploads from Web UI."""
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if not file or not file.filename:
        return jsonify({"error": "No selected file"}), 400

    import base64
    import mimetypes
    import uuid

    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg", ".ico", ".tiff"}
    TEXT_EXTENSIONS = {".txt", ".md", ".py", ".js", ".html", ".css", ".json", ".csv", ".xml", ".vbs", ".sh", ".c", ".cpp", ".h", ".java", ".ts", ".log", ".yaml", ".yml", ".ini", ".conf", ".sql", ".env"}

    filename = file.filename
    ext = Path(filename).suffix.lower()
    unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}{ext or '.bin'}"
    filepath = UPLOAD_DIR / unique_filename

    file.save(str(filepath))

    mime_type, _ = mimetypes.guess_type(filename)
    if not mime_type:
        if ext in IMAGE_EXTENSIONS:
            mime_type = f"image/{ext.replace('.', '')}"
        else:
            mime_type = "application/octet-stream"

    is_image = mime_type.startswith("image/") or ext in IMAGE_EXTENSIONS
    file_size = filepath.stat().st_size
    file_url = f"/uploads/{unique_filename}"

    b64_str = ""
    text_content = ""

    if is_image:
        try:
            with open(filepath, "rb") as f:
                b64_str = base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            logger.error(f"Error reading image base64: {e}")
    else:
        # Read text preview for document/code files (< 500KB)
        if file_size < 500_000 and (ext in TEXT_EXTENSIONS or mime_type.startswith("text/")):
            try:
                text_content = filepath.read_text(encoding="utf-8", errors="replace")
            except Exception:
                pass

    return jsonify({
        "status": "success",
        "filename": filename,
        "unique_filename": unique_filename,
        "filepath": str(filepath),
        "filetype": mime_type,
        "size": file_size,
        "url": file_url,
        "is_image": is_image,
        "base64": b64_str,
        "text_content": text_content,
    })


@app.route("/api/history", methods=["GET"])
def get_chat_history():
    """Get top 5 recent conversation sessions."""
    mem, _, _, _, _ = get_backend()
    sessions = mem.structured.get_recent_sessions(limit=5)
    return jsonify({"status": "success", "sessions": sessions, "current_session_id": mem.session_id})


@app.route("/api/history/<session_id>", methods=["GET"])
def get_session_details(session_id):
    """Get full message log for a specific session and load into active memory."""
    mem, _, _, _, _ = get_backend()
    messages = mem.structured.get_session_messages(session_id)
    mem.session_id = session_id
    mem.short_term.clear()
    for m in messages:
        if m["role"] == "user":
            mem.short_term.add_user_message(m["content"])
        elif m["role"] == "assistant":
            mem.short_term.add_assistant_message(m["content"], m.get("tool_calls"))
    return jsonify({"status": "success", "session_id": session_id, "messages": messages})


@app.route("/api/history/<session_id>", methods=["DELETE"])
def delete_session_history(session_id):
    """Delete a session from history."""
    mem, _, _, _, _ = get_backend()
    mem.structured.delete_session(session_id)
    if mem.session_id == session_id:
        mem.session_id = datetime.now().strftime("session_%Y%m%d_%H%M%S")
        mem.short_term.clear()
    return jsonify({"status": "success", "deleted_session_id": session_id, "new_session_id": mem.session_id})


@app.route("/api/chat/stream", methods=["POST"])
def chat_stream():
    """Stream chat response using Server-Sent Events (SSE)."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON payload"}), 400

    raw_message = data.get("message", "").strip()
    attachments = data.get("attachments", [])
    session_id = data.get("session_id")

    if not raw_message and not attachments:
        return jsonify({"error": "Empty message and no attachments"}), 400

    is_tool_mode = raw_message.startswith("/")
    user_message = raw_message[1:].strip() if is_tool_mode else raw_message
    if not user_message and raw_message:
        user_message = raw_message
    elif not user_message and attachments:
        user_message = "Hãy xem tệp đính kèm bên dưới và giúp tôi phân tích/xử lý."

    logger.info(f"User Stream (ToolMode={is_tool_mode}, Attachments={len(attachments)}): {user_message[:100]}")

    mem, llms, tools_reg, loop, ctx_asm = get_backend()
    if session_id:
        mem.session_id = session_id
    mem.add_user_message(raw_message or f"[Đã gửi {len(attachments)} tệp đính kèm]")

    tools_schemas = tools_reg.get_schemas()
    q = queue.Queue()

    def background_worker():
        async def _async_task():
            try:
                # 1. Start thinking timer
                q.put(f"data: {json.dumps({'type': 'thinking_start', 'is_tool_mode': True})}\n\n")
                q.put(f"data: {json.dumps({'type': 'thinking_step', 'step': 'Đang phân tích câu hỏi & nạp bộ nhớ...'})}\n\n")

                messages = await ctx_asm.assemble(user_message)

                # Process attachments into prompt context / vision format
                if attachments:
                    doc_context_parts = []
                    has_images = False
                    for att in attachments:
                        fname = att.get("filename", "file")
                        fpath = att.get("filepath", "")
                        if att.get("text_content"):
                            doc_context_parts.append(f"\n\n📎 **Nội dung tệp đính kèm (`{fname}`)** (Đường dẫn: `{fpath}`):\n```\n{att['text_content']}\n```")
                        elif att.get("is_image") and att.get("base64"):
                            has_images = True
                            doc_context_parts.append(f"\n\n📎 **Hình ảnh đính kèm (`{fname}`)** (Đường dẫn tệp: `{fpath}`)")
                        else:
                            doc_context_parts.append(f"\n\n📎 **Tệp đính kèm (`{fname}`)** (Đường dẫn tệp: `{fpath}`)")

                    full_text_prompt = user_message + "".join(doc_context_parts)

                    if messages:
                        if has_images:
                            content_list = [{"type": "text", "text": full_text_prompt}]
                            for att in attachments:
                                if att.get("is_image") and att.get("base64"):
                                    mime = att.get("filetype", "image/png")
                                    if not mime.startswith("image/"):
                                        mime = "image/png"
                                    content_list.append({
                                        "type": "image_url",
                                        "image_url": {"url": f"data:{mime};base64,{att['base64']}"}
                                    })
                            messages[-1]["content"] = content_list
                        else:
                            messages[-1]["content"] = full_text_prompt

                async def on_thinking(iteration):
                    q.put(f"data: {json.dumps({'type': 'thinking_step', 'step': f'Vòng tư duy {iteration}: Đang suy luận kế hoạch tiếp theo...', 'iteration': iteration})}\n\n")

                async def on_tool_call(name, args):
                    q.put(f"data: {json.dumps({'type': 'tool_call', 'name': name, 'args': str(args)[:300]})}\n\n")

                async def on_tool_result(name, result):
                    summary = f"Nhận được kết quả từ {name} ({len(str(result))} ký tự)"
                    q.put(f"data: {json.dumps({'type': 'tool_result', 'name': name, 'result_summary': summary})}\n\n")

                response_text, _ = await loop.run(
                    messages=messages,
                    tools=tools_schemas,
                    on_thinking=on_thinking,
                    on_tool_call=on_tool_call,
                    on_tool_result=on_tool_result,
                )

                q.put(f"data: {json.dumps({'type': 'thinking_step', 'step': 'Đang tổng hợp câu trả lời...'})}\n\n")
                q.put(f"data: {json.dumps({'type': 'thinking_done'})}\n\n")

                # Stream full response text
                q.put(f"data: {json.dumps({'type': 'chunk', 'content': response_text})}\n\n")
                mem.add_assistant_message(response_text)

                q.put(f"data: {json.dumps({'type': 'done'})}\n\n")
            except Exception as e:
                logger.error(f"Stream error: {e}", exc_info=True)
                q.put(f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n")
            finally:
                q.put(None)

        try:
            asyncio.run(_async_task())
        except Exception as ex:
            logger.error(f"Worker exception: {ex}")
            q.put(None)

    threading.Thread(target=background_worker, daemon=True).start()

    def generate():
        while True:
            item = q.get()
            if item is None:
                break
            yield item

    return Response(stream_with_context(generate()), mimetype="text/event-stream")




import re

def clean_text_for_tts(text: str) -> str:
    """Clean markdown, code blocks, URLs, and emojis for TTS reading."""
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'`[^`]*`', '', text)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    text = re.sub(r'[\*\#\_~]+', '', text)
    text = re.sub(r'https?://\S+', '', text)
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E6-\U0001F1FF"
        "\U0001F900-\U0001F9FF"
        "\U0001FA00-\U0001FA6F"
        "\U0001FA70-\U0001FAFF"
        "\u2600-\u26FF"
        "\u2700-\u27BF"
        "\uFE0F"
        "\u200D"
        "]+", flags=re.UNICODE
    )
    text = emoji_pattern.sub(r"", text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


@app.route("/api/tts", methods=["POST"])
def tts():
    """Generate TTS audio for a text response using Edge TTS."""
    data = request.get_json()
    raw_text = data.get("text", "").strip()
    if not raw_text:
        return jsonify({"error": "Empty text"}), 400

    text = clean_text_for_tts(raw_text)
    if not text:
        return jsonify({"error": "No readable text after cleanup"}), 400

    async def _generate_audio():
        import edge_tts
        tts_dir = config.DATA_DIR / "temp"
        tts_dir.mkdir(exist_ok=True)
        out_file = tts_dir / "tts_output.mp3"

        communicate = edge_tts.Communicate(
            text,
            voice=config.TTS_VOICE,
            rate=config.TTS_RATE,
            pitch=config.TTS_PITCH
        )
        await communicate.save(str(out_file))
        return out_file

    try:
        audio_file = asyncio.run(_generate_audio())
        with open(audio_file, "rb") as f:
            audio_bytes = f.read()

        return Response(audio_bytes, mimetype="audio/mpeg")

    except Exception as e:
        logger.error(f"TTS error: {e}")
        return jsonify({"error": f"TTS generation failed: {e}"}), 500


if __name__ == "__main__":
    app.run(
        host=config.WEB_HOST,
        port=config.WEB_PORT,
        debug=config.DEBUG,
    )
