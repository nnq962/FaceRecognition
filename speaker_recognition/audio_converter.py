"""
Audio Converter Module - Production-ready audio processing utility
Converts various audio formats to 16kHz mono WAV files

Author: Audio Processing Team
Version: 1.0.0
"""

import sys
import argparse
from pathlib import Path
from typing import Optional, List, Dict, Union
from dataclasses import dataclass

try:
    from pydub import AudioSegment
    from pydub.utils import which
except ImportError as e:
    raise ImportError("pydub is required. Install with: pip install pydub") from e

try:
    from utils.logger_config import LOGGER
except ImportError:
    import logging
    LOGGER = logging.getLogger(__name__)
    LOGGER.warning("Could not import logger from utils.logger_config. Using default logger.")


@dataclass
class AudioInfo:
    """Data class for audio file information"""
    file_path: Path
    original_format: str
    original_sample_rate: int
    original_channels: int
    duration_seconds: float
    file_size_mb: float


@dataclass
class ConversionResult:
    """Data class for conversion results"""
    success: bool
    input_path: Path
    output_path: Optional[Path] = None
    audio_info: Optional[AudioInfo] = None
    error_message: Optional[str] = None
    processing_time_seconds: Optional[float] = None


class AudioConverterError(Exception):
    """Custom exception for audio converter errors"""
    pass


class AudioConverter:
    """
    Professional audio converter for processing audio files to 16kHz mono WAV format.
    
    Supports multiple input formats: MP3, FLAC, OGG, M4A, AAC, WMA, WAV, AIFF, AU
    """
    
    SUPPORTED_FORMATS = {'.mp3', '.flac', '.ogg', '.m4a', '.aac', '.wma', '.wav', '.aiff', '.au'}
    TARGET_SAMPLE_RATE = 16000
    TARGET_CHANNELS = 1
    
    def __init__(self, check_dependencies: bool = True):
        """
        Initialize AudioConverter
        
        Args:
            check_dependencies: Whether to check for required dependencies on init
        """
        self.conversion_stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0
        }
        
        if check_dependencies:
            self._check_dependencies()
    
    def _check_dependencies(self) -> None:
        """Check for required system dependencies"""
        if not which("ffmpeg"):
            LOGGER.warning(
                "ffmpeg not found. Some audio formats may not be supported. "
                "Install ffmpeg: https://ffmpeg.org/download.html"
            )
    
    def _get_audio_info(self, audio: AudioSegment, file_path: Path) -> AudioInfo:
        """Extract audio file information"""
        return AudioInfo(
            file_path=file_path,
            original_format=file_path.suffix.lower(),
            original_sample_rate=audio.frame_rate,
            original_channels=audio.channels,
            duration_seconds=len(audio) / 1000.0,
            file_size_mb=file_path.stat().st_size / (1024 * 1024)
        )
    
    def _load_audio_file(self, file_path: Path) -> AudioSegment:
        """
        Load audio file using appropriate pydub method
        
        Args:
            file_path: Path to audio file
            
        Returns:
            AudioSegment object
            
        Raises:
            AudioConverterError: If file cannot be loaded
        """
        try:
            suffix = file_path.suffix.lower()
            
            if suffix == '.mp3':
                return AudioSegment.from_mp3(str(file_path))
            elif suffix == '.flac':
                return AudioSegment.from_flac(str(file_path))
            elif suffix == '.ogg':
                return AudioSegment.from_ogg(str(file_path))
            elif suffix in ['.m4a', '.aac']:
                return AudioSegment.from_file(str(file_path), format="m4a")
            elif suffix == '.wma':
                return AudioSegment.from_file(str(file_path), format="wma")
            else:
                return AudioSegment.from_file(str(file_path))
                
        except Exception as e:
            raise AudioConverterError(f"Failed to load audio file {file_path}: {str(e)}") from e
    
    def _process_audio(self, audio: AudioSegment) -> AudioSegment:
        """
        Process audio to target specifications (16kHz mono)
        
        Args:
            audio: Input AudioSegment
            
        Returns:
            Processed AudioSegment
        """
        processed_audio = audio
        
        # Convert to mono if needed
        if processed_audio.channels > 1:
            processed_audio = processed_audio.set_channels(self.TARGET_CHANNELS)
            LOGGER.debug("Converted to mono")
        
        # Convert sample rate if needed
        if processed_audio.frame_rate != self.TARGET_SAMPLE_RATE:
            processed_audio = processed_audio.set_frame_rate(self.TARGET_SAMPLE_RATE)
            LOGGER.debug(f"Converted sample rate to {self.TARGET_SAMPLE_RATE} Hz")
        
        return processed_audio
    
    def convert_single_file(
        self, 
        input_path: Union[str, Path], 
        output_path: Optional[Union[str, Path]] = None
    ) -> ConversionResult:
        """
        Convert a single audio file to 16kHz mono WAV
        
        Args:
            input_path: Path to input audio file
            output_path: Path for output file (optional)
            
        Returns:
            ConversionResult object with processing details
        """
        import time
        start_time = time.time()
        
        input_path = Path(input_path)
        
        try:
            # Validate input file
            if not input_path.exists():
                raise AudioConverterError(f"Input file does not exist: {input_path}")
            
            if input_path.suffix.lower() not in self.SUPPORTED_FORMATS:
                raise AudioConverterError(
                    f"Unsupported format: {input_path.suffix}. "
                    f"Supported formats: {', '.join(sorted(self.SUPPORTED_FORMATS))}"
                )
            
            # Generate output path if not provided
            if output_path is None:
                output_path = input_path.parent / f"{input_path.stem}_16khz_mono.wav"
            else:
                output_path = Path(output_path)
            
            LOGGER.info(f"Processing: {input_path.name}")
            
            # Load and process audio
            audio = self._load_audio_file(input_path)
            audio_info = self._get_audio_info(audio, input_path)
            
            LOGGER.info(
                f"Input specs - Format: {audio_info.original_format}, "
                f"Sample Rate: {audio_info.original_sample_rate} Hz, "
                f"Channels: {audio_info.original_channels}, "
                f"Duration: {audio_info.duration_seconds:.2f}s"
            )
            
            # Process audio
            processed_audio = self._process_audio(audio)
            
            # Export to WAV
            processed_audio.export(str(output_path), format="wav")
            
            processing_time = time.time() - start_time
            output_size_mb = output_path.stat().st_size / (1024 * 1024)
            
            LOGGER.info(
                f"Successfully converted: {output_path.name} "
                f"({output_size_mb:.2f} MB, {processing_time:.2f}s)"
            )
            
            # Update stats
            self.conversion_stats['total_processed'] += 1
            self.conversion_stats['successful'] += 1
            
            return ConversionResult(
                success=True,
                input_path=input_path,
                output_path=output_path,
                audio_info=audio_info,
                processing_time_seconds=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = str(e)
            
            LOGGER.error(f"Failed to convert {input_path}: {error_msg}")
            
            # Update stats
            self.conversion_stats['total_processed'] += 1
            self.conversion_stats['failed'] += 1
            
            return ConversionResult(
                success=False,
                input_path=input_path,
                error_message=error_msg,
                processing_time_seconds=processing_time
            )
    
    def convert_batch(
        self, 
        input_directory: Union[str, Path], 
        output_directory: Optional[Union[str, Path]] = None,
        recursive: bool = False
    ) -> List[ConversionResult]:
        """
        Convert multiple audio files in a directory
        
        Args:
            input_directory: Directory containing audio files
            output_directory: Output directory (optional)
            recursive: Search subdirectories recursively
            
        Returns:
            List of ConversionResult objects
        """
        input_dir = Path(input_directory)
        
        if not input_dir.exists() or not input_dir.is_dir():
            raise AudioConverterError(f"Input directory does not exist: {input_dir}")
        
        # Setup output directory
        if output_directory:
            output_dir = Path(output_directory)
            output_dir.mkdir(parents=True, exist_ok=True)
        else:
            output_dir = input_dir / "converted"
            output_dir.mkdir(exist_ok=True)
        
        # Find audio files
        audio_files = []
        search_pattern = "**/*" if recursive else "*"
        
        for pattern in [f"{search_pattern}{ext}" for ext in self.SUPPORTED_FORMATS]:
            audio_files.extend(input_dir.glob(pattern))
            audio_files.extend(input_dir.glob(pattern.upper()))
        
        # Remove duplicates and sort
        audio_files = sorted(set(audio_files))
        
        if not audio_files:
            LOGGER.warning(f"No audio files found in {input_dir}")
            return []
        
        LOGGER.info(f"Found {len(audio_files)} audio files in {input_dir}")
        LOGGER.info(f"Output directory: {output_dir}")
        
        # Process files
        results = []
        for audio_file in audio_files:
            output_file = output_dir / f"{audio_file.stem}_16khz_mono.wav"
            result = self.convert_single_file(audio_file, output_file)
            results.append(result)
        
        # Log summary
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        
        LOGGER.info(f"Batch conversion completed: {successful} successful, {failed} failed")
        
        return results
    
    def get_stats(self) -> Dict[str, int]:
        """Get conversion statistics"""
        return self.conversion_stats.copy()
    
    def reset_stats(self) -> None:
        """Reset conversion statistics"""
        self.conversion_stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0
        }


def create_converter(**kwargs) -> AudioConverter:
    """
    Factory function to create AudioConverter instance
    
    Returns:
        AudioConverter instance
    """
    return AudioConverter(**kwargs)


def convert_audio_file(
    input_path: Union[str, Path], 
    output_path: Optional[Union[str, Path]] = None
) -> ConversionResult:
    """
    Convenience function to convert a single audio file
    
    Args:
        input_path: Path to input audio file
        output_path: Path for output file (optional)
        
    Returns:
        ConversionResult object
    """
    converter = AudioConverter()
    return converter.convert_single_file(input_path, output_path)


def main():
    """Command line interface"""
    parser = argparse.ArgumentParser(
        description="Convert audio files to 16kHz mono WAV format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python audio_converter.py song.mp3
  python audio_converter.py song.flac -o output.wav
  python audio_converter.py -d /path/to/music/folder
  python audio_converter.py -d input_folder -od output_folder -r
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('input_file', nargs='?', help='Input audio file')
    group.add_argument('-d', '--directory', help='Directory containing audio files')
    
    parser.add_argument('-o', '--output', help='Output file (single file mode only)')
    parser.add_argument('-od', '--output-directory', help='Output directory (batch mode)')
    parser.add_argument('-r', '--recursive', action='store_true', 
                       help='Search subdirectories recursively')
    parser.add_argument('-v', '--verbose', action='store_true', 
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Setup logging level
    if args.verbose:
        LOGGER.setLevel(logging.DEBUG)
    
    try:
        converter = AudioConverter()
        
        if args.directory:
            # Batch processing
            results = converter.convert_batch(
                args.directory, 
                args.output_directory,
                args.recursive
            )
            
            # Print summary
            successful = sum(1 for r in results if r.success)
            failed = len(results) - successful
            LOGGER.info(f"Final summary: {successful} successful, {failed} failed")
            
        else:
            # Single file processing
            result = converter.convert_single_file(args.input_file, args.output)
            
            if result.success:
                LOGGER.info(f"Conversion completed successfully: {result.output_path}")
            else:
                LOGGER.error(f"Conversion failed: {result.error_message}")
                sys.exit(1)
                
    except Exception as e:
        LOGGER.error(f"Application error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()