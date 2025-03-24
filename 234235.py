import os
import sys
import platform
import shutil
import subprocess
import requests
import time
import yt_dlp
import spotdl

def check_ffmpeg_installed():
    if shutil.which("ffmpeg") is None:
        print("Error: FFmpeg is not installed or not in system path")
        print("Install FFmpeg")
        sys.exit(1)

def robust_get(url, stream=True):
    backoff = 1
    while True:
        try:
            response = requests.get(url, stream=stream)
            if response.status_code == 429:
                print(f"Rate limited by server, waiting {backoff} seconds...")
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
    """
    Determined the default download directory based on the operating system.
    For Windows and macOS it defaulted to the Downloads folder in the user's home directory.
    For other systems it defaulted to the current working directory.
    """
    system = platform.system()
    if system in ["Windows", "Darwin"]:
        return os.path.join(os.path.expanduser("~"), "Downloads")
    else:
        return "."

def download_direct(url, output_directory="."):
    local_filename = url.split("/")[-1]
    if not local_filename:
        local_filename = "downloaded_file"
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
    command = [
        "ffmpeg", "-i", input_file,
        "-vn",          # Remove any video stream.
        "-ab", "192k",  # Set audio bitrate.
        "-ar", "44100", # Set audio sampling rate.
        "-y",           # Overwrite output file if it exists.
        output_file
    ]
    try:
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return output_file
    except subprocess.CalledProcessError as e:
        raise Exception(f"FFmpeg conversion failed: {e}")

def download_from_youtube(url, output_directory="."):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(output_directory, '%(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': False,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

def download_from_spotify(url, output_directory="."):
    command = ["spotdl", "--output", os.path.join(output_directory, "%(title)s.%(ext)s"), url]
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        raise Exception(f"Spotify download failed: {e}")

def process_entry(query, output_directory="."):
    # Check if the entry is a URL.
    if query.startswith("http://") or query.startswith("https://"):
        if "spotify.com" in query or "open.spotify.com" in query:
            print("Detected Spotify URL.")
            download_from_spotify(query, output_directory)
        elif "youtube.com" in query or "youtu.be" in query:
            print("Detected YouTube URL.")
            download_from_youtube(query, output_directory)
        else:
            print("Detected direct file URL.")
            downloaded_file = download_direct(query, output_directory)
            print(f"Downloaded file saved as: {downloaded_file}")
            if not downloaded_file.lower().endswith(".mp3"):
                print("File was not in MP3 format. Converting to MP3...")
                mp3_file = convert_to_mp3(downloaded_file, output_directory)
                print(f"Conversion successful. MP3 file saved as: {mp3_file}")
            else:
                print("Downloaded file was already in MP3 format.")
    else:
        print("Processing search query on multiple platforms for:", query)
        # If the query suggests a full album or playlist, use playlist search mode.
        if "album" in query.lower() or "playlist" in query.lower():
            yt_query = f"ytsearchplaylist:{query}"
        else:
            yt_query = f"ytsearch:{query}"
        try:
            print("Searching YouTube...")
            download_from_youtube(yt_query, output_directory)
            return
        except Exception as e:
            print(f"YouTube search failed: {e}")
        # Try SoundCloud search using the 'scsearch:' prefix.
        sc_query = f"scsearch:{query}"
        try:
            print("Searching SoundCloud...")
            download_from_youtube(sc_query, output_directory)
            return
        except Exception as e:
            print(f"SoundCloud search failed: {e}")
        # Finally, attempt Spotify search.
        try:
            print("Searching Spotify...")
            download_from_spotify(query, output_directory)
            return
        except Exception as e:
            print(f"Spotify search failed: {e}")
        print("All searches failed for query:", query)

def main():
    check_ffmpeg_installed()
    output_directory = input("Enter output directory (leave blank for default downloads folder): ").strip()
    if not output_directory:
        output_directory = get_default_download_directory()
        print(f"No directory specified. Using default download directory: {output_directory}")
    print("Enter lecture queries (URLs, names, albums, playlists, etc).")
    print("Enter 'quit' or an empty line to finish:")
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
