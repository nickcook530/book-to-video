"""
server.py — Local HTTP server that turns a PDF upload into a narrated video.

Run it:
    source venv/bin/activate
    python server.py

Then from your phone (on the same Wi-Fi) or another machine:
    curl -F "file=@some_book.pdf" http://<mac-ip>:8000/upload

The server saves the PDF to ./uploads/, kicks off the conversion in a
background thread, and responds immediately with 202 Accepted. The final
.mp4 lands in ./output/<book_name>.mp4 a few minutes later.

Find your Mac's LAN IP with:  ipconfig getifaddr en0
"""

import threading
import traceback
from pathlib import Path

from flask import Flask, jsonify, request
from werkzeug.utils import secure_filename

from book_to_video import convert_pdf_to_video

PROJECT_ROOT = Path(__file__).resolve().parent
UPLOADS_DIR  = PROJECT_ROOT / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

PORT = 8000

app = Flask(__name__)


def run_job(pdf_path: Path) -> None:
    """Background-thread target. Runs the conversion and logs any failure."""
    try:
        print(f"[job] starting: {pdf_path.name}")
        output_video = convert_pdf_to_video(pdf_path)
        print(f"[job] done: {output_video}")
    except Exception:
        # Catch-all so a single bad PDF doesn't kill the process. The thread
        # dies quietly otherwise — print the traceback so you can debug.
        print(f"[job] FAILED: {pdf_path.name}")
        traceback.print_exc()


@app.get("/")
def health():
    return jsonify(status="ok", message="book-to-video server is running")


@app.post("/upload")
def upload():
    if "file" not in request.files:
        return jsonify(error="missing 'file' field"), 400

    uploaded = request.files["file"]
    if not uploaded.filename:
        return jsonify(error="empty filename"), 400

    # secure_filename strips path separators and other dangerous chars but
    # preserves the human-readable name that book_name_from_pdf() will sanitize.
    filename = secure_filename(uploaded.filename)
    if not filename.lower().endswith(".pdf"):
        return jsonify(error="file must be a .pdf"), 400

    pdf_path = UPLOADS_DIR / filename
    uploaded.save(pdf_path)
    print(f"[server] received {filename} ({pdf_path.stat().st_size} bytes)")

    # Fire-and-forget background thread. daemon=True so Ctrl-C on the server
    # doesn't hang waiting for a 3-minute conversion to finish.
    threading.Thread(target=run_job, args=(pdf_path,), daemon=True).start()

    return jsonify(status="accepted", filename=filename), 202


if __name__ == "__main__":
    print(f"Starting server on http://0.0.0.0:{PORT}")
    print("Find your Mac's LAN IP with: ipconfig getifaddr en0")
    app.run(host="0.0.0.0", port=PORT, debug=False)
