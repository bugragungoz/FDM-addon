#!/usr/bin/env python3
"""
Croxz Universal Downloader Bridge
Handles media extraction via yt-dlp and direct file downloads
"""

import sys
import json
import subprocess
import shutil
import re
import os
import unicodedata
from urllib.parse import urlparse, unquote
from typing import Optional, Dict, Any, List


def sanitize_filename(title: str, max_length: int = 200) -> str:
    """
    Convert title to a clean ASCII filename.
    - Transliterates unicode to ASCII
    - Removes invalid filename characters
    - Replaces spaces with underscores
    - Limits length
    """
    if not title:
        return "download"
    
    # Unicode normalization and ASCII transliteration
    # NFD decomposes characters, then we filter to ASCII
    normalized = unicodedata.normalize('NFKD', title)
    ascii_text = normalized.encode('ascii', 'ignore').decode('ascii')
    
    # If we lost too much, try a simpler approach
    if len(ascii_text) < len(title) * 0.3:
        # Replace common unicode characters manually
        replacements = {
            # Turkish
            '\u011f': 'g', '\u011e': 'G',  # g breve
            '\u0131': 'i', '\u0130': 'I',  # dotless i, dotted I
            '\u015f': 's', '\u015e': 'S',  # s cedilla
            '\u00fc': 'u', '\u00dc': 'U',  # u umlaut
            '\u00f6': 'o', '\u00d6': 'O',  # o umlaut
            '\u00e7': 'c', '\u00c7': 'C',  # c cedilla
            # German
            '\u00e4': 'ae', '\u00c4': 'Ae',  # a umlaut
            '\u00df': 'ss',  # eszett
            # French/Spanish
            '\u00e9': 'e', '\u00e8': 'e', '\u00ea': 'e', '\u00eb': 'e',
            '\u00e0': 'a', '\u00e1': 'a', '\u00e2': 'a',
            '\u00f1': 'n', '\u00d1': 'N',
            # Common symbols
            '\u2019': "'", '\u2018': "'",  # smart quotes
            '\u201c': '"', '\u201d': '"',
            '\u2013': '-', '\u2014': '-',  # dashes
            '\u2026': '...',  # ellipsis
            '\u00a9': '(c)', '\u00ae': '(r)',
            '\u2122': '(tm)',
        }
        
        temp = title
        for old, new in replacements.items():
            temp = temp.replace(old, new)
        
        # Try again with replacements
        normalized = unicodedata.normalize('NFKD', temp)
        ascii_text = normalized.encode('ascii', 'ignore').decode('ascii')
    
    # Remove or replace invalid filename characters
    # Windows invalid: \ / : * ? " < > |
    # Also remove control characters
    invalid_chars = r'[\\/:*?"<>|\x00-\x1f]'
    clean = re.sub(invalid_chars, '', ascii_text)
    
    # Replace multiple spaces/underscores with single underscore
    clean = re.sub(r'[\s_]+', '_', clean)
    
    # Remove leading/trailing underscores and dots
    clean = clean.strip('_. ')
    
    # Limit length (leave room for extension)
    if len(clean) > max_length:
        clean = clean[:max_length].rstrip('_')
    
    # Fallback if empty
    if not clean:
        return "download"
    
    return clean


def generate_filename(title: str, video_id: str = None, height: int = None, 
                      ext: str = "mp4", include_quality: bool = True) -> str:
    """Generate a clean filename from video metadata"""
    
    base_name = sanitize_filename(title)
    
    parts = [base_name]
    
    # Add quality indicator if available
    if include_quality and height:
        parts.append(f"{height}p")
    
    # Add video ID for uniqueness (shortened)
    if video_id and len(video_id) <= 15:
        parts.append(f"[{video_id}]")
    
    filename = "_".join(parts)
    
    return filename


# File extensions by category
ARCHIVE_EXTENSIONS = {
    "zip", "rar", "7z", "tar", "gz", "bz2", "xz", "iso", "cab", "arj", "lzh", "ace"
}

EXECUTABLE_EXTENSIONS = {
    "exe", "msi", "dmg", "pkg", "deb", "rpm", "appimage", "apk", "ipa", "run", "bin", "sh", "bat", "cmd", "ps1"
}

DOCUMENT_EXTENSIONS = {
    "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "odt", "ods", "odp", "rtf", "txt", "csv", "epub", "mobi"
}

IMAGE_EXTENSIONS = {
    "jpg", "jpeg", "png", "gif", "webp", "bmp", "svg", "ico", "tiff", "tif", "psd", "ai", "raw", "cr2", "nef"
}

AUDIO_EXTENSIONS = {
    "mp3", "m4a", "wav", "flac", "ogg", "aac", "wma", "opus", "aiff", "ape", "alac"
}

VIDEO_EXTENSIONS = {
    "mp4", "mkv", "webm", "avi", "mov", "wmv", "flv", "m4v", "mpeg", "mpg", "3gp", "ts", "m2ts", "vob"
}

FONT_EXTENSIONS = {
    "ttf", "otf", "woff", "woff2", "eot", "fon"
}

CODE_EXTENSIONS = {
    "js", "py", "java", "cpp", "c", "h", "cs", "php", "rb", "go", "rs", "swift", "kt", "scala", "sql"
}

ALL_DIRECT_EXTENSIONS = (
    ARCHIVE_EXTENSIONS | EXECUTABLE_EXTENSIONS | DOCUMENT_EXTENSIONS |
    IMAGE_EXTENSIONS | AUDIO_EXTENSIONS | VIDEO_EXTENSIONS |
    FONT_EXTENSIONS | CODE_EXTENSIONS
)


def get_file_category(ext: str) -> str:
    """Get category for file extension"""
    ext = ext.lower()
    if ext in ARCHIVE_EXTENSIONS:
        return "archive"
    elif ext in EXECUTABLE_EXTENSIONS:
        return "executable"
    elif ext in DOCUMENT_EXTENSIONS:
        return "document"
    elif ext in IMAGE_EXTENSIONS:
        return "image"
    elif ext in AUDIO_EXTENSIONS:
        return "audio"
    elif ext in VIDEO_EXTENSIONS:
        return "video"
    elif ext in FONT_EXTENSIONS:
        return "font"
    elif ext in CODE_EXTENSIONS:
        return "code"
    return "file"


def extract_filename_from_url(url: str) -> str:
    """Extract filename from URL"""
    parsed = urlparse(url)
    path = unquote(parsed.path)
    
    # Get the last part of the path
    filename = os.path.basename(path)
    
    # Remove query string artifacts
    if "?" in filename:
        filename = filename.split("?")[0]
    
    return filename if filename else "download"


def get_extension_from_url(url: str) -> Optional[str]:
    """Extract file extension from URL"""
    filename = extract_filename_from_url(url)
    if "." in filename:
        ext = filename.rsplit(".", 1)[-1].lower()
        # Validate it's a reasonable extension (not too long, alphanumeric)
        if len(ext) <= 10 and ext.isalnum():
            return ext
    return None


def is_direct_download_url(url: str) -> bool:
    """Check if URL points to a direct downloadable file"""
    ext = get_extension_from_url(url)
    return ext is not None and ext in ALL_DIRECT_EXTENSIONS


def find_ytdlp() -> Optional[str]:
    """Find yt-dlp executable"""
    ytdlp_path = shutil.which("yt-dlp")
    if ytdlp_path:
        return ytdlp_path
    
    possible_paths = [
        os.path.expandvars(r"%LOCALAPPDATA%\yt-dlp\yt-dlp.exe"),
        os.path.expandvars(r"%APPDATA%\yt-dlp\yt-dlp.exe"),
        r"C:\yt-dlp\yt-dlp.exe",
        os.path.expanduser("~/.local/bin/yt-dlp"),
        "/usr/local/bin/yt-dlp",
        "/usr/bin/yt-dlp",
    ]
    
    for path in possible_paths:
        if os.path.isfile(path):
            return path
    
    return None


def create_direct_download_result(url: str) -> Dict[str, Any]:
    """Create result for direct file download"""
    original_filename = extract_filename_from_url(url)
    ext = get_extension_from_url(url) or "bin"
    category = get_file_category(ext)
    
    # Clean the filename - remove extension for processing
    name_without_ext = original_filename
    if "." in original_filename:
        name_without_ext = original_filename.rsplit(".", 1)[0]
    
    clean_name = sanitize_filename(name_without_ext)
    
    # Determine protocol
    protocol = "https" if url.startswith("https") else "http"
    
    # Build format based on category
    fmt = {
        "url": url,
        "protocol": protocol,
        "ext": ext,
        "format": f"{category}/{ext}",
        "_filename": clean_name
    }
    
    # For video/audio files, set appropriate ext fields
    if category == "video":
        fmt["video_ext"] = ext
    elif category == "audio":
        fmt["audio_ext"] = ext
    
    return {
        "id": clean_name,
        "title": clean_name,
        "original_title": original_filename,
        "webpage_url": url,
        "formats": [fmt],
        "category": category,
        "direct_download": True
    }


def check_ytdlp_version() -> Optional[str]:
    """Check if yt-dlp needs update"""
    ytdlp = find_ytdlp()
    if not ytdlp:
        return None
    try:
        result = subprocess.run(
            [ytdlp, "--version"],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except:
        return None


def extract_with_ytdlp(url: str, playlist: bool = False) -> Dict[str, Any]:
    """Extract media info using yt-dlp"""
    ytdlp = find_ytdlp()
    if not ytdlp:
        return {"error": "yt-dlp not found. Install it for media extraction support."}
    
    cmd = [
        ytdlp,
        "--dump-json",
        "--no-warnings",
        "--no-progress",
        "--ignore-errors",
        "--no-check-certificates",
    ]
    
    if playlist:
        cmd.extend(["--flat-playlist", "--yes-playlist"])
    else:
        cmd.append("--no-playlist")
    
    cmd.append(url)
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            encoding="utf-8",
            errors="replace"
        )
        
        if result.returncode != 0 and not result.stdout.strip():
            error_msg = result.stderr.strip() if result.stderr else "Unknown error"
            return {"error": error_msg}
        
        output = result.stdout.strip()
        if not output:
            return {"error": "No data returned from yt-dlp"}
        
        lines = output.split("\n")
        json_objects = []
        
        for line in lines:
            line = line.strip()
            if line:
                try:
                    json_objects.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        
        if not json_objects:
            return {"error": "Failed to parse yt-dlp output"}
        
        if len(json_objects) == 1:
            return transform_single(json_objects[0])
        else:
            return transform_playlist(json_objects, url)
            
    except subprocess.TimeoutExpired:
        return {"error": "Extraction timeout (120s)"}
    except Exception as e:
        return {"error": str(e)}


def has_video(fmt: Dict[str, Any]) -> bool:
    """Check if format has video stream"""
    vcodec = fmt.get("vcodec", "none")
    return vcodec and vcodec != "none"


def has_audio(fmt: Dict[str, Any]) -> bool:
    """Check if format has audio stream"""
    acodec = fmt.get("acodec", "none")
    return acodec and acodec != "none"


def is_combined_format(fmt: Dict[str, Any]) -> bool:
    """Check if format has both video and audio"""
    return has_video(fmt) and has_audio(fmt)


def safe_int(value, default: int = 0) -> int:
    """Safely convert value to int, handling None and invalid types"""
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def format_filesize(size_bytes) -> str:
    """Format file size in human readable format"""
    if size_bytes is None:
        return ""
    try:
        size = float(size_bytes)
        if size < 1024:
            return f"{int(size)}B"
        elif size < 1024 * 1024:
            return f"{size/1024:.1f}KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size/(1024*1024):.1f}MB"
        else:
            return f"{size/(1024*1024*1024):.2f}GB"
    except (TypeError, ValueError):
        return ""


def get_format_quality_score(fmt: Dict[str, Any]) -> int:
    """Calculate quality score for sorting formats"""
    score = 0
    
    # Combined formats get highest priority
    if is_combined_format(fmt):
        score += 100000
    
    # Height-based score
    height = safe_int(fmt.get("height"), 0)
    score += height * 10
    
    # Bitrate score
    tbr = safe_int(fmt.get("tbr"), 0)
    score += tbr
    
    # Prefer mp4 over webm
    ext = fmt.get("ext") or ""
    if ext == "mp4":
        score += 500
    elif ext == "webm":
        score += 100
    
    # FPS bonus
    fps = safe_int(fmt.get("fps"), 0)
    if fps >= 60:
        score += 200
    elif fps >= 30:
        score += 100
    
    return score


def merge_video_audio_formats(formats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Create merged video+audio format entries for FDM.
    FDM doesn't auto-merge, so we prioritize combined formats
    and create virtual merged entries for separate streams.
    """
    combined = []
    video_only = []
    audio_only = []
    
    for fmt in formats:
        # Skip formats without URL
        if not fmt.get("url"):
            continue
        # Skip storyboard/mhtml formats
        if fmt.get("ext") == "mhtml" or fmt.get("vcodec") == "images":
            continue
            
        if is_combined_format(fmt):
            combined.append(fmt)
        elif has_video(fmt):
            video_only.append(fmt)
        elif has_audio(fmt):
            audio_only.append(fmt)
    
    result = []
    
    # Add combined formats first (these work directly)
    for fmt in combined:
        result.append(fmt)
    
    # If we have separate video and audio, find best audio to pair with each video
    if video_only and audio_only:
        # Sort audio by bitrate to get best quality
        audio_only.sort(key=lambda x: x.get("abr") or x.get("tbr") or 0, reverse=True)
        best_audio = audio_only[0] if audio_only else None
        
        if best_audio:
            for vfmt in video_only:
                # Create a merged format description
                merged = vfmt.copy()
                
                # Add audio information to the format
                merged["acodec"] = best_audio.get("acodec", "aac")
                merged["abr"] = best_audio.get("abr")
                merged["audio_ext"] = best_audio.get("ext", "m4a")
                
                # Mark that this needs audio from separate URL
                merged["_audio_url"] = best_audio.get("url")
                merged["_needs_merge"] = True
                
                result.append(merged)
    
    # If no combined and no video+audio pairs, include video-only as fallback
    if not result and video_only:
        for vfmt in video_only:
            vfmt_copy = vfmt.copy()
            vfmt_copy["_video_only"] = True
            result.append(vfmt_copy)
    
    # Add audio-only formats at the end (for music downloads)
    for fmt in audio_only:
        fmt_copy = fmt.copy()
        fmt_copy["preference"] = safe_int(fmt_copy.get("preference"), 0) - 50
        result.append(fmt_copy)
    
    # Sort by quality score
    result.sort(key=get_format_quality_score, reverse=True)
    
    # Deduplicate and filter:
    # - Video formats: MUST have both video AND audio
    # - Keep only best format per resolution
    # - Keep only 1 best audio-only format (for music downloads)
    
    seen_resolutions = set()
    video_formats = []
    best_audio = None
    
    for fmt in result:
        height = fmt.get("height") or 0
        has_v = fmt.get("vcodec") and fmt.get("vcodec") != "none"
        has_a = fmt.get("acodec") and fmt.get("acodec") != "none"
        has_audio_ext = fmt.get("audio_ext")
        
        if has_v:
            # VIDEO FORMAT: Must have audio embedded!
            if has_a or has_audio_ext:
                key = f"video_{height}"
                if key not in seen_resolutions:
                    seen_resolutions.add(key)
                    video_formats.append(fmt)
            # Skip video-only formats (no audio = useless for user)
        else:
            # AUDIO-ONLY: Keep only the best one
            if has_a and best_audio is None:
                best_audio = fmt
    
    # Combine: all video formats + 1 best audio at the end
    deduplicated = video_formats
    if best_audio:
        deduplicated.append(best_audio)
    
    return deduplicated


def transform_single(data: Dict[str, Any]) -> Dict[str, Any]:
    """Transform yt-dlp output to FDM format"""
    if data.get("_type") == "playlist":
        return transform_playlist_info(data)
    
    # Get original title and create clean version
    original_title = data.get("title", "Unknown Title")
    clean_title = sanitize_filename(original_title)
    video_id = data.get("id", "")
    
    result = {
        "id": video_id,
        "title": clean_title,  # Use clean ASCII title
        "original_title": original_title,  # Keep original for display
        "webpage_url": data.get("webpage_url", data.get("url", "")),
        "duration": data.get("duration"),
        "formats": [],
        "subtitles": {},
        "thumbnails": []
    }
    
    upload_date = data.get("upload_date")
    if upload_date and len(upload_date) == 8:
        result["upload_date"] = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
    
    formats = data.get("formats", [])
    if not formats and data.get("url"):
        formats = [data]
    
    # Process and merge formats for video+audio
    processed_formats = merge_video_audio_formats(formats)
    
    for fmt in processed_formats:
        fmt_obj = transform_format(fmt, clean_title, video_id)
        if fmt_obj:
            result["formats"].append(fmt_obj)
    
    # Filter formats - prefer combined but keep all as fallback
    filtered_formats = []
    for fmt in result["formats"]:
        has_v = fmt.get("vcodec") and fmt.get("vcodec") != "none"
        has_a = fmt.get("acodec") and fmt.get("acodec") != "none"
        has_audio_ext = fmt.get("audio_ext")
        
        # Keep if: combined, audio-only, has audio info, or video-only fallback
        if (has_v and has_a) or (not has_v and has_a) or has_audio_ext or fmt.get("_video_only"):
            filtered_formats.append(fmt)
    
    # If filtering removed everything, fall back to all formats
    if filtered_formats:
        result["formats"] = filtered_formats
    
    # If still no formats, return error info
    if not result["formats"]:
        version = check_ytdlp_version()
        result["_error"] = "No downloadable formats found"
        result["_ytdlp_version"] = version
        result["_hint"] = "Try updating yt-dlp: yt-dlp -U"
    
    subtitles = data.get("subtitles", {})
    for lang, subs in subtitles.items():
        if isinstance(subs, list) and subs:
            result["subtitles"][lang] = []
            for sub in subs:
                result["subtitles"][lang].append({
                    "name": sub.get("name", lang),
                    "url": sub.get("url", ""),
                    "ext": sub.get("ext", "vtt")
                })
    
    thumbnails = data.get("thumbnails", [])
    for thumb in thumbnails:
        if thumb.get("url"):
            result["thumbnails"].append({
                "url": thumb["url"],
                "width": thumb.get("width"),
                "height": thumb.get("height"),
                "preference": safe_int(thumb.get("preference"), 0)
            })
    
    return result


def transform_format(fmt: Dict[str, Any], title: str = None, video_id: str = None) -> Optional[Dict[str, Any]]:
    """Transform a single format to FDM format"""
    url = fmt.get("url")
    if not url:
        return None
    
    protocol = fmt.get("protocol", "https")
    if protocol not in ["http", "https", "m3u8_native", "http_dash_segments"]:
        if "m3u8" in url or fmt.get("ext") == "m3u8":
            protocol = "m3u8_native"
        elif url.startswith("https"):
            protocol = "https"
        else:
            protocol = "http"
    
    ext = fmt.get("ext", "mp4")
    height = fmt.get("height")
    
    result = {
        "url": url,
        "protocol": protocol,
        "ext": ext,
        "filesize": fmt.get("filesize") or fmt.get("filesize_approx"),
        "quality": safe_int(fmt.get("quality"), 0),
        "preference": safe_int(fmt.get("preference"), 0),
        "tbr": fmt.get("tbr"),
    }
    
    # Video codec handling
    vcodec = fmt.get("vcodec", "none")
    has_v = vcodec and vcodec != "none"
    if has_v:
        result["video_ext"] = ext
        result["vcodec"] = vcodec
        result["height"] = height
        result["width"] = fmt.get("width")
        result["fps"] = fmt.get("fps")
    
    # Audio codec handling
    acodec = fmt.get("acodec", "none")
    has_a = acodec and acodec != "none"
    if has_a:
        # For combined formats, audio_ext should match the container
        # For audio-only, use the actual extension
        if has_v:
            result["audio_ext"] = ext
        else:
            result["audio_ext"] = fmt.get("audio_ext", ext)
        result["acodec"] = acodec
        result["abr"] = fmt.get("abr")
    
    # Handle formats that had audio info merged in
    if fmt.get("audio_ext") and not has_a:
        result["audio_ext"] = fmt.get("audio_ext")
        result["acodec"] = fmt.get("acodec", "aac")
        result["abr"] = fmt.get("abr")
    
    # Build format description for user display
    format_parts = []
    if has_v:
        fps = safe_int(fmt.get("fps"), 0)
        if height:
            format_parts.append(f"{height}p")
        if fps >= 60:
            format_parts.append(f"{fps}fps")
    if has_a or fmt.get("audio_ext"):
        abr = safe_int(fmt.get("abr"), 0)
        if abr > 0:
            format_parts.append(f"{abr}kbps")
    
    # Add file size to format description
    filesize = fmt.get("filesize") or fmt.get("filesize_approx")
    if filesize:
        size_str = format_filesize(filesize)
        format_parts.append(f"[{size_str}]")
    
    if format_parts:
        result["format"] = " ".join(format_parts) + f" ({ext})"
    
    # Generate clean filename for this format
    if title:
        filename_parts = [title]
        if height:
            filename_parts.append(f"{height}p")
        if video_id and len(video_id) <= 12:
            filename_parts.append(f"[{video_id}]")
        result["_filename"] = "_".join(filename_parts)
    
    if fmt.get("language"):
        result["language"] = fmt["language"]
        result["languagePreference"] = fmt.get("language_preference", 0)
    
    http_headers = fmt.get("http_headers", {})
    if http_headers:
        result["httpHeaders"] = http_headers
    
    if protocol == "http_dash_segments":
        result["container"] = f"{ext}_dash"
    
    fragments = fmt.get("fragments", [])
    if fragments:
        result["fragment_base_url"] = fmt.get("fragment_base_url", "")
        result["fragments"] = [{"path": f.get("path", f.get("url", ""))} for f in fragments]
    
    if protocol == "m3u8_native":
        result["manifestUrl"] = fmt.get("manifest_url", url)
    
    return result


def transform_playlist_info(data: Dict[str, Any]) -> Dict[str, Any]:
    """Transform playlist info to FDM format"""
    entries = []
    
    for entry in data.get("entries", []):
        if entry:
            entries.append({
                "_type": "url",
                "url": entry.get("url", entry.get("webpage_url", "")),
                "title": entry.get("title", "Unknown"),
                "duration": entry.get("duration")
            })
    
    return {
        "_type": "playlist",
        "id": data.get("id", ""),
        "title": data.get("title", "Playlist"),
        "webpage_url": data.get("webpage_url", ""),
        "entries": entries
    }


def transform_playlist(items: List[Dict[str, Any]], url: str) -> Dict[str, Any]:
    """Transform multiple items to playlist format"""
    entries = []
    title = "Playlist"
    
    for item in items:
        if item.get("_type") == "playlist":
            return transform_playlist_info(item)
        
        entries.append({
            "_type": "url",
            "url": item.get("webpage_url", item.get("url", "")),
            "title": item.get("title", "Unknown"),
            "duration": item.get("duration")
        })
        
        if not title or title == "Playlist":
            title = item.get("playlist_title", item.get("playlist", "Playlist"))
    
    return {
        "_type": "playlist",
        "title": title,
        "webpage_url": url,
        "entries": entries
    }


def analyze_url(url: str) -> Dict[str, Any]:
    """Analyze URL and determine best extraction method"""
    result = {
        "url": url,
        "is_direct": False,
        "has_ytdlp": find_ytdlp() is not None,
        "extension": get_extension_from_url(url),
        "filename": extract_filename_from_url(url)
    }
    
    if is_direct_download_url(url):
        result["is_direct"] = True
        result["category"] = get_file_category(result["extension"])
    
    return result


def extract_info(url: str, playlist: bool = False) -> Dict[str, Any]:
    """Main extraction function - handles both direct and media URLs"""
    
    # Check if it's a direct download URL
    if is_direct_download_url(url):
        return create_direct_download_result(url)
    
    # Try yt-dlp for media extraction
    return extract_with_ytdlp(url, playlist)


def main():
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Usage: croxz_bridge.py <command> <url>"}))
        sys.exit(1)
    
    command = sys.argv[1]
    url = sys.argv[2]
    
    if command == "analyze":
        result = analyze_url(url)
        print(json.dumps(result, ensure_ascii=False))
    elif command == "extract":
        result = extract_info(url, playlist=False)
        print(json.dumps(result, ensure_ascii=False))
    elif command == "playlist":
        result = extract_info(url, playlist=True)
        print(json.dumps(result, ensure_ascii=False))
    elif command == "check":
        is_direct = is_direct_download_url(url)
        has_ytdlp = find_ytdlp() is not None
        print(json.dumps({"supported": is_direct or has_ytdlp, "is_direct": is_direct}))
    else:
        print(json.dumps({"error": f"Unknown command: {command}"}))
        sys.exit(1)


if __name__ == "__main__":
    main()

