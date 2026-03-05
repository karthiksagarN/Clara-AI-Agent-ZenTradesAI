"""
Whisper-based local audio transcription.
Zero-cost, runs locally using OpenAI's Whisper model.
"""

import sys
import argparse
from pathlib import Path

from utils import setup_logging, save_text, WHISPER_MODEL

logger = setup_logging("transcribe")


def transcribe_audio(audio_path: Path, model_name: str = None) -> str:
    """
    Transcribe an audio file using Whisper locally.

    Args:
        audio_path: Path to audio file (.m4a, .mp3, .wav, etc.)
        model_name: Whisper model size (tiny, base, small, medium, large)

    Returns:
        Transcribed text string
    """
    try:
        import whisper
    except ImportError:
        logger.error("Whisper not installed. Run: pip install openai-whisper")
        raise

    model_name = model_name or WHISPER_MODEL
    logger.info(f"Loading Whisper model: {model_name}")
    model = whisper.load_model(model_name)

    logger.info(f"Transcribing: {audio_path}")
    result = model.transcribe(
        str(audio_path),
        language="en",
        verbose=False
    )

    text = result["text"].strip()
    logger.info(f"Transcription complete: {len(text)} characters")
    return text


def transcribe_and_save(audio_path: Path, output_path: Path, model_name: str = None) -> str:
    """Transcribe audio and save to file."""
    text = transcribe_audio(audio_path, model_name)
    save_text(text, output_path)
    return text


def main():
    parser = argparse.ArgumentParser(description="Transcribe audio files using Whisper")
    parser.add_argument("audio_path", type=str, help="Path to audio file")
    parser.add_argument("--output", "-o", type=str, help="Output transcript path")
    parser.add_argument("--model", "-m", type=str, default=None,
                        help=f"Whisper model (default: {WHISPER_MODEL})")

    args = parser.parse_args()
    audio_path = Path(args.audio_path)

    if not audio_path.exists():
        logger.error(f"Audio file not found: {audio_path}")
        sys.exit(1)

    output_path = Path(args.output) if args.output else audio_path.with_suffix(".txt")

    transcript = transcribe_and_save(audio_path, output_path, args.model)
    print(f"\nTranscription saved to: {output_path}")
    print(f"Length: {len(transcript)} characters")


if __name__ == "__main__":
    main()
