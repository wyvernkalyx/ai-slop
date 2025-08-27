"""Video assembly module - wrapper for FFmpeg assembler."""

from .assemble_ffmpeg import VideoAssembler, FFmpegVideoAssembler

# Export both for compatibility
__all__ = ['VideoAssembler', 'FFmpegVideoAssembler']