"""Media validation utility for video pipeline test data (Tasks C1.01, C1.02 — Doc 11 §3.2-3.3, Doc 08 §9)."""

from __future__ import annotations

import json
import math
import mimetypes
import subprocess
from pathlib import Path

RECOMMENDED_PART_SIZE = 50 * 1024 * 1024  # 50MB
MIN_PART_SIZE = 5 * 1024 * 1024  # 5MB
MAX_PART_SIZE = 200 * 1024 * 1024  # 200MB
MAX_TOTAL_FILE_SIZE = 5 * 1024 * 1024 * 1024  # 5GB
ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
ALLOWED_MIME_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",
    "video/x-matroska",
    "video/webm",
}


def get_ffprobe_metadata(file_path: Path) -> dict:
    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(file_path),
    ]
    result = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", check=False
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed for {file_path}: {result.stderr}")
    return json.loads(result.stdout)


def validate_video_file(file_path: Path) -> dict:
    if not file_path.exists():
        return {"file": str(file_path), "status": "FAIL", "reason": "File not found"}

    file_size = file_path.stat().st_size
    extension = file_path.suffix.lower()
    guessed_mime, _ = mimetypes.guess_type(str(file_path))
    if not guessed_mime and extension == ".mp4":
        guessed_mime = "video/mp4"

    # Size check
    size_ok = 0 < file_size <= MAX_TOTAL_FILE_SIZE
    ext_ok = extension in ALLOWED_EXTENSIONS
    mime_ok = guessed_mime in ALLOWED_MIME_TYPES

    # Multipart calculation
    total_parts = math.ceil(file_size / RECOMMENDED_PART_SIZE)
    parts_info = []
    remaining = file_size
    for i in range(1, total_parts + 1):
        p_size = min(remaining, RECOMMENDED_PART_SIZE)
        parts_info.append({"part_number": i, "size_bytes": p_size, "size_mb": round(p_size / (1024 * 1024), 2)})
        remaining -= p_size

    # FFprobe stream inspection
    probe_data = get_ffprobe_metadata(file_path)
    fmt = probe_data.get("format", {})
    streams = probe_data.get("streams", [])

    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

    has_video = len(video_streams) > 0
    has_audio = len(audio_streams) > 0

    v_stream = video_streams[0] if has_video else {}
    a_stream = audio_streams[0] if has_audio else {}

    duration = float(fmt.get("duration", 0.0))

    report = {
        "file_name": file_path.name,
        "file_size_bytes": file_size,
        "file_size_mb": round(file_size / (1024 * 1024), 2),
        "extension": extension,
        "mime_type": guessed_mime,
        "duration_seconds": duration,
        "bit_rate_kbps": round(float(fmt.get("bit_rate", 0)) / 1000, 2),
        "video_codec": v_stream.get("codec_name"),
        "resolution": f"{v_stream.get('width')}x{v_stream.get('height')}" if has_video else None,
        "fps": v_stream.get("r_frame_rate"),
        "audio_codec": a_stream.get("codec_name") if has_audio else None,
        "audio_channels": a_stream.get("channels") if has_audio else None,
        "audio_sample_rate": a_stream.get("sample_rate") if has_audio else None,
        "validation_checks": {
            "size_under_5gb": size_ok,
            "allowed_extension": ext_ok,
            "allowed_mime_type": mime_ok,
            "has_video_stream": has_video,
            "has_audio_stream": has_audio,
        },
        "multipart_planning": {
            "part_size_bytes": RECOMMENDED_PART_SIZE,
            "part_size_mb": 50,
            "total_parts": total_parts,
            "parts": parts_info,
        },
        "all_checks_passed": size_ok and ext_ok and mime_ok and has_video and has_audio,
    }
    return report


def main() -> None:
    media_dir = Path("media")
    if not media_dir.exists():
        print("Media directory does not exist.")
        return

    files = [f for f in media_dir.iterdir() if f.is_file() and f.suffix.lower() in ALLOWED_EXTENSIONS]
    print(f"Found {len(files)} video files in media/:")
    for f in sorted(files):
        print(f"--- Analyzing: {f.name} ---")
        report = validate_video_file(f)
        print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
