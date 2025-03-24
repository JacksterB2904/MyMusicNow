import os
import sys
import platform
import shutil
import subprocess
import requests
import time
import yt_dlp

def check_ffmpeg_installed():
    if shutil.which("ffmpeg") is None:
        print("Error: FFmpeg is not installed or not in system path")
        sys.exit(1)

def robust_get(url, stream=True):
    backoff = 1
    while True:
        try:
            response = requests.get(url, stream=stream)
            if response.status_code == 429:
                print(f"Rate limited, waiting {backoff} seconds...")
                time.sleep(backoff)
                backoff *= 2
                continue
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}. Retrying in {backoff} seconds...")
            time.sleep(backoff)
            backoff *= 2

def get_default_download_directory():
    system = platform.system()
    if system in ["Windows", "Darwin"]:
        return os.path.join(os.path.expanduser("~"), "Downloads")
    return "."

def download_direct(url, output_directory="."):
    local_filename = url.split("/")[-1] or "downloaded_file"
    local_filepath = os.path.join(output_directory, local_filename)
    try:
        with robust_get(url, stream=True) as response:
            with open(local_filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        return local_filepath
    except Exception as e:
        raise Exception(f"Direct download failed: {e}")

def convert_to_mp3(input_file, output_directory="."):
    base = os.path.splitext(os.path.basename(input_file))[0]
    output_file = os.path.join(output_directory, base + ".mp3")
    command = ["ffmpeg", "-i", input_file, "-vn", "-ab", "192k", "-ar", "44100", "-y", output_file]
    try:
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return output_file
    except subprocess.CalledProcessError as e:
        raise Exception(f"FFmpeg conversion failed: {e}")

def download_from_youtube(url, output_directory="."):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(output_directory, '%(title)s.%(ext)s'),
        'writethumbnail': True,
        'postprocessors': [
            {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'},
            {'key': 'FFmpegEmbedThumbnail'}
        ],
        'quiet': False,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

def download_from_spotify(url, output_directory="."):
    if shutil.which("spotdl") is None:
        print("Error: spotdl is not installed or not in system path")
        sys.exit(1)
    command = ["spotdl", "--output", os.path.join(output_directory, "%(title)s.%(ext)s"), url]
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        raise Exception(f"Spotify download failed: {e}")

def download_from_tidal(url, output_directory="."):
    if shutil.which("tidal-dl") is None:
        print("Error: tidal-dl is not installed or not in system path")
        sys.exit(1)
    command = ["tidal-dl", "--embed-thumbnail", "--output", os.path.join(output_directory, "%(title)s.%(ext)s"), url]
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        raise Exception(f"Tidal download failed: {e}")

def process_entry(query, output_directory="."):
    if query.startswith("http://") or query.startswith("https://"):
        if "spotify.com" in query:
            print("Detected Spotify URL.")
            download_from_spotify(query, output_directory)
        elif "tidal.com" in query:
            print("Detected Tidal URL.")
            download_from_tidal(query, output_directory)
        elif "youtube.com" in query or "youtu.be" in query:
            print("Detected YouTube URL.")
            download_from_youtube(query, output_directory)
        else:
            print("Detected direct file URL.")
            downloaded_file = download_direct(query, output_directory)
            print(f"Downloaded file saved as: {downloaded_file}")
            if not downloaded_file.lower().endswith(".mp3"):
                print("Converting to MP3...")
                mp3_file = convert_to_mp3(downloaded_file, output_directory)
                print(f"MP3 saved as: {mp3_file}")
            else:
                print("File is already in MP3 format.")
    else:
        print("Processing search query:", query)
        try:
            print("Searching Spotify...")
            download_from_spotify(query, output_directory)
            return
        except Exception as e:
            print("Spotify search failed:", e)
        try:
            print("Searching Tidal...")
            download_from_tidal(query, output_directory)
            return
        except Exception as e:
            print("Tidal search failed:", e)
        try:
            yt_query = f"ytsearchplaylist:{query}" if ("album" in query.lower() or "playlist" in query.lower()) else f"ytsearch:{query}"
            print("Searching YouTube...")
            download_from_youtube(yt_query, output_directory)
            return
        except Exception as e:
            print("YouTube search failed:", e)
        try:
            sc_query = f"scsearch:{query}"
            print("Searching SoundCloud...")
            download_from_youtube(sc_query, output_directory)
            return
        except Exception as e:
            print("SoundCloud search failed:", e)
        print("All searches failed for:", query)

def main():
    check_ffmpeg_installed()
    output_directory = input("Enter output directory (blank for default downloads folder): ").strip()
    if not output_directory:
        output_directory = get_default_download_directory()
        print(f"Using default directory: {output_directory}")
    print("Enter lecture queries (URLs, names, albums, playlists, etc).")
    print("Enter 'quit' or blank to finish:")
    queries = []
    while True:
        entry = input("Lecture query: ").strip()
        if entry.lower() in ["quit", ""]:
            break
        queries.append(entry)
    for query in queries:
        process_entry(query, output_directory)

if __name__ == '__main__':
    main()
