#!/usr/bin/env python3
"""
Local Audiobook Generator for Apple Silicon

This script generates audiobooks using local LLMs running on Apple Silicon (M1/M2/M3).
It supports multiple backends for both text generation and text-to-speech.

Features:
- Local LLM text generation (MLX, llama.cpp, Ollama)
- Text-to-speech using local models or macOS built-in voices
- Chapter-based audiobook creation
- Multiple output formats (MP3, M4B, WAV)
- Support for custom prompts and story generation

Requirements:
    pip install -r local_audiobook_requirements.txt

    For MLX (Apple Silicon native):
    pip install mlx-lm

    For llama.cpp:
    pip install llama-cpp-python

    For Ollama:
    curl -fsSL https://ollama.com/install.sh | sh

Usage:
    # Generate audiobook from prompt:
    python local_audiobook_generator.py --prompt "A mystery story about a detective cat" --chapters 5

    # Convert existing text to audiobook:
    python local_audiobook_generator.py --input story.txt --output my_audiobook.mp3

    # Use specific model:
    python local_audiobook_generator.py --model mlx-community/Mistral-7B-Instruct-v0.2-4bit --prompt "Sci-fi adventure"
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple
import re

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    print("Warning: pydub not installed. Install with: pip install pydub")


@dataclass
class AudiobookConfig:
    """Configuration for audiobook generation."""
    model_backend: str = "ollama"  # ollama, mlx, llamacpp
    model_name: str = "llama3.2:3b"
    tts_backend: str = "macos"  # macos, piper, bark
    voice: str = "Samantha"  # macOS voice name
    output_format: str = "mp3"
    chapters: int = 3
    words_per_chapter: int = 1000
    temperature: float = 0.7
    add_chapter_titles: bool = True


class LocalLLMGenerator:
    """Generate text using local LLMs on Apple Silicon."""

    def __init__(self, backend: str = "ollama", model_name: str = "llama3.2:3b"):
        """Initialize the LLM generator.

        Args:
            backend: Backend to use (ollama, mlx, llamacpp)
            model_name: Model identifier
        """
        self.backend = backend
        self.model_name = model_name
        self._validate_backend()

    def _validate_backend(self):
        """Validate that the selected backend is available."""
        if self.backend == "ollama":
            try:
                subprocess.run(["ollama", "--version"],
                             capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("Error: Ollama not found. Install from https://ollama.com")
                sys.exit(1)

        elif self.backend == "mlx":
            try:
                import mlx_lm
            except ImportError:
                print("Error: MLX not installed. Install with: pip install mlx-lm")
                sys.exit(1)

        elif self.backend == "llamacpp":
            try:
                import llama_cpp
            except ImportError:
                print("Error: llama-cpp-python not installed.")
                print("Install with: pip install llama-cpp-python")
                sys.exit(1)

    def generate_with_ollama(self, prompt: str, max_tokens: int = 1000,
                           temperature: float = 0.7) -> str:
        """Generate text using Ollama.

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            Generated text
        """
        cmd = [
            "ollama", "run", self.model_name,
            prompt
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            print("Warning: Generation timed out")
            return ""
        except Exception as e:
            print(f"Error generating with Ollama: {e}")
            return ""

    def generate_with_mlx(self, prompt: str, max_tokens: int = 1000,
                         temperature: float = 0.7) -> str:
        """Generate text using MLX.

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            Generated text
        """
        try:
            from mlx_lm import load, generate

            # Load model
            model, tokenizer = load(self.model_name)

            # Generate
            output = generate(
                model,
                tokenizer,
                prompt=prompt,
                max_tokens=max_tokens,
                temp=temperature
            )

            return output
        except Exception as e:
            print(f"Error generating with MLX: {e}")
            return ""

    def generate_with_llamacpp(self, prompt: str, max_tokens: int = 1000,
                              temperature: float = 0.7) -> str:
        """Generate text using llama.cpp.

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            Generated text
        """
        try:
            from llama_cpp import Llama

            # Initialize model
            llm = Llama(
                model_path=self.model_name,
                n_ctx=2048,
                n_threads=8,
                n_gpu_layers=-1  # Use Metal on Apple Silicon
            )

            # Generate
            output = llm(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                echo=False
            )

            return output['choices'][0]['text']
        except Exception as e:
            print(f"Error generating with llama.cpp: {e}")
            return ""

    def generate(self, prompt: str, max_tokens: int = 1000,
                temperature: float = 0.7) -> str:
        """Generate text using the configured backend.

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            Generated text
        """
        print(f"Generating with {self.backend} ({self.model_name})...")

        if self.backend == "ollama":
            return self.generate_with_ollama(prompt, max_tokens, temperature)
        elif self.backend == "mlx":
            return self.generate_with_mlx(prompt, max_tokens, temperature)
        elif self.backend == "llamacpp":
            return self.generate_with_llamacpp(prompt, max_tokens, temperature)
        else:
            raise ValueError(f"Unknown backend: {self.backend}")


class LocalTTSGenerator:
    """Generate speech from text using local TTS."""

    def __init__(self, backend: str = "macos", voice: str = "Samantha"):
        """Initialize TTS generator.

        Args:
            backend: TTS backend (macos, piper, bark)
            voice: Voice identifier
        """
        self.backend = backend
        self.voice = voice

    def generate_with_macos(self, text: str, output_file: str,
                           rate: int = 200) -> bool:
        """Generate speech using macOS built-in TTS.

        Args:
            text: Text to speak
            output_file: Output audio file path
            rate: Speech rate (words per minute)

        Returns:
            True if successful
        """
        try:
            # Use macOS 'say' command
            cmd = [
                "say",
                "-v", self.voice,
                "-r", str(rate),
                "-o", output_file,
                "--data-format=LEF32@22050",
                text
            ]

            subprocess.run(cmd, check=True, capture_output=True)

            # Convert to desired format if needed
            if not output_file.endswith('.aiff'):
                self._convert_audio(output_file, output_file.replace('.aiff', '.wav'))

            return True
        except subprocess.CalledProcessError as e:
            print(f"Error with macOS TTS: {e}")
            return False

    def generate_with_piper(self, text: str, output_file: str) -> bool:
        """Generate speech using Piper TTS.

        Args:
            text: Text to speak
            output_file: Output audio file path

        Returns:
            True if successful
        """
        try:
            # Piper command line
            cmd = [
                "piper",
                "--model", self.voice,
                "--output_file", output_file
            ]

            result = subprocess.run(
                cmd,
                input=text,
                text=True,
                capture_output=True,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Error: Piper not found or failed")
            return False

    def _convert_audio(self, input_file: str, output_file: str):
        """Convert audio file format using ffmpeg."""
        try:
            cmd = [
                "ffmpeg", "-i", input_file,
                "-y",  # Overwrite
                output_file
            ]
            subprocess.run(cmd, check=True, capture_output=True)

            # Remove original if conversion successful
            if os.path.exists(output_file):
                os.remove(input_file)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Warning: ffmpeg not available for conversion")

    def generate(self, text: str, output_file: str) -> bool:
        """Generate speech using configured backend.

        Args:
            text: Text to speak
            output_file: Output audio file path

        Returns:
            True if successful
        """
        if self.backend == "macos":
            return self.generate_with_macos(text, output_file)
        elif self.backend == "piper":
            return self.generate_with_piper(text, output_file)
        else:
            raise ValueError(f"Unknown TTS backend: {self.backend}")


class AudiobookGenerator:
    """Main audiobook generator orchestrator."""

    def __init__(self, config: AudiobookConfig):
        """Initialize audiobook generator.

        Args:
            config: Audiobook configuration
        """
        self.config = config
        self.llm = LocalLLMGenerator(config.model_backend, config.model_name)
        self.tts = LocalTTSGenerator(config.tts_backend, config.voice)

    def generate_story(self, prompt: str) -> List[Tuple[str, str]]:
        """Generate a multi-chapter story.

        Args:
            prompt: Story prompt

        Returns:
            List of (chapter_title, chapter_text) tuples
        """
        chapters = []

        print(f"\nGenerating {self.config.chapters} chapters...")

        for i in range(self.config.chapters):
            chapter_num = i + 1
            print(f"\nChapter {chapter_num}/{self.config.chapters}...")

            # Create chapter prompt
            if i == 0:
                chapter_prompt = f"""Write Chapter 1 of a story based on this premise: {prompt}

Write approximately {self.config.words_per_chapter} words for this chapter.
Start with 'Chapter 1: [Title]' and then write the chapter content.
Make it engaging and end with a hook for the next chapter."""
            elif i == self.config.chapters - 1:
                chapter_prompt = f"""Continue the story. Write the final chapter (Chapter {chapter_num}).

Previous context: {chapters[-1][1][-500:] if chapters else ''}

Write approximately {self.config.words_per_chapter} words.
Start with 'Chapter {chapter_num}: [Title]' and conclude the story satisfyingly."""
            else:
                chapter_prompt = f"""Continue the story. Write Chapter {chapter_num}.

Previous context: {chapters[-1][1][-500:] if chapters else ''}

Write approximately {self.config.words_per_chapter} words.
Start with 'Chapter {chapter_num}: [Title]' and continue the narrative."""

            # Generate chapter
            chapter_text = self.llm.generate(
                chapter_prompt,
                max_tokens=int(self.config.words_per_chapter * 1.5),
                temperature=self.config.temperature
            )

            if not chapter_text:
                print(f"Warning: Failed to generate chapter {chapter_num}")
                continue

            # Extract title
            title_match = re.search(r'Chapter \d+:\s*(.+?)(?:\n|$)', chapter_text)
            if title_match:
                title = title_match.group(1).strip()
            else:
                title = f"Chapter {chapter_num}"

            chapters.append((title, chapter_text))
            print(f"✓ Generated: {title} ({len(chapter_text)} chars)")

        return chapters

    def text_to_speech(self, chapters: List[Tuple[str, str]],
                       output_dir: Path) -> List[str]:
        """Convert chapters to speech.

        Args:
            chapters: List of (title, text) tuples
            output_dir: Directory for audio files

        Returns:
            List of audio file paths
        """
        audio_files = []

        print(f"\nConverting to speech using {self.config.tts_backend}...")

        for i, (title, text) in enumerate(chapters, 1):
            print(f"\nChapter {i}/{len(chapters)}: {title}")

            # Create temp file
            audio_file = output_dir / f"chapter_{i:02d}.aiff"

            # Add chapter announcement if enabled
            if self.config.add_chapter_titles:
                full_text = f"Chapter {i}. {title}.\n\n{text}"
            else:
                full_text = text

            # Generate speech
            success = self.tts.generate(full_text, str(audio_file))

            if success and audio_file.exists():
                audio_files.append(str(audio_file))
                print(f"✓ Generated audio: {audio_file.name}")
            else:
                print(f"✗ Failed to generate audio for chapter {i}")

        return audio_files

    def combine_audio_files(self, audio_files: List[str],
                           output_file: str) -> bool:
        """Combine multiple audio files into one.

        Args:
            audio_files: List of audio file paths
            output_file: Output file path

        Returns:
            True if successful
        """
        if not PYDUB_AVAILABLE:
            print("Warning: pydub not available. Trying ffmpeg...")
            return self._combine_with_ffmpeg(audio_files, output_file)

        try:
            print(f"\nCombining {len(audio_files)} audio files...")

            # Load and combine
            combined = AudioSegment.empty()
            for audio_file in audio_files:
                segment = AudioSegment.from_file(audio_file)
                combined += segment
                # Add 1 second pause between chapters
                combined += AudioSegment.silent(duration=1000)

            # Export
            file_format = self.config.output_format
            combined.export(output_file, format=file_format)

            print(f"✓ Audiobook saved: {output_file}")
            return True

        except Exception as e:
            print(f"Error combining audio: {e}")
            return self._combine_with_ffmpeg(audio_files, output_file)

    def _combine_with_ffmpeg(self, audio_files: List[str],
                            output_file: str) -> bool:
        """Combine audio files using ffmpeg."""
        try:
            # Create concat file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt',
                                            delete=False) as f:
                concat_file = f.name
                for audio_file in audio_files:
                    f.write(f"file '{os.path.abspath(audio_file)}'\n")

            # Run ffmpeg
            cmd = [
                "ffmpeg", "-f", "concat", "-safe", "0",
                "-i", concat_file,
                "-y", output_file
            ]

            subprocess.run(cmd, check=True, capture_output=True)
            os.unlink(concat_file)

            print(f"✓ Audiobook saved: {output_file}")
            return True

        except Exception as e:
            print(f"Error combining with ffmpeg: {e}")
            return False

    def generate_audiobook(self, prompt: Optional[str] = None,
                          input_file: Optional[str] = None,
                          output_file: str = "audiobook.mp3") -> bool:
        """Generate complete audiobook.

        Args:
            prompt: Story prompt (for generation)
            input_file: Input text file (for conversion)
            output_file: Output audio file path

        Returns:
            True if successful
        """
        # Create temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Generate or load content
            if prompt:
                chapters = self.generate_story(prompt)

                # Save text version
                text_file = output_file.replace('.mp3', '.txt').replace('.m4b', '.txt')
                with open(text_file, 'w', encoding='utf-8') as f:
                    for title, text in chapters:
                        f.write(f"\n{'='*80}\n")
                        f.write(f"{title}\n")
                        f.write(f"{'='*80}\n\n")
                        f.write(f"{text}\n\n")
                print(f"✓ Text saved: {text_file}")

            elif input_file:
                # Load from file
                with open(input_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Split into chapters (simple split by Chapter markers or paragraphs)
                chapter_pattern = r'(?:Chapter \d+[:\.]?\s*(.+?)(?:\n|$))'
                parts = re.split(chapter_pattern, content)

                chapters = []
                for i in range(1, len(parts), 2):
                    if i < len(parts):
                        title = parts[i].strip() if i < len(parts) else f"Part {i//2 + 1}"
                        text = parts[i+1] if i+1 < len(parts) else parts[i]
                        chapters.append((title, text))

                if not chapters:
                    # No chapter markers, treat as single chapter
                    chapters = [("Full Text", content)]
            else:
                print("Error: Must provide either --prompt or --input")
                return False

            if not chapters:
                print("Error: No content generated")
                return False

            # Convert to speech
            audio_files = self.text_to_speech(chapters, temp_path)

            if not audio_files:
                print("Error: No audio files generated")
                return False

            # Combine into audiobook
            return self.combine_audio_files(audio_files, output_file)


def list_macos_voices():
    """List available macOS voices."""
    try:
        result = subprocess.run(
            ["say", "-v", "?"],
            capture_output=True,
            text=True,
            check=True
        )
        print("\nAvailable macOS voices:")
        print(result.stdout)
    except Exception as e:
        print(f"Error listing voices: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate audiobooks using local LLMs on Apple Silicon",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate a mystery audiobook:
  python local_audiobook_generator.py --prompt "A detective cat solves crimes" --chapters 5

  # Convert existing text to audiobook:
  python local_audiobook_generator.py --input my_story.txt --output my_audiobook.mp3

  # Use specific model and voice:
  python local_audiobook_generator.py --model llama3.2:3b --voice "Alex" --prompt "Sci-fi adventure"

  # List available voices:
  python local_audiobook_generator.py --list-voices
        """
    )

    parser.add_argument('--prompt', '-p', help='Story prompt for generation')
    parser.add_argument('--input', '-i', help='Input text file to convert')
    parser.add_argument('--output', '-o', default='audiobook.mp3',
                       help='Output audio file (default: audiobook.mp3)')

    parser.add_argument('--model-backend', default='ollama',
                       choices=['ollama', 'mlx', 'llamacpp'],
                       help='LLM backend (default: ollama)')
    parser.add_argument('--model', '-m', default='llama3.2:3b',
                       help='Model name/path (default: llama3.2:3b for Ollama)')

    parser.add_argument('--tts-backend', default='macos',
                       choices=['macos', 'piper'],
                       help='TTS backend (default: macos)')
    parser.add_argument('--voice', '-v', default='Samantha',
                       help='Voice name (default: Samantha for macOS)')

    parser.add_argument('--chapters', '-c', type=int, default=3,
                       help='Number of chapters to generate (default: 3)')
    parser.add_argument('--words-per-chapter', type=int, default=1000,
                       help='Target words per chapter (default: 1000)')
    parser.add_argument('--temperature', '-t', type=float, default=0.7,
                       help='Generation temperature (default: 0.7)')

    parser.add_argument('--format', '-f', default='mp3',
                       choices=['mp3', 'm4b', 'wav'],
                       help='Output audio format (default: mp3)')
    parser.add_argument('--no-chapter-titles', action='store_true',
                       help='Don\'t announce chapter titles in audio')

    parser.add_argument('--list-voices', action='store_true',
                       help='List available macOS voices and exit')

    args = parser.parse_args()

    if args.list_voices:
        list_macos_voices()
        return

    if not args.prompt and not args.input:
        parser.print_help()
        print("\nError: Must provide either --prompt or --input")
        return

    # Create config
    config = AudiobookConfig(
        model_backend=args.model_backend,
        model_name=args.model,
        tts_backend=args.tts_backend,
        voice=args.voice,
        output_format=args.format,
        chapters=args.chapters,
        words_per_chapter=args.words_per_chapter,
        temperature=args.temperature,
        add_chapter_titles=not args.no_chapter_titles
    )

    # Generate audiobook
    generator = AudiobookGenerator(config)

    success = generator.generate_audiobook(
        prompt=args.prompt,
        input_file=args.input,
        output_file=args.output
    )

    if success:
        print("\n" + "="*80)
        print("✓ Audiobook generation complete!")
        print("="*80)
    else:
        print("\n✗ Audiobook generation failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
