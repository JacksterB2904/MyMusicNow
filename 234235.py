import os
import sys
import platform
import shutil
import subprocess
import requests
import time


def check_ffmpeg_installed():
    if shutil.which("ffmpeg") is None:
        print("Error: FFmpeg is not installed or not in your system PATH.")
        print("Please install FFmpeg and ensure it is added to the PATH environment variable.")
        sys.exit(1)


def robust_get(url, stream=True):
    """
    Performed a GET request that handled rate limiting and network errors by using exponential backoff.
    The function retried indefinitely when HTTP 429 or other network errors were encountered.
    """
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

    For Windows and macOS, it defaulted to the Downloads folder in the user's home directory.
    For other systems, it defaulted to the current working directory.
    """
    system = platform.system()
    if system in ["Windows", "Darwin"]:
        return os.path.join(os.path.expanduser("~"), "Downloads")
    else:
        return "."


def download_direct(url, output_directory="."):
    """
    Downloaded a file from a direct URL and saved it in the specified directory.

    The filename was derived from the URL. If no filename could be determined, a default name was used.
    This function used robust_get to extend rate/request limits indefinitely.
    """
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
    """
    Converted the given input file to MP3 format using FFmpeg.

    The function invoked FFmpeg via a subprocess, removing any video stream if present.
    """
    base = os.path.splitext(os.path.basename(input_file))[0]
    output_file = os.path.join(output_directory, base + ".mp3")
    command = [
        "ffmpeg", "-i", input_file,
        "-vn",  # Remove any video.
        "-ab", "192k",  # Set audio bitrate.
        "-ar", "44100",  # Set audio sampling rate.
        "-y",  # Overwrite output file if it exists.
        output_file
    ]
    try:
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return output_file
    except subprocess.CalledProcessError as e:
        raise Exception(f"FFmpeg conversion failed: {e}")


def download_from_youtube(url, output_directory="."):
    try:
        import yt_dlp
    except ImportError:
        print("Error: yt_dlp is not installed. Please install it using 'pip install yt_dlp'")
        sys.exit(1)

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
    """
    Downloaded lecture recordings from Spotify by invoking spotdl.

    The function checked for the existence of the spotdl command and then ran it to download the track as MP3.
    """
    if shutil.which("spotdl") is None:
        print("Error: spotdl is not installed or not in your system PATH.")
        print("Please install it using 'pip install spotdl'")
        sys.exit(1)

    # spotdl's output template was set to save the file in the specified output directory.
    command = ["spotdl", "--output", os.path.join(output_directory, "%(title)s.%(ext)s"), url]
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        raise Exception(f"Spotify download failed: {e}")


def main():
    """
    Prompted the user for the lecture recording URL and the output directory.

    Based on the URL provided, the programme selected the appropriate download method:
      - YouTube URLs were processed using yt_dlp.
      - Spotify URLs were processed using spotdl.
      - Other direct URLs were downloaded using requests and converted to MP3 if necessary.

    The default output directory was determined by the operating system.
    """
    check_ffmpeg_installed()

    print("Enter the URL of the lecture recording to download:")
    url = input("URL: ").strip()

    output_directory = input("Enter output directory (leave blank for default downloads folder): ").strip()
    if not output_directory:
        output_directory = get_default_download_directory()
        print(f"No directory specified. Using default download directory: {output_directory}")

    try:
        if "spotify.com" in url or "open.spotify.com" in url:
            print("Detected Spotify URL. Using spotdl to download the lecture recording.")
            download_from_spotify(url, output_directory)
        elif "youtube.com" in url or "youtu.be" in url:
            print("Detected YouTube URL. Using yt_dlp to download the lecture recording as MP3.")
            download_from_youtube(url, output_directory)
        else:
            print("Detected a direct file URL. Downloading directly...")
            downloaded_file = download_direct(url, output_directory)
            print(f"Downloaded file saved as: {downloaded_file}")
            if not downloaded_file.lower().endswith(".mp3"):
                print("File was not in MP3 format. Converting to MP3...")
                mp3_file = convert_to_mp3(downloaded_file, output_directory)
                print(f"Conversion successful. MP3 file saved as: {mp3_file}")
            else:
                print("Downloaded file was already in MP3 format.")
    except Exception as e:
        print(e)


if __name__ == '__main__':
    main()
