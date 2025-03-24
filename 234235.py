import os
import requests
import subprocess
import platform


def get_default_download_directory():
    """
    Determined the default download directory based on the operating system.

    For Windows and macOS, it was typically the Downloads folder within the user's home directory.
    For other systems, it defaulted to the current working directory.
    """
    system = platform.system()
    if system in ["Windows", "Darwin"]:
        return os.path.join(os.path.expanduser("~"), "Downloads")
    else:
        return "."


def download_file(url, output_directory="."):
    """
    Downloaded a file from a given URL and saved it in the specified directory.

    The filename was derived from the URL; if no filename could be determined, a default name was used.
    """
    local_filename = url.split("/")[-1]
    if not local_filename:
        local_filename = "downloaded_file"
    local_filepath = os.path.join(output_directory, local_filename)

    try:
        with requests.get(url, stream=True) as response:
            response.raise_for_status()
            with open(local_filepath, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)
        return local_filepath
    except Exception as e:
        raise Exception(f"An error occurred during download: {e}")


def convert_to_mp3(input_file, output_directory="."):
    """
    Converted a given input file to MP3 format using FFmpeg.

    The function invoked FFmpeg via a subprocess, removing any video stream if present.
    It required that FFmpeg was installed and available in the system's PATH.
    """
    base = os.path.splitext(os.path.basename(input_file))[0]
    output_file = os.path.join(output_directory, base + ".mp3")
    command = [
        "ffmpeg", "-i", input_file,
        "-vn",  # No video stream.
        "-ab", "192k",  # Audio bitrate.
        "-ar", "44100",  # Audio sampling rate.
        "-y",  # Overwrite output if exists.
        output_file
    ]
    try:
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return output_file
    except subprocess.CalledProcessError as e:
        raise Exception(f"FFmpeg conversion failed: {e}")


def main():
    print("Enter the URL of the lecture recording to download:")
    url = input("URL: ").strip()

    output_directory = input("Enter output directory (leave blank for default downloads folder): ").strip()
    if not output_directory:
        output_directory = get_default_download_directory()
        print(f"No directory specified. Using default download directory: {output_directory}")

    try:
        downloaded_file = download_file(url, output_directory)
        print(f"Downloaded file saved as: {downloaded_file}")
    except Exception as e:
        print(e)
        return

    if not downloaded_file.lower().endswith(".mp3"):
        print("File was not in MP3 format. Converting to MP3...")
        try:
            mp3_file = convert_to_mp3(downloaded_file, output_directory)
            print(f"Conversion successful. MP3 file saved as: {mp3_file}")
        except Exception as e:
            print(e)
    else:
        print("Downloaded file was already in MP3 format.")


if __name__ == '__main__':
    main()
