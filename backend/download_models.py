#!/usr/bin/env python3
"""
Download models for AI FUN Token Wheel during Docker build.
Downloads GPT-2 (always) and Llama 3.2 1B (if HF_TOKEN is provided).
"""
import os
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


def download_llama(token):
    """Download Llama 3.2 1B model (requires HuggingFace token)."""
    print('Downloading Llama 3.2 1B with authentication...')
    try:
        AutoTokenizer.from_pretrained('meta-llama/Llama-3.2-1B', token=token)
        AutoModelForCausalLM.from_pretrained('meta-llama/Llama-3.2-1B', token=token)
        print('✓ Llama 3.2 1B download complete!')
        return True
    except Exception as e:
        print(f'ERROR downloading Llama 3.2 1B: {e}')
        return False


def main():
    # Always download GPT-2
    if not download_gpt2():
        sys.exit(1)

    # Download Llama only if HF_TOKEN is provided
    hf_token = os.environ.get('HF_TOKEN')
    if hf_token:
        print('\nHF_TOKEN detected - downloading Llama 3.2 1B...')
        if not download_llama(hf_token):
            sys.exit(1)
    else:
        print('\nSkipping Llama 3.2 1B - no HF_TOKEN provided (GPT-2 only build)')

    print('\n✓ All model downloads complete!')


if __name__ == '__main__':
    main()
