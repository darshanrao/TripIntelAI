import os
import requests
import shutil
import datetime
from dotenv import load_dotenv
import time
import subprocess
import mimetypes

load_dotenv()

# Initialize mimetypes
mimetypes.init()

# Create a debug directory if it doesn't exist
DEBUG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'debug_audio')
os.makedirs(DEBUG_DIR, exist_ok=True)

# Set to True to keep debug files, False to clean them up after successful processing
KEEP_DEBUG_FILES = False

def identify_file_type(file_path):
    """Use multiple methods to identify the file type"""
    # First try using mimetypes
    file_type, _ = mimetypes.guess_type(file_path)
    
    # If that doesn't work, try using the file command if available
    if not file_type:
        try:
            # On macOS/Linux, the 'file' command can identify file types
            result = subprocess.run(['file', '--mime-type', file_path], 
                                    capture_output=True, text=True, check=True)
            # Extract just the mime type from the output
            file_type = result.stdout.split(': ')[1].strip()
        except (subprocess.SubprocessError, IndexError, FileNotFoundError):
            # If the file command fails or isn't available, guess based on file extension
            ext = os.path.splitext(file_path)[1].lower()
            if ext == '.mp3':
                file_type = 'audio/mpeg'
            elif ext == '.webm':
                file_type = 'audio/webm'
            elif ext == '.wav':
                file_type = 'audio/wav'
            elif ext == '.ogg':
                file_type = 'audio/ogg'
            else:
                file_type = 'application/octet-stream'  # Default type
    
    print(f"[DEBUG] File MIME type detected: {file_type}")
    return file_type

def convert_audio_to_mp3(input_file, timestamp=None):
    """
    Convert an audio file to MP3 format using ffmpeg.
    Returns the path to the converted file.
    """
    if timestamp is None:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    output_file = os.path.join(DEBUG_DIR, f'converted_{timestamp}.mp3')
    
    try:
        print(f"[DEBUG] Converting audio to MP3 format using ffmpeg...")
        # Check if ffmpeg is available
        subprocess.run(['ffmpeg', '-version'], check=True, capture_output=True)
        
        # Convert the file
        result = subprocess.run([
            'ffmpeg', '-i', input_file, 
            '-vn',  # No video
            '-ar', '44100',  # 44.1kHz sample rate
            '-ac', '1',  # Mono
            '-b:a', '128k',  # 128kbps bitrate
            '-f', 'mp3',  # MP3 format
            output_file
        ], check=True, capture_output=True)
        
        print(f"[DEBUG] Audio converted successfully to {output_file}")
        return output_file
    except subprocess.SubprocessError as e:
        print(f"[ERROR] ffmpeg conversion failed: {e}")
        return None
    except FileNotFoundError:
        print("[ERROR] ffmpeg not found. Please install ffmpeg.")
        return None

def clean_up_files(files_to_delete):
    """
    Cleanup function to delete temporary and debug files
    """
    if KEEP_DEBUG_FILES:
        print(f"[DEBUG] Debug mode is on, keeping debug files")
        return
        
    for file_path in files_to_delete:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"[DEBUG] Deleted file: {file_path}")
            except Exception as e:
                print(f"[WARNING] Could not delete file {file_path}: {e}")

def transcribe_audio(file_path, keep_files=False):
    global KEEP_DEBUG_FILES
    KEEP_DEBUG_FILES = keep_files
    
    api_key = os.getenv('DEEPGRAM_API_KEY')
    print(f"[DEBUG] Using DEEPGRAM_API_KEY: {'SET' if api_key else 'NOT SET'}")
    if not api_key:
        raise ValueError('DEEPGRAM_API_KEY environment variable not set')

    # Files to clean up after processing
    files_to_cleanup = []
    
    # Save a copy of the file for debugging
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    debug_file_path = os.path.join(DEBUG_DIR, f'audio_{timestamp}.mp3')
    
    try:
        shutil.copy2(file_path, debug_file_path)
        print(f"[DEBUG] Saved copy of audio file to {debug_file_path}")
        files_to_cleanup.append(debug_file_path)
    except Exception as e:
        print(f"[WARNING] Could not save debug copy of audio: {e}")
    
    # Identify the actual file type
    file_type = identify_file_type(file_path)
    
    base_url = 'https://api.deepgram.com/v1/listen'
    headers = {
        'Authorization': f'Token {api_key}',
    }
    
    file_size = os.path.getsize(file_path)
    print(f"[DEBUG] File to upload: {file_path}")
    print(f"[DEBUG] File size: {file_size} bytes")
    print(f"[DEBUG] Detected file type: {file_type}")
    
    # Check if file is empty or too small
    if file_size < 100:
        raise ValueError(f"Audio file is too small ({file_size} bytes)")
    
    response = None
    converted_file = None
    try:
        print(f"[DEBUG] Processing audio file...")
        
        # Try with default settings first
        with open(file_path, 'rb') as audio_file:
            print(f"[DEBUG] Sending request to Deepgram...")
            # Set basic parameters for better accuracy
            params = {
                'punctuate': 'true',
                'model': 'nova',
                'language': 'en'
            }
            response = requests.post(
                base_url, 
                headers=headers,
                params=params,
                data=audio_file  # Use 'data' instead of 'files' for binary data
            )
        
        # If first attempt didn't work, try with format parameters
        if response.status_code != 200:
            print(f"[DEBUG] First attempt failed with status {response.status_code}, trying with format specification...")
            
            # If default fails, try with explicit format parameter based on detected type
            params = {
                'punctuate': 'true',
                'model': 'nova',
                'language': 'en'
            }
            
            # Add format-specific parameters
            if 'mpeg' in file_type or 'mp3' in file_type:
                params['encoding'] = 'mp3'
            elif 'webm' in file_type:
                params['encoding'] = 'webm'
            elif 'wav' in file_type or 'x-wav' in file_type:
                params['encoding'] = 'wav'
            elif 'ogg' in file_type:
                params['encoding'] = 'ogg'
                
            print(f"[DEBUG] Using parameters: {params}")
            
            with open(file_path, 'rb') as audio_file:
                # Use data parameter directly for binary data
                response = requests.post(
                    base_url, 
                    headers=headers,
                    params=params,
                    data=audio_file
                )
        
        # If both attempts failed, try converting to MP3 as a last resort
        if response.status_code != 200:
            print(f"[DEBUG] Second attempt failed with status {response.status_code}, trying with conversion...")
            
            # Try to convert the file to a known good format
            converted_file = convert_audio_to_mp3(file_path, timestamp)
            if converted_file:
                files_to_cleanup.append(converted_file)
            
            if converted_file and os.path.exists(converted_file):
                print(f"[DEBUG] Sending converted MP3 file to Deepgram...")
                with open(converted_file, 'rb') as audio_file:
                    params = {
                        'punctuate': 'true',
                        'model': 'nova',
                        'language': 'en',
                        'encoding': 'mp3'
                    }
                    
                    # Set proper Content-Type header
                    headers_with_type = headers.copy()
                    headers_with_type['Content-Type'] = 'audio/mpeg'
                    
                    response = requests.post(
                        base_url, 
                        headers=headers_with_type,
                        params=params,
                        data=audio_file
                    )
        
        print(f"[DEBUG] Deepgram API response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"[ERROR] Deepgram API error content: {response.content}")
            # Save the error details to a file for reference
            error_file_path = os.path.join(DEBUG_DIR, f'error_{timestamp}.txt')
            with open(error_file_path, 'w') as f:
                f.write(f"Response status: {response.status_code}\n")
                f.write(f"Response content: {response.content.decode('utf-8', errors='replace')}\n")
            print(f"[DEBUG] Error details saved to {error_file_path}")
            files_to_cleanup.append(error_file_path)  # Clean up error file on retry
            response.raise_for_status()
            
        data = response.json()
        
        # Return only the main transcript string
        transcript = data['results']['channels'][0]['alternatives'][0]['transcript']
        print(f"[DEBUG] Transcription successful: '{transcript}'")
        
        # Clean up files after successful transcription
        clean_up_files(files_to_cleanup)
        
        # Optionally delete the original file if it's in the audio_files directory
        if not KEEP_DEBUG_FILES and 'audio_files' in file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"[DEBUG] Deleted original audio file: {file_path}")
            except Exception as e:
                print(f"[WARNING] Could not delete original file {file_path}: {e}")
        
        return transcript
    except Exception as e:
        if response is not None:
            print(f"[ERROR] Deepgram API error content: {response.content}")
        print(f"[ERROR] Exception during transcription: {e}")
        # Don't clean up files on error for debugging purposes
        raise e 