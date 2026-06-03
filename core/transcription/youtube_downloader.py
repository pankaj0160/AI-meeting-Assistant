import yt_dlp
from pathlib import Path
import re


def sanitize_filename(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "", name)


def download_youtube(
    url: str,
    output_dir: str = "uploads/audio"
)-> dict:

    Path(output_dir).mkdir(exist_ok=True)

    with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
        info = ydl.extract_info(url, download=False)

    title = sanitize_filename(info["title"])

    output_template = f"{output_dir}/{title}.%(ext)s"

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    return {
        "title": title,
        "audio_file": str(Path(output_dir) / f"{title}.mp3")
    }


if __name__ == "__main__":
    url = input("Enter YouTube URL: ")

    result = download_youtube(url)

    print(f"Title: {result['title']}")
    print(f"File: {result['audio_file']}")