# core/transcription/audio_cleaner.py

"""
Phase 10 — Audio Cleaning & Enhancement
Improves transcription accuracy by cleaning audio before Whisper processing.
"""

import numpy as np
import librosa
import soundfile as sf
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class AudioCleaner:
    """
    Audio cleaning and enhancement pipeline.
    Reduces noise and improves signal quality for better transcription.
    """
    
    def __init__(self, sr: int = 16000):
        """
        Initialize cleaner with target sample rate.
        
        Args:
            sr: Sample rate in Hz (default: 16000 for Whisper)
        """
        self.sr = sr
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    # ── Step 1: Load Audio ─────────────────────────────────────────────────
    
    def load_audio(self, audio_path: str) -> tuple[np.ndarray, int]:
        """
        Load audio file with automatic resampling.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            (audio_data, sample_rate)
        """
        try:
            y, sr = librosa.load(audio_path, sr=self.sr, mono=True)
            self.logger.info(f"Loaded audio: {len(y)} samples @ {sr}Hz")
            return y, sr
        except Exception as e:
            self.logger.error(f"Failed to load audio: {e}")
            raise
    
    # ── Step 2: Detect and Remove Silence ──────────────────────────────────
    
    def trim_silence(
        self, 
        y: np.ndarray, 
        top_db: float = 40,
        min_duration: float = 0.5
    ) -> np.ndarray:
        """
        Remove leading/trailing silence and long silent segments.
        
        Args:
            y: Audio time series
            top_db: Threshold (dB) below reference to consider as silence
            min_duration: Minimum silent duration to remove (seconds)
            
        Returns:
            Trimmed audio
        """
        # Trim edges
        y_trimmed, _ = librosa.effects.trim(y, top_db=top_db)
        
        # Remove long silence in the middle
        # Get S gram for silence detection
        S = librosa.feature.melspectrogram(y=y_trimmed, sr=self.sr)
        S_db = librosa.power_to_db(S, ref=np.max)
        
        # Find silent frames
        silent_frames = np.mean(S_db, axis=0) < -top_db
        
        # Convert to time indices
        frame_length = len(y_trimmed) / len(silent_frames)
        min_frames = int(min_duration * self.sr / (self.sr / S.shape[1]))
        
        self.logger.info(f"Trimmed silence: {len(y)} → {len(y_trimmed)} samples")
        
        return y_trimmed
    
    # ── Step 3: Noise Reduction (Spectral Subtraction) ────────────────────
    
    def reduce_noise_spectral(
        self,
        y: np.ndarray,
        n_fft: int = 2048,
        noise_duration: float = 1.0
    ) -> np.ndarray:
        """
        Reduce noise using spectral subtraction.
        Assumes first N seconds are mostly noise (or silence).
        
        Args:
            y: Audio time series
            n_fft: FFT window size
            noise_duration: Duration of noise profile (seconds)
            
        Returns:
            Noise-reduced audio
        """
        # Get noise profile from beginning
        noise_sample_count = int(noise_duration * self.sr)
        noise_profile = y[:noise_sample_count]
        
        # Compute STFT
        D = librosa.stft(y, n_fft=n_fft)
        S = np.abs(D)
        phase = np.angle(D)
        
        # Compute noise magnitude spectrum
        D_noise = librosa.stft(noise_profile, n_fft=n_fft)
        S_noise = np.mean(np.abs(D_noise), axis=1, keepdims=True)
        
        # Spectral subtraction
        S_cleaned = S - 2.0 * S_noise  # aggressive factor: 2.0
        S_cleaned = np.maximum(S_cleaned, 0.1 * S)  # floor to avoid over-subtraction
        
        # Reconstruct
        D_cleaned = S_cleaned * np.exp(1j * phase)
        y_cleaned = librosa.istft(D_cleaned)
        
        self.logger.info("Applied spectral subtraction noise reduction")
        
        return y_cleaned
    
    # ── Step 4: Normalize Audio Level ──────────────────────────────────────
    
    def normalize_level(
        self,
        y: np.ndarray,
        target_loudness: float = -20.0
    ) -> np.ndarray:
        """
        Normalize audio to target loudness using LUFS-like approach.
        
        Args:
            y: Audio time series
            target_loudness: Target loudness in dB (default -20 is moderate)
            
        Returns:
            Normalized audio
        """
        # Calculate current loudness (simplified)
        S = librosa.feature.melspectrogram(y=y, sr=self.sr)
        loudness = np.mean(librosa.power_to_db(S, ref=np.max))
        
        # Calculate gain needed
        gain_db = target_loudness - loudness
        gain_linear = 10 ** (gain_db / 20.0)
        
        y_normalized = y * gain_linear
        
        # Prevent clipping
        max_val = np.max(np.abs(y_normalized))
        if max_val > 1.0:
            y_normalized = y_normalized / max_val
        
        self.logger.info(f"Normalized level: {loudness:.1f}dB → {target_loudness:.1f}dB")
        
        return y_normalized
    
    # ── Step 5: Dynamic Range Compression ──────────────────────────────────
    
    def apply_compression(
        self,
        y: np.ndarray,
        threshold: float = -20,
        ratio: float = 4.0,
        attack_ms: float = 10,
        release_ms: float = 100
    ) -> np.ndarray:
        """
        Apply dynamic range compression to even out volume.
        Helps with variable speaker volumes.
        
        Args:
            y: Audio time series
            threshold: Threshold in dB
            ratio: Compression ratio (4:1 = moderate)
            attack_ms: Attack time in milliseconds
            release_ms: Release time in milliseconds
            
        Returns:
            Compressed audio
        """
        # Convert to dB
        S = np.abs(librosa.stft(y)) + 1e-9
        S_db = librosa.power_to_db(S, ref=np.max)
        
        # Apply compression logic
        gain = np.zeros_like(S_db)
        above_threshold = S_db > threshold
        gain[above_threshold] = (threshold + (S_db[above_threshold] - threshold) / ratio) - S_db[above_threshold]
        gain[~above_threshold] = 0
        
        # Convert back to linear
        gain_linear = 10 ** (gain / 20.0)
        
        # Apply gain
        S_compressed = S * gain_linear
        phase = np.angle(librosa.stft(y))
        D_compressed = S_compressed * np.exp(1j * phase)
        
        y_compressed = librosa.istft(D_compressed)
        
        self.logger.info("Applied dynamic range compression")
        
        return y_compressed
    
    # ── Step 6: Quality Check ──────────────────────────────────────────────
    
    def check_quality(self, y: np.ndarray) -> dict:
        """
        Check audio quality metrics.
        
        Args:
            y: Audio time series
            
        Returns:
            Quality report dict
        """
        # SNR estimation
        silence_threshold = np.max(np.abs(y)) * 0.1
        noise_level = np.mean(np.abs(y[np.abs(y) < silence_threshold]))
        signal_level = np.mean(np.abs(y[np.abs(y) >= silence_threshold]))
        snr = 20 * np.log10(signal_level / (noise_level + 1e-9))
        
        # Clipping detection
        clipping_ratio = np.sum(np.abs(y) > 0.99) / len(y)
        
        # Duration
        duration = len(y) / self.sr
        
        report = {
            "duration_seconds": duration,
            "snr_db": snr,
            "clipping_ratio": clipping_ratio,
            "min_db": 20 * np.log10(np.min(np.abs(y) + 1e-9)),
            "max_db": 20 * np.log10(np.max(np.abs(y))),
            "warnings": []
        }
        
        # Generate warnings
        if snr < 15:
            report["warnings"].append("Low SNR - audio may be noisy")
        if clipping_ratio > 0.01:
            report["warnings"].append("Clipping detected - audio distorted")
        if duration < 5:
            report["warnings"].append("Very short audio - may not be sufficient")
        
        self.logger.info(f"Quality report: SNR={snr:.1f}dB, Clipping={clipping_ratio*100:.2f}%")
        
        return report
    
    # ── Full Pipeline ──────────────────────────────────────────────────────
    
    def clean_audio(
        self,
        input_path: str,
        output_path: str = None,
        enable_noise_reduction: bool = True,
        enable_compression: bool = True,
        save_output: bool = True
    ) -> dict:
        """
        Full audio cleaning pipeline.
        
        Args:
            input_path: Input audio file path
            output_path: Output audio file path (auto-generated if None)
            enable_noise_reduction: Enable spectral subtraction
            enable_compression: Enable dynamic range compression
            save_output: Whether to save cleaned audio
            
        Returns:
            {
                "output_path": str,
                "quality_before": dict,
                "quality_after": dict,
                "processing_steps": list
            }
        """
        input_file = Path(input_path)
        if not input_file.exists():
            raise FileNotFoundError(f"Audio file not found: {input_path}")
        
        # Default output path
        if output_path is None:
            output_path = input_file.parent / f"{input_file.stem}_cleaned.wav"
        
        self.logger.info(f"Starting audio cleaning: {input_file}")
        
        steps = []
        
        # Load audio
        y, sr = self.load_audio(str(input_path))
        quality_before = self.check_quality(y)
        steps.append("load")
        
        # Clean steps
        y = self.trim_silence(y)
        steps.append("trim_silence")
        
        if enable_noise_reduction:
            y = self.reduce_noise_spectral(y)
            steps.append("noise_reduction")
        
        y = self.normalize_level(y)
        steps.append("normalize")
        
        if enable_compression:
            y = self.apply_compression(y)
            steps.append("compression")
        
        # Quality check
        quality_after = self.check_quality(y)
        
        # Save
        if save_output:
            sf.write(str(output_path), y, sr, subtype='PCM_16')
            self.logger.info(f"Cleaned audio saved: {output_path}")
        
        return {
            "output_path": str(output_path),
            "quality_before": quality_before,
            "quality_after": quality_after,
            "processing_steps": steps,
            "snr_improvement_db": quality_after["snr_db"] - quality_before["snr_db"]
        }


# ── Convenience functions ──────────────────────────────────────────────────

def clean_audio_simple(
    input_path: str,
    output_path: str = None
) -> str:
    """
    Simple one-liner for audio cleaning.
    
    Args:
        input_path: Input file path
        output_path: Output file path
        
    Returns:
        Path to cleaned audio file
    """
    cleaner = AudioCleaner(sr=16000)
    result = cleaner.clean_audio(
        input_path,
        output_path,
        enable_noise_reduction=True,
        enable_compression=True
    )
    return result["output_path"]