"""
book_to_video.py — Turn a folder of page images into a narrated video.

Usage:
    python book_to_video.py ./input/my_book ./output/my_book.mp4

Folder layout expected:
    ./input/my_book/
        page_01.jpg
        page_02.jpg
        ...

Pipeline per page:
    image -> [vision model] -> text -> [TTS] -> audio -> [ffmpeg] -> video segment
Then all segments are concatenated into the final video.
"""

import base64
import os
import subprocess
import sys
from pathlib import Path

from openai import OpenAI          # pip install openai

# Anthropic is only imported if VISION_PROVIDER is set to "anthropic" below.
# This keeps things simple if you want to use OpenAI for everything.

# ---------------------------------------------------------------------------
# Config — the knobs you'll actually tune
# ---------------------------------------------------------------------------

# Which provider reads the page images.
#   "openai"    — uses GPT-4o vision. Only needs OPENAI_API_KEY. Simpler setup.
#   "anthropic" — uses Claude. Needs ANTHROPIC_API_KEY too. Slightly better at
#                 messy/stylized text layouts in my experience.
VISION_PROVIDER = "openai"

VISION_MODEL_OPENAI    = "gpt-4o-mini"          # cheap and plenty good for print
VISION_MODEL_ANTHROPIC = "claude-opus-4-7"      # used only if VISION_PROVIDER = "anthropic"

TTS_MODEL    = "tts-1-hd"              # OpenAI's high quality TTS
TTS_VOICE    = "nova"                  # try: alloy, echo, fable, nova, shimmer
TTS_SPEED    = 0.9                     # slower for a 4-year-old
PAGE_TAIL_SILENCE_SEC = 0.75           # beat between pages so last word lands

# When a page has no readable text (title page, blank, pure illustration),
# hold the image this long with no audio.
SILENT_PAGE_DURATION_SEC = 3.0

# Shared prompt used by both providers for text extraction.
EXTRACTION_PROMPT = (
    "This is a page from a children's picture book. "
    "Extract ONLY the text that should be read aloud as narration. "
    "Preserve the original wording exactly — do not paraphrase. "
    "Ignore page numbers, publisher info, and decorative text. "
    "If the page has no narratable text (e.g. pure illustration, blank, "
    "or title page with only the book title), respond with exactly: NO_TEXT"
)

# ---------------------------------------------------------------------------
# Step 1: Read the page with a vision model
# ---------------------------------------------------------------------------

def extract_text_from_page(image_path: Path, vision_client) -> str:
    """
    Send the page image to the configured vision model and ask for narratable text.
    Returns empty string if the page has no text (e.g. pure illustration).

    Dispatches to OpenAI or Anthropic based on VISION_PROVIDER.
    """
    image_data = base64.standard_b64encode(image_path.read_bytes()).decode("utf-8")
    media_type = "image/jpeg" if image_path.suffix.lower() in (".jpg", ".jpeg") else "image/png"

    if VISION_PROVIDER == "openai":
        response = vision_client.chat.completions.create(
            model=VISION_MODEL_OPENAI,
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": EXTRACTION_PROMPT},
                    {"type": "image_url", "image_url": {
                        "url": f"data:{media_type};base64,{image_data}"
                    }},
                ],
            }],
        )
        text = response.choices[0].message.content.strip()

    elif VISION_PROVIDER == "anthropic":
        # Imported here so you don't need the anthropic package installed
        # unless you're actually using it.
        from anthropic import Anthropic  # noqa: F401 — type hint only

        response = vision_client.messages.create(
            model=VISION_MODEL_ANTHROPIC,
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {
                        "type": "base64", "media_type": media_type, "data": image_data
                    }},
                    {"type": "text", "text": EXTRACTION_PROMPT},
                ],
            }],
        )
        text = response.content[0].text.strip()

    else:
        raise ValueError(f"Unknown VISION_PROVIDER: {VISION_PROVIDER!r}")

    return "" if text == "NO_TEXT" else text


# ---------------------------------------------------------------------------
# Step 2: Turn text into audio
# ---------------------------------------------------------------------------

def generate_narration(text: str, output_path: Path, openai_client: OpenAI) -> None:
    """Generate a wav of the narration using OpenAI TTS."""
    with openai_client.audio.speech.with_streaming_response.create(
        model=TTS_MODEL,
        voice=TTS_VOICE,
        input=text,
        speed=TTS_SPEED,
        response_format="wav",
    ) as response:
        response.stream_to_file(output_path)


# ---------------------------------------------------------------------------
# Step 3: Build one video segment per page
# ---------------------------------------------------------------------------

def _run_ffmpeg(cmd: list[str]) -> None:
    """Run ffmpeg and surface its stderr on failure so errors are debuggable."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write("\n--- ffmpeg failed ---\n")
        sys.stderr.write(" ".join(cmd) + "\n\n")
        sys.stderr.write(result.stderr)
        sys.stderr.write("\n---------------------\n")
        raise subprocess.CalledProcessError(result.returncode, cmd)


# libx264 requires even-numbered dimensions. Scanned pages are often odd.
# Target output resolution. 1920px wide is a sensible "HD-ish" default that
# looks good on YouTube and on phone/tablet screens. Height is computed to
# preserve aspect ratio while staying even (libx264 requires even dimensions).
# The `force_original_aspect_ratio=decrease` + pad trick keeps tall pages from
# being stretched, letterboxing them cleanly instead.
TARGET_WIDTH  = 1920
TARGET_HEIGHT = 1920   # square canvas works for both portrait and landscape pages

# Video filter: scale to fit, preserve aspect, pad with black if needed.
VIDEO_FILTER = (
    f"scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=decrease,"
    f"pad={TARGET_WIDTH}:{TARGET_HEIGHT}:(ow-iw)/2:(oh-ih)/2:color=black,"
    f"setsar=1"
)

# Audio settings — used consistently across all segments so concat is clean.
AUDIO_SAMPLE_RATE = "44100"
AUDIO_CHANNELS    = "2"


def build_segment_with_audio(image_path: Path, audio_path: Path, output_path: Path) -> None:
    """
    Create an mp4 that shows `image_path` while playing `audio_path`.
    Adds a bit of trailing silence so the page doesn't flip on the last syllable.
    """
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(image_path),
        "-i", str(audio_path),
        "-vf", VIDEO_FILTER,
        "-af", f"apad=pad_dur={PAGE_TAIL_SILENCE_SEC},aresample={AUDIO_SAMPLE_RATE}",
        "-ac", AUDIO_CHANNELS,
        "-ar", AUDIO_SAMPLE_RATE,
        "-c:v", "libx264", "-tune", "stillimage", "-preset", "fast",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-r", "25",                  # lock framerate so all segments match
        "-shortest",
        str(output_path),
    ]
    _run_ffmpeg(cmd)


def build_silent_segment(image_path: Path, output_path: Path, duration: float) -> None:
    """For pages with no narration — just hold the image for `duration` seconds."""
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(image_path),
        "-f", "lavfi",
        "-i", f"anullsrc=channel_layout=stereo:sample_rate={AUDIO_SAMPLE_RATE}",
        "-vf", VIDEO_FILTER,
        "-ac", AUDIO_CHANNELS,
        "-ar", AUDIO_SAMPLE_RATE,
        "-t", str(duration),
        "-c:v", "libx264", "-tune", "stillimage", "-preset", "fast",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-r", "25",
        str(output_path),
    ]
    _run_ffmpeg(cmd)


# ---------------------------------------------------------------------------
# Step 4: Concatenate all segments into the final video
# ---------------------------------------------------------------------------

def concatenate_segments(segment_paths: list[Path], output_path: Path, work_dir: Path) -> None:
    """
    Join segments using ffmpeg's concat *filter* (not demuxer).

    The concat filter re-processes both video and audio streams, tolerating
    small parameter differences between inputs. The concat demuxer is faster
    but requires byte-perfect parameter matches across segments, which breaks
    in practice when you're mixing silent segments with audio segments and
    scanned pages with varying dimensions.
    """
    # Build the filter_complex string: "[0:v][0:a][1:v][1:a]...concat=n=N:v=1:a=1[v][a]"
    n = len(segment_paths)
    filter_parts = "".join(f"[{i}:v][{i}:a]" for i in range(n))
    filter_complex = f"{filter_parts}concat=n={n}:v=1:a=1[v][a]"

    cmd = ["ffmpeg", "-y"]
    for seg in segment_paths:
        cmd.extend(["-i", str(seg)])
    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "fast",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        str(output_path),
    ])
    _run_ffmpeg(cmd)


def extract_audio_to_mp3(video_path: Path, audio_path: Path) -> None:
    """Pull the audio track out of the final video into a standalone mp3."""
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vn",
        "-c:a", "libmp3lame", "-b:a", "192k",
        str(audio_path),
    ]
    _run_ffmpeg(cmd)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def main(input_dir: Path, output_video: Path) -> None:
    openai_client = OpenAI()   # reads OPENAI_API_KEY from env

    if VISION_PROVIDER == "openai":
        vision_client = openai_client
    elif VISION_PROVIDER == "anthropic":
        from anthropic import Anthropic
        vision_client = Anthropic()   # reads ANTHROPIC_API_KEY from env
    else:
        sys.exit(f"Unknown VISION_PROVIDER: {VISION_PROVIDER!r}")

    work_dir = output_video.parent / f".{output_video.stem}_work"
    work_dir.mkdir(parents=True, exist_ok=True)

    page_images = sorted(
        p for p in input_dir.iterdir()
        if p.suffix.lower() in (".jpg", ".jpeg", ".png")
    )
    if not page_images:
        sys.exit(f"No images found in {input_dir}")

    # Checkpointing strategy: every expensive step writes its output to the work
    # directory. On re-run, we skip any step whose output file already exists.
    # If you want to redo a step (e.g. try a new voice), just delete the
    # corresponding files from the work dir and rerun.
    segments: list[Path] = []
    for i, image_path in enumerate(page_images, start=1):
        text_path    = work_dir / f"text_{i:03d}.txt"
        audio_path   = work_dir / f"audio_{i:03d}.wav"
        segment_path = work_dir / f"segment_{i:03d}.mp4"

        # --- Step 1: extract text (cached to disk) ---
        if text_path.exists():
            text = text_path.read_text()
            print(f"[{i}/{len(page_images)}] {image_path.name} — text cached")
        else:
            print(f"[{i}/{len(page_images)}] {image_path.name} — extracting text")
            text = extract_text_from_page(image_path, vision_client)
            text_path.write_text(text)

        # --- Step 2: build the segment (skip if already built) ---
        if segment_path.exists():
            print(f"    segment cached")
        elif text:
            if not audio_path.exists():
                print(f"    generating narration")
                generate_narration(text, audio_path, openai_client)
            print(f"    building segment")
            build_segment_with_audio(image_path, audio_path, segment_path)
        else:
            print(f"    no text on page — silent segment")
            build_silent_segment(image_path, segment_path, SILENT_PAGE_DURATION_SEC)

        segments.append(segment_path)

    print(f"Concatenating {len(segments)} segments -> {output_video}")
    concatenate_segments(segments, output_video, work_dir)

    output_audio = output_video.with_suffix(".mp3")
    print(f"Extracting narration audio -> {output_audio}")
    extract_audio_to_mp3(output_video, output_audio)
    print("Done.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("Usage: python book_to_video.py <input_dir> <output_video.mp4>")
    main(Path(sys.argv[1]), Path(sys.argv[2]))
