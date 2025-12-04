#!/usr/bin/env python3
"""
Download models for AI FUN Token Wheel during Docker build.
Downloads GPT-2 and TinyLlama 1.1B (both ungated, no authentication needed).
"""
import sys
from transformers import AutoModelForCausalLM, AutoTokenizer


def download_gpt2():
    """Download GPT-2 model (no authentication required)."""
    print('Downloading GPT-2...')
    try:
        AutoTokenizer.from_pretrained('gpt2')
        AutoModelForCausalLM.from_pretrained('gpt2')
        print('✓ GPT-2 download complete!')
        return True
    except Exception as e:
        print(f'ERROR downloading GPT-2: {e}')
        return False


def download_tinyllama():
    """Download TinyLlama 1.1B model (no authentication required)."""
    print('Downloading TinyLlama 1.1B...')
    try:
        AutoTokenizer.from_pretrained('TinyLlama/TinyLlama-1.1B-Chat-v1.0')
        AutoModelForCausalLM.from_pretrained('TinyLlama/TinyLlama-1.1B-Chat-v1.0')
        print('✓ TinyLlama 1.1B download complete!')
        return True
    except Exception as e:
        print(f'ERROR downloading TinyLlama 1.1B: {e}')
        return False


def main():
    # Download both models
    if not download_gpt2():
        sys.exit(1)

    if not download_tinyllama():
        sys.exit(1)

    print('\n✓ All model downloads complete!')


if __name__ == '__main__':
    main()
