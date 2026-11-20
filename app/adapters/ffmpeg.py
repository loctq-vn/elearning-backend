"""FFmpeg and ffprobe adapter for video inspection, HLS transcoding, and audio extraction (Spec 11 §4)."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


class FFmpegError(RuntimeError):
    """Raised when an external ffmpeg or ffprobe process fails."""


@dataclass(slots=True)
class VideoProbeResult:
    """Media container and stream properties extracted via ffprobe."""

    duration_seconds: float
    width: int
    height: int
    fps: float
    video_codec: str
    audio_codec: str | None
    audio_sample_rate: int | None
    audio_channels: int | None
    file_size_bytes: int


@dataclass(slots=True)
class HlsRendition:
    """Specification of an HLS rendition (Spec 11 §4.1.1)."""

    name: str  # e.g. "1080p", "720p", "480p"
    width: int
    height: int
    video_bitrate_kbps: int
    maxrate_kbps: int
    bufsize_kbps: int
    profile: str
    bandwidth: int  # in bps for master.m3u8


# Standard 3 renditions defined in Spec 11 §4.1.1
STANDARD_RENDITIONS: list[HlsRendition] = [
    HlsRendition(
        name="1080p",
        width=1920,
        height=1080,
        video_bitrate_kbps=4500,
        maxrate_kbps=4800,
        bufsize_kbps=9000,
        profile="high",
        bandwidth=4628000,
    ),
    HlsRendition(
        name="720p",
        width=1280,
        height=720,
        video_bitrate_kbps=2500,
        maxrate_kbps=2700,
        bufsize_kbps=5000,
        profile="main",
        bandwidth=2628000,
    ),
    HlsRendition(
        name="480p",
        width=854,
        height=480,
        video_bitrate_kbps=1200,
        maxrate_kbps=1300,
        bufsize_kbps=2400,
        profile="main",
        bandwidth=1328000,
    ),
]


class FFmpegAdapter:
    """Executes local ffmpeg/ffprobe binary operations."""

    def __init__(
        self,
        ffmpeg_bin: str = "ffmpeg",
        ffprobe_bin: str = "ffprobe",
    ) -> None:
        self.ffmpeg_bin = ffmpeg_bin
        self.ffprobe_bin = ffprobe_bin

    def check_installed(self) -> bool:
        """Verify ffmpeg and ffprobe are available in the execution PATH."""
        return bool(shutil.which(self.ffmpeg_bin) and shutil.which(self.ffprobe_bin))

    def probe(self, input_path: str | Path) -> VideoProbeResult:
        """Inspect media file properties using ffprobe."""
        input_file = Path(input_path)
        if not input_file.is_file():
            raise FFmpegError(f"File not found: '{input_path}'")

        cmd = [
            self.ffprobe_bin,
            "-v",
            "error",
            "-show_entries",
            "format=duration,size:stream=index,codec_type,codec_name,width,height,r_frame_rate,avg_frame_rate,sample_rate,channels",
            "-of",
            "json",
            str(input_file),
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
        except subprocess.CalledProcessError as exc:
            raise FFmpegError(f"ffprobe execution failed: {exc.stderr}") from exc
        except (json.JSONDecodeError, KeyError) as exc:
            raise FFmpegError(f"Unable to parse ffprobe output: {exc}") from exc

        format_info = data.get("format", {})
        streams = data.get("streams", [])

        duration = float(format_info.get("duration", 0.0))
        file_size = int(format_info.get("size", input_file.stat().st_size))

        video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

        if not video_stream:
            raise FFmpegError("No video stream found in media file")

        width = int(video_stream.get("width", 0))
        height = int(video_stream.get("height", 0))
        video_codec = str(video_stream.get("codec_name", "unknown"))

        # Parse frame rate
        fps_str = video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate") or "24/1"
        try:
            if "/" in fps_str:
                num, den = fps_str.split("/")
                fps = float(num) / float(den) if float(den) != 0 else 24.0
            else:
                fps = float(fps_str)
        except (ValueError, ZeroDivisionError):
            fps = 24.0

        audio_codec = audio_stream.get("codec_name") if audio_stream else None
        audio_sample_rate = (
            int(audio_stream.get("sample_rate"))
            if audio_stream and audio_stream.get("sample_rate")
            else None
        )
        audio_channels = (
            int(audio_stream.get("channels"))
            if audio_stream and audio_stream.get("channels")
            else None
        )

        return VideoProbeResult(
            duration_seconds=duration,
            width=width,
            height=height,
            fps=fps,
            video_codec=video_codec,
            audio_codec=audio_codec,
            audio_sample_rate=audio_sample_rate,
            audio_channels=audio_channels,
            file_size_bytes=file_size,
        )

    def transcode_to_hls(
        self,
        input_path: str | Path,
        output_dir: str | Path,
        probe_info: VideoProbeResult | None = None,
        progress_callback: Callable[[float], None] | None = None,
    ) -> list[str]:
        """Transcode input video to multi-rendition HLS (Spec 11 §4.1).

        Generates renditions (1080p, 720p, 480p) and master.m3u8 playlist.
        Returns list of generated file names relative to output_dir.
        """
        input_file = Path(input_path)
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        if probe_info is None:
            probe_info = self.probe(input_file)

        # Keyframe interval fixed 2 seconds: -g 2*fps, -keyint_min 2*fps, -sc_threshold 0
        g_val = max(1, round(2.0 * probe_info.fps))

        # Filter target renditions so we don't unnecessarily upscale low-res video
        applicable_renditions = [
            r for r in STANDARD_RENDITIONS if probe_info.height >= r.height or r.name == "480p"
        ]
        if not applicable_renditions:
            applicable_renditions = [STANDARD_RENDITIONS[-1]]  # At least 480p

        total_steps = len(applicable_renditions)
        generated_files: list[str] = []

        for idx, rendition in enumerate(applicable_renditions):
            playlist_name = f"{rendition.name}.m3u8"
            segment_pattern = str(out_path / f"{rendition.name}_%03d.ts")
            playlist_path = str(out_path / playlist_name)

            # Ensure aspect ratio preserves and pads if needed
            scale_filter = (
                f"scale=w={rendition.width}:h={rendition.height}:force_original_aspect_ratio=decrease,"
                f"pad={rendition.width}:{rendition.height}:(ow-iw)/2:(oh-ih)/2"
            )

            cmd = [
                self.ffmpeg_bin,
                "-y",
                "-i",
                str(input_file),
                "-vf",
                scale_filter,
                "-c:v",
                "libx264",
                "-profile:v",
                rendition.profile,
                "-b:v",
                f"{rendition.video_bitrate_kbps}k",
                "-maxrate",
                f"{rendition.maxrate_kbps}k",
                "-bufsize",
                f"{rendition.bufsize_kbps}k",
                "-g",
                str(g_val),
                "-keyint_min",
                str(g_val),
                "-sc_threshold",
                "0",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                "-ar",
                "48000",
                "-ac",
                "2",
                "-hls_time",
                "6",
                "-hls_playlist_type",
                "vod",
                "-hls_segment_filename",
                segment_pattern,
                playlist_path,
            ]

            logger.info("Transcoding %s rendition: %s", rendition.name, " ".join(cmd[:10]))
            try:
                subprocess.run(cmd, capture_output=True, text=True, check=True)
            except subprocess.CalledProcessError as exc:
                raise FFmpegError(
                    f"FFmpeg failed while transcoding {rendition.name}: {exc.stderr}"
                ) from exc

            generated_files.append(playlist_name)
            if progress_callback:
                # e.g., 1/3 -> 33%, 2/3 -> 66%, 3/3 -> 100%
                percent = round(((idx + 1) / total_steps) * 100.0, 1)
                progress_callback(percent)

        # Generate master.m3u8
        master_content = ["#EXTM3U", "#EXT-X-VERSION:3"]
        for rendition in applicable_renditions:
            master_content.append(
                f"#EXT-X-STREAM-INF:BANDWIDTH={rendition.bandwidth},"
                f"RESOLUTION={rendition.width}x{rendition.height}"
            )
            master_content.append(f"{rendition.name}.m3u8")

        master_path = out_path / "master.m3u8"
        master_path.write_text("\n".join(master_content) + "\n", encoding="utf-8")
        generated_files.append("master.m3u8")

        # Collect all generated segment files
        for ts_file in out_path.glob("*.ts"):
            generated_files.append(ts_file.name)

        return sorted(set(generated_files))

    def extract_audio_for_whisper(
        self,
        input_path: str | Path,
        output_wav_path: str | Path,
    ) -> Path:
        """Extract audio to mono 16kHz WAV format for Whisper (Spec 11 §4.2)."""
        input_file = Path(input_path)
        output_wav = Path(output_wav_path)
        output_wav.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            self.ffmpeg_bin,
            "-y",
            "-i",
            str(input_file),
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ac",
            "1",
            "-ar",
            "16000",
            str(output_wav),
        ]

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as exc:
            raise FFmpegError(f"FFmpeg failed extracting audio: {exc.stderr}") from exc

        return output_wav
