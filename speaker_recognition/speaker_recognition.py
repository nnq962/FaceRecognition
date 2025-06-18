"""
Speaker Recognition Module - Production-ready speaker embedding and recognition
Uses SpeechBrain ECAPA-TDNN for high-quality speaker embeddings

Author: Audio Processing Team
Version: 1.0.0
"""

import json
import numpy as np
from pathlib import Path
from typing import Union, Optional, Dict, List, Tuple
from dataclasses import dataclass
import time

import torch
import torchaudio
from speechbrain.inference import EncoderClassifier

try:
    from utils.logger_config import LOGGER
except ImportError:
    import logging
    LOGGER = logging.getLogger(__name__)
    LOGGER.warning("Could not import logger from utils.logger_config. Using default logger.")

try:
    from speaker_recognition.audio_converter import AudioConverter
except ImportError:
    LOGGER.warning("AudioConverter not found. Some features may be limited.")
    AudioConverter = None


@dataclass
class AudioEmbedding:
    """Data class for audio embedding results"""
    file_path: Path
    embedding: np.ndarray
    duration_seconds: float
    sample_rate: int
    processing_time_seconds: float
    model_name: str
    embedding_dim: int


@dataclass
class SimilarityResult:
    """Data class for similarity comparison results"""
    similarity_score: float
    is_same_speaker: bool
    threshold_used: float


class SpeakerRecognitionError(Exception):
    """Custom exception for speaker recognition errors"""
    pass


class SpeakerRecognition:
    """
    Speaker Recognition system using SpeechBrain ECAPA-TDNN model.
    
    Provides functionality for:
    - Audio file embedding extraction
    - Speaker similarity comparison using cosine similarity
    - Batch processing
    - Audio format conversion integration
    """
    
    DEFAULT_MODEL = "speechbrain/spkrec-ecapa-voxceleb"
    DEFAULT_SIMILARITY_THRESHOLD = 0.75  # Cosine similarity threshold (higher = more similar)
    REQUIRED_SAMPLE_RATE = 16000
    
    def __init__(self, 
                 model_name: str = DEFAULT_MODEL,
                 similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
                 auto_convert_audio: bool = True):
        """
        Initialize the Speaker Recognition model.
        
        Args:
            model_name: SpeechBrain model name for speaker recognition
            similarity_threshold: Cosine similarity threshold for same speaker (0-1, higher = more similar)
            auto_convert_audio: Whether to automatically convert audio to required format
        """
        self.model_name = model_name
        self.similarity_threshold = similarity_threshold
        self.auto_convert_audio = auto_convert_audio
        
        # Setup device
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        LOGGER.info(f"Initializing Speaker Recognition on device: {self.device}")
        
        # Initialize audio converter if available
        self.audio_converter = None
        if AudioConverter and auto_convert_audio:
            try:
                self.audio_converter = AudioConverter(check_dependencies=False)
                LOGGER.info("Audio converter initialized for automatic format conversion")
            except Exception as e:
                LOGGER.warning(f"Could not initialize audio converter: {e}")
        
        # Load model
        self._load_model()
        
        # Stats tracking
        self.processing_stats = {
            'embeddings_generated': 0,
            'comparisons_made': 0,
            'files_converted': 0
        }
    
    def _load_model(self) -> None:
        """Load the SpeechBrain model"""
        try:
            LOGGER.info(f"Loading model: {self.model_name}")
            
            model_save_dir = f"models/{self.model_name}"
            self.model = EncoderClassifier.from_hparams(
                source=self.model_name,
                savedir=model_save_dir,
                run_opts={"device": self.device}
            )
            
            LOGGER.info(f"Model loaded successfully. Save directory: {model_save_dir}")
            
        except Exception as e:
            raise SpeakerRecognitionError(f"Failed to load model {self.model_name}: {str(e)}") from e
    
    def _prepare_audio(self, audio_path: Union[str, Path]) -> Tuple[Path, bool]:
        """
        Prepare audio file for processing (convert if needed)
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Tuple of (prepared_file_path, was_converted)
        """
        audio_path = Path(audio_path)
        
        if not audio_path.exists():
            raise SpeakerRecognitionError(f"Audio file not found: {audio_path}")
        
        # Check if file needs conversion
        try:
            # Try to load audio info
            info = torchaudio.info(str(audio_path))
            
            # Check if conversion is needed
            needs_conversion = (
                info.sample_rate != self.REQUIRED_SAMPLE_RATE or
                info.num_channels != 1 or
                audio_path.suffix.lower() not in ['.wav']
            )
            
            if needs_conversion and self.audio_converter:
                LOGGER.info(f"Converting audio file: {audio_path.name}")
                
                # Convert audio
                converted_path = audio_path.parent / f"{audio_path.stem}_16khz_mono.wav"
                result = self.audio_converter.convert_single_file(audio_path, converted_path)
                
                if result.success:
                    self.processing_stats['files_converted'] += 1
                    return result.output_path, True
                else:
                    raise SpeakerRecognitionError(f"Audio conversion failed: {result.error_message}")
            
            elif needs_conversion and not self.audio_converter:
                LOGGER.warning(
                    f"Audio file may need conversion (SR: {info.sample_rate}, CH: {info.num_channels}) "
                    f"but auto_convert_audio is disabled"
                )
            
            return audio_path, False
            
        except Exception as e:
            if self.audio_converter:
                # Try conversion as fallback
                LOGGER.info(f"Could not read audio info, attempting conversion: {audio_path.name}")
                converted_path = audio_path.parent / f"{audio_path.stem}_16khz_mono.wav"
                result = self.audio_converter.convert_single_file(audio_path, converted_path)
                
                if result.success:
                    self.processing_stats['files_converted'] += 1
                    return result.output_path, True
                else:
                    raise SpeakerRecognitionError(f"Audio preparation failed: {result.error_message}")
            else:
                raise SpeakerRecognitionError(f"Could not prepare audio file: {str(e)}") from e
    
    def _load_audio_tensor(self, audio_path: Path) -> Tuple[torch.Tensor, int]:
        """
        Load audio file as tensor
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Tuple of (audio_tensor, sample_rate)
        """
        try:
            waveform, sample_rate = torchaudio.load(str(audio_path))
            
            # Move to device
            waveform = waveform.to(self.device)
            
            # Ensure mono
            if waveform.shape[0] > 1:
                waveform = torch.mean(waveform, dim=0, keepdim=True)
            
            LOGGER.debug(f"Loaded audio: shape={waveform.shape}, sr={sample_rate}")
            
            return waveform, sample_rate
            
        except Exception as e:
            raise SpeakerRecognitionError(f"Failed to load audio tensor from {audio_path}: {str(e)}") from e
    
    def _normalize_embedding(self, embedding: torch.Tensor) -> torch.Tensor:
        """
        Normalize embedding vector using L2 normalization
        
        Args:
            embedding: Raw embedding tensor
            
        Returns:
            L2 normalized embedding tensor
        """
        # L2 normalization: embedding / ||embedding||_2
        norm = torch.norm(embedding, p=2, dim=-1, keepdim=True)
        normalized_embedding = embedding / (norm + 1e-8)  # Add small epsilon to avoid division by zero
        
        LOGGER.debug(f"Embedding normalized - Original norm: {norm.item():.6f}, New norm: {torch.norm(normalized_embedding).item():.6f}")
        
        return normalized_embedding
    
    def extract_embedding(self, audio_path: Union[str, Path]) -> Tuple[Optional[AudioEmbedding], str]:
        """
        Extract speaker embedding from audio file
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Tuple containing:
            - AudioEmbedding object (None if failed)
            - Message string describing the result
        """
        start_time = time.time()
        audio_path = Path(audio_path)
        
        try:
            LOGGER.info(f"Extracting embedding from: {audio_path.name}")
            
            # Check if file exists
            if not audio_path.exists():
                message = f"File not found: {audio_path}"
                LOGGER.warning(message)
                return None, message
            
            # Check file extension
            allowed_extensions = {'.wav', '.mp3', '.flac', '.m4a', '.ogg', '.wma'}
            if audio_path.suffix.lower() not in allowed_extensions:
                message = f"Unsupported file format: {audio_path.suffix}. Allowed formats: {', '.join(allowed_extensions)}"
                LOGGER.warning(message)
                return None, message
            
            # Prepare audio (convert if needed)
            prepared_path, was_converted = self._prepare_audio(audio_path)
            
            # Load audio tensor
            waveform, sample_rate = self._load_audio_tensor(prepared_path)
            
            # Check if audio is valid
            if waveform is None or waveform.shape[1] == 0:
                message = f"Invalid or empty audio file: {audio_path.name}"
                LOGGER.warning(message)
                return None, message
            
            # Extract embedding
            LOGGER.debug("Generating speaker embedding...")
            with torch.no_grad():
                # SpeechBrain's encode_batch returns unnormalized embeddings
                embedding = self.model.encode_batch(waveform)
                embedding = embedding.squeeze()
                
                # Apply L2 normalization for better cosine similarity comparison
                embedding = self._normalize_embedding(embedding)
                
                # Convert to numpy
                embedding = embedding.cpu().numpy()
            
            # Calculate duration
            duration = waveform.shape[1] / sample_rate
            processing_time = time.time() - start_time
            
            success_message = (
                f"Embedding extracted successfully from {audio_path.name} - "
                f"Dim: {embedding.shape[0]}, Duration: {duration:.2f}s, "
                f"Processing time: {processing_time:.2f}s"
            )
            LOGGER.info(success_message)
            
            # Update stats
            self.processing_stats['embeddings_generated'] += 1
            
            # Clean up converted file if temporary
            if was_converted and prepared_path != audio_path:
                try:
                    prepared_path.unlink()
                    LOGGER.debug(f"Cleaned up temporary file: {prepared_path}")
                except Exception as e:
                    LOGGER.warning(f"Could not clean up temporary file {prepared_path}: {e}")
            
            audio_embedding = AudioEmbedding(
                file_path=audio_path,
                embedding=embedding,
                duration_seconds=duration,
                sample_rate=sample_rate,
                processing_time_seconds=processing_time,
                model_name=self.model_name,
                embedding_dim=embedding.shape[0]
            )
            
            return audio_embedding, success_message
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_message = f"Failed to extract embedding from {audio_path.name}: {str(e)}"
            LOGGER.error(error_message)
            
            # Update error stats if available
            if hasattr(self, 'processing_stats'):
                if 'failed_extractions' not in self.processing_stats:
                    self.processing_stats['failed_extractions'] = 0
                self.processing_stats['failed_extractions'] += 1
            
            return None, error_message
    
    def compare_embeddings(self, 
                         embedding1: np.ndarray, 
                         embedding2: np.ndarray,
                         threshold: Optional[float] = None) -> SimilarityResult:
        """
        Compare two speaker embeddings using cosine similarity
        
        Args:
            embedding1: First speaker embedding (should be L2 normalized)
            embedding2: Second speaker embedding (should be L2 normalized)
            threshold: Custom cosine similarity threshold (0-1, uses default if None)
            
        Returns:
            SimilarityResult with similarity metrics
        """
        if threshold is None:
            threshold = self.similarity_threshold
        
        try:
            # Ensure embeddings are numpy arrays
            if isinstance(embedding1, torch.Tensor):
                embedding1 = embedding1.cpu().numpy()
            if isinstance(embedding2, torch.Tensor):
                embedding2 = embedding2.cpu().numpy()
            
            # Ensure embeddings are normalized (L2 norm = 1)
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)
            
            if not (0.99 <= norm1 <= 1.01):
                LOGGER.warning(f"Embedding1 may not be normalized (norm: {norm1:.6f})")
                embedding1 = embedding1 / (norm1 + 1e-8)
            
            if not (0.99 <= norm2 <= 1.01):
                LOGGER.warning(f"Embedding2 may not be normalized (norm: {norm2:.6f})")
                embedding2 = embedding2 / (norm2 + 1e-8)
            
            # Calculate cosine similarity (for normalized vectors, this is just dot product)
            similarity = np.dot(embedding1, embedding2)
            
            # Determine if same speaker (higher similarity = more similar)
            is_same_speaker = similarity >= threshold
            
            self.processing_stats['comparisons_made'] += 1
            
            LOGGER.debug(f"Cosine similarity: {similarity:.4f}, Same speaker: {is_same_speaker} (threshold: {threshold})")
            
            return SimilarityResult(
                similarity_score=float(similarity),
                is_same_speaker=is_same_speaker,
                threshold_used=threshold
            )
            
        except Exception as e:
            raise SpeakerRecognitionError(f"Failed to compare embeddings: {str(e)}") from e
    
    def compare_audio_files(self, 
                          audio_path1: Union[str, Path], 
                          audio_path2: Union[str, Path],
                          threshold: Optional[float] = None) -> SimilarityResult:
        """
        Compare two audio files for speaker similarity
        
        Args:
            audio_path1: Path to first audio file
            audio_path2: Path to second audio file
            threshold: Custom threshold (uses default if None)
            
        Returns:
            SimilarityResult with similarity metrics
        """
        try:
            LOGGER.info(f"Comparing audio files: {Path(audio_path1).name} vs {Path(audio_path2).name}")
            
            # Extract embeddings
            embedding1 = self.extract_embedding(audio_path1)
            embedding2 = self.extract_embedding(audio_path2)
            
            # Compare embeddings
            result = self.compare_embeddings(
                embedding1.embedding, 
                embedding2.embedding, 
                threshold
            )
            
            LOGGER.info(f"Comparison result: Similarity={result.similarity_score:.4f}, Same speaker: {result.is_same_speaker}")
            
            return result
            
        except Exception as e:
            raise SpeakerRecognitionError(f"Failed to compare audio files: {str(e)}") from e
    
    def extract_embeddings_batch(self, 
                               audio_paths: List[Union[str, Path]]) -> List[AudioEmbedding]:
        """
        Extract embeddings from multiple audio files
        
        Args:
            audio_paths: List of paths to audio files
            
        Returns:
            List of AudioEmbedding objects
        """
        LOGGER.info(f"Extracting embeddings from {len(audio_paths)} files")
        
        embeddings = []
        successful = 0
        failed = 0
        
        for audio_path in audio_paths:
            try:
                embedding = self.extract_embedding(audio_path)
                embeddings.append(embedding)
                successful += 1
            except Exception as e:
                LOGGER.error(f"Failed to process {audio_path}: {str(e)}")
                failed += 1
        
        LOGGER.info(f"Batch processing completed: {successful} successful, {failed} failed")
        
        return embeddings
    
    def save_embedding(self, embedding: AudioEmbedding, output_path: Union[str, Path]) -> None:
        """
        Save embedding to file
        
        Args:
            embedding: AudioEmbedding object to save
            output_path: Path to save the embedding
        """
        output_path = Path(output_path)
        
        try:
            embedding_data = {
                'file_path': str(embedding.file_path),
                'embedding': embedding.embedding.tolist(),
                'duration_seconds': embedding.duration_seconds,
                'sample_rate': embedding.sample_rate,
                'processing_time_seconds': embedding.processing_time_seconds,
                'model_name': embedding.model_name,
                'embedding_dim': embedding.embedding_dim,
                'created_at': time.time(),
                'is_normalized': True,  # Flag to indicate embedding is L2 normalized
                'normalization_method': 'L2'
            }
            
            with open(output_path, 'w') as f:
                json.dump(embedding_data, f, indent=2)
            
            LOGGER.info(f"Embedding saved to: {output_path}")
            
        except Exception as e:
            raise SpeakerRecognitionError(f"Failed to save embedding: {str(e)}") from e
    
    def load_embedding(self, embedding_path: Union[str, Path]) -> AudioEmbedding:
        """
        Load embedding from file
        
        Args:
            embedding_path: Path to saved embedding file
            
        Returns:
            AudioEmbedding object
        """
        embedding_path = Path(embedding_path)
        
        try:
            with open(embedding_path, 'r') as f:
                data = json.load(f)
            
            return AudioEmbedding(
                file_path=Path(data['file_path']),
                embedding=np.array(data['embedding']),
                duration_seconds=data['duration_seconds'],
                sample_rate=data['sample_rate'],
                processing_time_seconds=data['processing_time_seconds'],
                model_name=data['model_name'],
                embedding_dim=data['embedding_dim']
            )
            
        except Exception as e:
            raise SpeakerRecognitionError(f"Failed to load embedding: {str(e)}") from e
    
    def get_stats(self) -> Dict[str, int]:
        """Get processing statistics"""
        return self.processing_stats.copy()
    
    def reset_stats(self) -> None:
        """Reset processing statistics"""
        self.processing_stats = {
            'embeddings_generated': 0,
            'comparisons_made': 0,
            'files_converted': 0
        }


# Convenience functions
def extract_speaker_embedding(audio_path: Union[str, Path], 
                            model_name: str = SpeakerRecognition.DEFAULT_MODEL) -> AudioEmbedding:
    """
    Convenience function to extract a single speaker embedding
    
    Args:
        audio_path: Path to audio file
        model_name: SpeechBrain model name
        
    Returns:
        AudioEmbedding object
    """
    recognizer = SpeakerRecognition(model_name=model_name)
    return recognizer.extract_embedding(audio_path)


def compare_speakers(audio_path1: Union[str, Path], 
                   audio_path2: Union[str, Path],
                   threshold: float = SpeakerRecognition.DEFAULT_SIMILARITY_THRESHOLD) -> SimilarityResult:
    """
    Convenience function to compare two speakers
    
    Args:
        audio_path1: Path to first audio file
        audio_path2: Path to second audio file
        threshold: Cosine similarity threshold (0-1, higher = more similar)
        
    Returns:
        SimilarityResult object
    """
    recognizer = SpeakerRecognition(similarity_threshold=threshold)
    return recognizer.compare_audio_files(audio_path1, audio_path2)


if __name__ == "__main__":
    # Example usage
    import argparse
    
    parser = argparse.ArgumentParser(description="Speaker Recognition CLI")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Extract embedding command
    extract_parser = subparsers.add_parser('extract', help='Extract speaker embedding')
    extract_parser.add_argument('audio_file', help='Audio file path')
    extract_parser.add_argument('-o', '--output', help='Output embedding file')
    extract_parser.add_argument('-m', '--model', default=SpeakerRecognition.DEFAULT_MODEL, help='Model name')
    
    # Compare command
    compare_parser = subparsers.add_parser('compare', help='Compare two audio files')
    compare_parser.add_argument('audio1', help='First audio file')
    compare_parser.add_argument('audio2', help='Second audio file')
    compare_parser.add_argument('-t', '--threshold', type=float, 
                              default=SpeakerRecognition.DEFAULT_SIMILARITY_THRESHOLD, 
                              help='Cosine similarity threshold (0-1, higher = more similar)')
    
    args = parser.parse_args()
    
    if args.command == 'extract':
        embedding = extract_speaker_embedding(args.audio_file, args.model)
        print(f"Embedding extracted: {embedding.embedding_dim} dimensions")
        
        if args.output:
            recognizer = SpeakerRecognition()
            recognizer.save_embedding(embedding, args.output)
            print(f"Saved to: {args.output}")
    
    elif args.command == 'compare':
        result = compare_speakers(args.audio1, args.audio2, args.threshold)
        print(f"Cosine similarity: {result.similarity_score:.4f}")
        print(f"Same speaker: {result.is_same_speaker}")
        print(f"Threshold used: {result.threshold_used}")
    
    else:
        parser.print_help()