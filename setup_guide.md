# Book-to-Video: Setup & First Book Guide

A step-by-step guide to go from zero on a Mac to your first narrated book video.

**Time estimate:** 45–60 minutes for first-time setup, plus ~10 minutes of active work per book after that.

**Cost estimate:** ~$10 upfront API credit (covers dozens of books), ~5¢ per book after.

---

## Part 1: One-Time Setup

You only do this section once. Future books jump straight to Part 2.

### Step 1 — Open Terminal

Press `Cmd + Space`, type `Terminal`, hit Enter. A window with a text prompt opens. Every command in this guide gets pasted into this window and run with Enter.

### Step 2 — Install Homebrew

Homebrew is a package manager — it installs software for you via the command line. Check if you already have it:

```
brew --version
```

If you see a version number, skip ahead. If you see `command not found`, install it:

```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Follow the prompts (it may ask for your Mac password). At the end, it prints two commands to "add Homebrew to your PATH" — copy and run both. Then verify:

```
brew --version
```

### Step 3 — Install ffmpeg and Python

`ffmpeg` stitches images and audio into video. Python runs the script.

```
brew install ffmpeg python
```

This takes a few minutes. Verify both installed:

```
ffmpeg -version
python3 --version
```

Each should print a version number.

### Step 4 — Create the project folder

```
mkdir -p ~/book-videos/input ~/book-videos/output
cd ~/book-videos
```

This makes a `book-videos` folder in your home directory with `input/` and `output/` subfolders, then moves you into it.

### Step 5 — Add the script

Download `book_to_video.py` (the artifact from earlier) and move it into `~/book-videos/`. Easiest way from Terminal:

```
mv ~/Downloads/book_to_video.py ~/book-videos/
```

Verify it's there:

```
ls
```

You should see `book_to_video.py`, `input`, and `output`.

### Step 6 — Create a Python virtual environment

This keeps the project's Python packages isolated from your system Python. Do this once:

```
python3 -m venv venv
source venv/bin/activate
```

Your prompt should now show `(venv)` at the start — that means the virtual environment is active.

Install the Python package the script needs:

```
pip install openai
```

*(If you want to use Claude for the vision step instead of GPT-4o, also run `pip install anthropic`. See Step 7 for details.)*

### Step 7 — Get your API key

You need an OpenAI account for programmatic API access. This is separate from any ChatGPT subscription you might have.

**OpenAI (handles both reading the pages and generating the narration voice):**

1. Go to [platform.openai.com](https://platform.openai.com) and sign in.
2. Go to Settings → Billing, add $5 of credit (covers hundreds of books).
3. Go to API Keys, click "Create new secret key", name it `book-videos`, copy the key (starts with `sk-...`).
4. Paste it somewhere temporary — you can't view it again later.

**Optional: add Anthropic (Claude) for the vision step.**

The script defaults to using OpenAI for everything — simpler, one bill, works great for most books. But Claude tends to handle messy/stylized text layouts a bit better, so if you run into pages the OpenAI vision model struggles with, you can swap providers.

To set that up:

1. Go to [console.anthropic.com](https://console.anthropic.com), Settings → Billing, add $5 of credit.
2. Settings → API Keys → Create Key, name it `book-videos`, copy it (starts with `sk-ant-...`).
3. Install the Anthropic package: `pip install anthropic`
4. In `book_to_video.py`, change `VISION_PROVIDER = "openai"` to `VISION_PROVIDER = "anthropic"`.

### Step 8 — Save your API key permanently

You want this available every time you open Terminal, without having to paste it in.

Open your shell config file in a basic editor:

```
nano ~/.zshrc
```

Scroll to the bottom (arrow keys) and add this line, pasting in your actual key:

```
export OPENAI_API_KEY="sk-paste-your-key-here"
```

If you also set up Anthropic (optional), add a second line:

```
export ANTHROPIC_API_KEY="sk-ant-paste-your-key-here"
```

Save and exit: `Ctrl+O`, Enter, `Ctrl+X`.

Reload the config so the key is active in your current session:

```
source ~/.zshrc
```

Verify it's set:

```
echo $OPENAI_API_KEY
```

Should print your key.

**Setup done.** You won't repeat any of this for future books.

---

## Part 2: Your First Book

### Step 9 — Pick a short book

For your first run, choose something short and simple — ideally under 20 pages with clearly printed text on mostly white backgrounds. Saves time, saves money, and makes problems easier to diagnose. Save the complex ones for after you know the pipeline works.

### Step 10 — Scan the pages with your iPhone

1. Open the **Notes** app.
2. Create a new note, tap the camera icon, choose **Scan Documents**.
3. Shoot each page one at a time. Notes auto-detects edges and de-warps the image — way better than a raw photo.
4. For books with two-page spreads where both pages have content, do one page per scan (makes narration pacing feel natural). For tight spreads that belong together, scan the whole spread.
5. When done, tap **Save**. The scan becomes a PDF attached to the note.

### Step 11 — Get the pages onto your Mac

Easiest path:

1. In the Notes app on your Mac, open the same note (syncs via iCloud).
2. Right-click the scanned PDF attachment → **Share** → **Save to Files** → save to `~/Downloads/` with a clear name like `goodnight_moon.pdf`.

### Step 12 — Convert the PDF into page images

Back in Terminal (make sure you're in `~/book-videos` with the venv active — your prompt should show `(venv)`):

```
brew install poppler
```

This only needs to happen once. Then for each book:

```
mkdir input/first_book
cd input/first_book
pdftoppm -jpeg -r 150 ~/Downloads/goodnight_moon.pdf page
cd ~/book-videos
```

That produces `page-1.jpg`, `page-2.jpg`, etc. in `input/first_book/`.

### Step 13 — Fix the filenames so they sort correctly

`pdftoppm` names files `page-1.jpg`, `page-2.jpg`, … `page-10.jpg`. Alphabetically, `page-10` sorts before `page-2`, which would scramble your video.

Zero-pad the numbers:

```
cd input/first_book
for f in page-?.jpg; do mv "$f" "page_0${f#page-}"; done
for f in page-??.jpg; do mv "$f" "page_${f#page-}"; done
cd ~/book-videos
```

Verify:

```
ls input/first_book
```

You should see `page_01.jpg`, `page_02.jpg`, … in correct order.

### Step 14 — Run the script

```
python book_to_video.py ./input/first_book ./output/first_book.mp4
```

You'll see per-page progress. Each page does: extract text → generate narration → build segment. A 20-page book takes ~2–3 minutes total.

If you see errors, jump to the Troubleshooting section below.

### Step 15 — Watch the result

```
open ./output/first_book.mp4
```

QuickTime opens and plays the video. Watch it end-to-end with a critical ear.

### Step 16 — Tune, then optionally re-run

Common things you'll want to adjust after the first listen:

- **Narration too fast?** Open `book_to_video.py`, change `TTS_SPEED = 0.9` to `0.85` or `0.8`.
- **Pages flip too abruptly?** Change `PAGE_TAIL_SILENCE_SEC = 0.75` to `1.0` or `1.25`.
- **Want a different voice?** Change `TTS_VOICE = "fable"` to `"nova"`, `"shimmer"`, `"alloy"`, or `"echo"`. Audition them at the OpenAI TTS docs.
- **Text extraction got a word wrong?** Open `output/.first_book_work/text_007.txt` (for page 7), fix the word, then delete `audio_007.mp3` and `segment_007.mp4` from the same folder.

After any change, re-run the same command:

```
python book_to_video.py ./input/first_book ./output/first_book.mp4
```

Thanks to the checkpointing, it only redoes the work affected by your changes. Voice change → all audio regenerates but text extraction is skipped. Single-page text fix → only that page's audio regenerates.

### Step 17 — Share or save

The final file is at `output/first_book.mp4`. You can:

- AirDrop it to your iPhone or iPad for bedtime viewing
- Upload it to YouTube (set to Unlisted or Private if you'd rather not publish)
- Drop it in a shared family iCloud album
- Email it to grandparents

---

## Part 3: Future Books

Once setup is done, each new book is just:

1. Scan in Notes, save PDF to Downloads
2. Open Terminal, `cd ~/book-videos`, `source venv/bin/activate`
3. `mkdir input/book_name && cd input/book_name`
4. `pdftoppm -jpeg -r 150 ~/Downloads/book_name.pdf page`
5. Run the two rename loops from Step 13
6. `cd ~/book-videos`
7. `python book_to_video.py ./input/book_name ./output/book_name.mp4`
8. `open ./output/book_name.mp4`

10 minutes of active work per book, most of that scanning pages.

---

## Troubleshooting

**"command not found: brew"** after install → close and reopen Terminal, or run the two PATH commands Homebrew printed at the end of installation.

**"command not found: ffmpeg"** → run `brew link ffmpeg`, then reopen Terminal.

**Authentication error from OpenAI (or Anthropic)** → your env var isn't loaded in this shell. Run `source ~/.zshrc`, then verify with `echo $OPENAI_API_KEY`.

**Prompt doesn't show `(venv)`** → you're not in the virtual environment. From `~/book-videos`, run `source venv/bin/activate`.

**Pages out of order in the final video** → filename sorting issue. Check `ls input/first_book` — all files should be `page_01.jpg`, `page_02.jpg`, with zero-padded numbers.

**"No images found in ..."** → wrong path, or images aren't `.jpg`/`.jpeg`/`.png`. Check with `ls input/first_book`.

**Vision model misread a word** → open the cached `text_XXX.txt` in `output/.first_book_work/`, fix it, delete the matching `audio_XXX.mp3` and `segment_XXX.mp4`, re-run.

**Narration sounds robotic or flat** → expected with the cheap TTS model. Upgrade path is to swap `generate_narration()` for ElevenLabs, which has much more natural voices.

**Credit balance hit zero mid-book** → top up on the relevant platform's billing page, re-run the same command. Cached work is preserved.

---

## What's in the work directory

After a run, `output/.first_book_work/` contains:

- `text_001.txt`, `text_002.txt`, … — extracted text per page
- `audio_001.mp3`, `audio_002.mp3`, … — narration audio per page
- `segment_001.mp4`, `segment_002.mp4`, … — per-page video segments
- `concat_list.txt` — the list ffmpeg uses to stitch them

Keep this folder until you're happy with the video. Delete it to force a full regeneration from scratch. Delete individual files to force specific steps to redo.
