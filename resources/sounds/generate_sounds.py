#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Generate simple sound effects for DogeDictate
"""

import os
import math
import wave
import struct
import numpy as np

def generate_sine_wave(frequency, duration, sample_rate=44100, amplitude=0.5):
    """
    Generate a sine wave
    
    Args:
        frequency (float): Frequency in Hz
        duration (float): Duration in seconds
        sample_rate (int): Sample rate in Hz
        amplitude (float): Amplitude (0.0 to 1.0)
        
    Returns:
        numpy.ndarray: Audio data
    """
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    wave = amplitude * np.sin(2 * np.pi * frequency * t)
    return wave

def apply_fade(audio_data, fade_duration=0.05, sample_rate=44100):
    """
    Apply fade in/out to audio data
    
    Args:
        audio_data (numpy.ndarray): Audio data
        fade_duration (float): Fade duration in seconds
        sample_rate (int): Sample rate in Hz
        
    Returns:
        numpy.ndarray: Audio data with fade
    """
    fade_length = int(fade_duration * sample_rate)
    
    # Create fade in/out curves
    fade_in = np.linspace(0, 1, fade_length)
    fade_out = np.linspace(1, 0, fade_length)
    
    # Apply fade in
    audio_data[:fade_length] *= fade_in
    
    # Apply fade out
    audio_data[-fade_length:] *= fade_out
    
    return audio_data

def save_wav(audio_data, filename, sample_rate=44100):
    """
    Save audio data to WAV file
    
    Args:
        audio_data (numpy.ndarray): Audio data
        filename (str): Output filename
        sample_rate (int): Sample rate in Hz
    """
    # Normalize to 16-bit range
    audio_data = audio_data * 32767
    audio_data = audio_data.astype(np.int16)
    
    # Write WAV file
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data.tobytes())
    
    print(f"Sound saved to: {filename}")

def generate_start_sound(output_path, duration=0.3, sample_rate=44100):
    """
    Generate a sound for starting dictation
    
    Args:
        output_path (str): Output file path
        duration (float): Duration in seconds
        sample_rate (int): Sample rate in Hz
    """
    # Generate a rising tone
    start_freq = 440  # A4
    end_freq = 880    # A5
    
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    freq = np.linspace(start_freq, end_freq, len(t))
    
    audio_data = 0.5 * np.sin(2 * np.pi * freq * t)
    audio_data = apply_fade(audio_data, 0.05, sample_rate)
    
    save_wav(audio_data, output_path, sample_rate)

def generate_stop_sound(output_path, duration=0.3, sample_rate=44100):
    """
    Generate a sound for stopping dictation
    
    Args:
        output_path (str): Output file path
        duration (float): Duration in seconds
        sample_rate (int): Sample rate in Hz
    """
    # Generate a falling tone
    start_freq = 880  # A5
    end_freq = 440    # A4
    
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    freq = np.linspace(start_freq, end_freq, len(t))
    
    audio_data = 0.5 * np.sin(2 * np.pi * freq * t)
    audio_data = apply_fade(audio_data, 0.05, sample_rate)
    
    save_wav(audio_data, output_path, sample_rate)

def generate_error_sound(output_path, duration=0.5, sample_rate=44100):
    """
    Generate an error sound
    
    Args:
        output_path (str): Output file path
        duration (float): Duration in seconds
        sample_rate (int): Sample rate in Hz
    """
    # Generate two tones
    freq1 = 220  # A3
    freq2 = 233  # Bb3 (slightly dissonant)
    
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    
    audio_data1 = 0.3 * np.sin(2 * np.pi * freq1 * t)
    audio_data2 = 0.3 * np.sin(2 * np.pi * freq2 * t)
    
    audio_data = audio_data1 + audio_data2
    audio_data = apply_fade(audio_data, 0.05, sample_rate)
    
    save_wav(audio_data, output_path, sample_rate)

if __name__ == "__main__":
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Generate sounds
    generate_start_sound(os.path.join(script_dir, "start.wav"))
    generate_stop_sound(os.path.join(script_dir, "stop.wav"))
    generate_error_sound(os.path.join(script_dir, "error.wav"))
    
    print("Sound generation completed!") 