# Making a New Narrated Book Video

Once-you've-done-it-before quick reference. End-to-end in about 10 minutes of active work.

---

## Step 1 — Scan the book on your iPhone

1. Open **Notes**, create a new note.
2. Tap the camera icon → **Scan Documents**.
3. Shoot each page one at a time. Notes auto-detects and de-warps edges.
4. Tap **Save** when done.

---

## Step 2 — Export the PDF to your Mac

Two options — pick whichever is faster:

**AirDrop (fastest):**
1. In Notes on iPhone, tap the scan to open it.
2. Tap the share icon → **AirDrop** → tap your Mac's name.
3. File lands in `~/Downloads/` automatically.

**iCloud (if AirDrop isn't cooperating):**
1. In Notes on iPhone, tap the scan → share icon → **Save to Files** → iCloud Drive → Save.
2. On Mac, open Finder → iCloud Drive → drag the PDF to `~/Downloads/`.

---

## Step 3 — Convert PDF to page images

Open Terminal. Run these commands, replacing `book_name` with a short name for this book (no spaces — use underscores):

```
cd ~/book-videos
source venv/bin/activate
mkdir input/book_name
cd input/book_name
pdftoppm -jpeg -r 150 ~/Downloads/your_file.pdf page
cd ~/book-videos
```

Verify the pages look right:

```
ls input/book_name
```

You should see `page-01.jpg`, `page-02.jpg`, etc. with zero-padded numbers. If they're already zero-padded (all same number of digits), you're good. If not, run:

```
cd input/book_name
for f in page-?.jpg; do mv "$f" "page_0${f#page-}"; done
for f in page-??.jpg; do mv "$f" "page_${f#page-}"; done
cd ~/book-videos
```

---

## Step 4 — Run the script

```
python book_to_video.py ./input/book_name ./output/book_name.mp4
```

You'll see per-page progress. A typical picture book takes 2–4 minutes.

---

## Step 5 — Watch it

```
open ./output/book_name.mp4
```

---

## Step 6 — Tune if needed

Open `book_to_video.py` in any text editor to adjust these settings at the top:

| Setting | Default | What it does |
|---|---|---|
| `TTS_SPEED` | `0.9` | Narration speed. Try `0.85` for slower, `1.0` for normal. |
| `TTS_VOICE` | `"fable"` | Voice character. Options: `alloy`, `echo`, `fable`, `nova`, `shimmer`. |
| `PAGE_TAIL_SILENCE_SEC` | `0.75` | Pause after last word before page turns. |
| `SILENT_PAGE_DURATION_SEC` | `3.0` | How long to hold pages with no text. |

After changing settings, delete the old segments and re-run (text and audio are cached — only segments and the final video regenerate):

```
rm output/.book_name_work/segment_*.mp4
rm output/book_name.mp4
python book_to_video.py ./input/book_name ./output/book_name.mp4
```

---

## Fixing a specific page

If the vision model misread a word on a particular page:

1. Press `Cmd + Shift + .` in Finder to show hidden files, or navigate directly in Terminal.
2. Open the cached text file for that page and fix it:
   ```
   open -a TextEdit output/.book_name_work/text_007.txt
   ```
3. Delete that page's audio and segment so they regenerate:
   ```
   rm output/.book_name_work/audio_007.mp3
   rm output/.book_name_work/segment_007.mp4
   ```
4. Re-run the script — only that page rebuilds, everything else is cached:
   ```
   python book_to_video.py ./input/book_name ./output/book_name.mp4
   ```

---

## Share or save

The finished file is at `output/book_name.mp4`. Options:

- **AirDrop** to iPhone/iPad for bedtime viewing
- **Upload to YouTube** — set to Unlisted so only people with the link can see it
- **Drag to a shared iCloud folder** for the family

---

## Cheat sheet (copy-paste version)

```
cd ~/book-videos
source venv/bin/activate
mkdir input/BOOKNAME && cd input/BOOKNAME
pdftoppm -jpeg -r 150 ~/Downloads/FILENAME.pdf page
cd ~/book-videos
python book_to_video.py ./input/BOOKNAME ./output/BOOKNAME.mp4
open ./output/BOOKNAME.mp4
```

Replace `BOOKNAME` and `FILENAME` with your actual names.
