import os
from yt_dlp import YoutubeDL

ROOT_DIR = "./"

videos = {
    "fire": [
        "https://youtube.com/shorts/7Hl2qBg5zKY",
        "https://youtu.be/DDED0V8KTU0",
        "https://youtu.be/SM-yqtSU2zg",
        "https://youtu.be/_5hQVw9_8g8",
        "https://youtu.be/sNQiYf4CaLQ",
        "https://youtube.com/shorts/TbgWC3zGmyU",
    ],
    "smoke": [
        "https://youtu.be/dxDa1ztIiBg",
        "https://youtu.be/cTKNlycFoQY",
        "https://youtu.be/P3BboSPMmsk",
    ],
    "smoke_fire": [
        "https://youtu.be/PIyFtxiAx0E",
        "https://youtube.com/shorts/LtGVW42ZY5w",
        "https://youtu.be/PIyFtxiAx0E",  # Duplicate; yt-dlp will skip if already downloaded.
        "https://youtube.com/shorts/OJ7p4POdP8E",
    ],
    "no_fire_smoke": [
        "https://youtu.be/8DJi4PrdFCg",
        "https://youtu.be/umRhIdT1nW8",
        "https://youtu.be/0piTQw83NBE",
        "https://youtu.be/ms-Q3t5IqNM",
    ],
}

for category, urls in videos.items():
    save_dir = os.path.join(ROOT_DIR, category)
    os.makedirs(save_dir, exist_ok=True)

    ydl_opts = {
        "outtmpl": os.path.join(save_dir, "%(title)s.%(ext)s"),
        "format": "bv*+ba/b",  # Best video + audio, fallback to best single file
        "merge_output_format": "mp4",
        "noplaylist": True,
        "ignoreerrors": True,
    }

    with YoutubeDL(ydl_opts) as ydl:
        print(f"\nDownloading {category} videos...")
        ydl.download(urls)

print("\nDone!")