"""
GPT-2 Token Wheel Generator

This module provides the core functionality for generating token probability
distributions and mapping them to wheel wedges for visualization.

Educational purpose: Demonstrates how LLMs generate text by sampling from
probability distributions, visualized as a spinning wheel.
"""

from typing import Dict, List, Optional
import torch
import numpy as np
import time
import os
import glob
from transformers import AutoModelForCausalLM, AutoTokenizer


# Model Configuration Registry
SUPPORTED_MODELS = {
    'gpt2': {
        'hf_model_name': 'gpt2',
        'display_name': 'GPT-2 (124M)',
        'params': '124M',
        'size_mb': 500,
        'ram_required_gb': 2,
        'requires_auth': False,
        'is_default': True,
        'default_min_threshold': 0.1,
        'default_secondary_threshold': 0.05
    },
    'tinyllama-1.1b': {
        'hf_model_name': 'TinyLlama/TinyLlama-1.1B-Chat-v1.0',
        'display_name': 'TinyLlama 1.1B',
        'params': '1.1B',
        'size_mb': 2200,
        'ram_required_gb': 4,
        'requires_auth': False,
        'is_default': False,
        'default_min_threshold': 0.1,
        'default_secondary_threshold': 0.05
    }
}


class TokenWheelGenerator:
    """
    Generator for token probability distributions and wheel visualizations.

    This class handles:
    - Loading and running any supported language model inference
    - Extracting token probability distributions
    - Mapping probabilities to wheel wedges
    - Sampling tokens from distributions

    Attributes:
        model: The language model
        tokenizer: The tokenizer
        device: Device to run inference on ('cpu' or 'cuda')
        model_key: Key identifying which model is loaded (from SUPPORTED_MODELS)
        model_config: Configuration dict for the loaded model
    """

    def __init__(self, model_key: str = 'gpt2', device: Optional[str] = None, hf_token: Optional[str] = None):
        """
        Initialize the Token Wheel Generator with the specified model.

        Args:
            model_key: Key from SUPPORTED_MODELS dict (e.g., 'gpt2', 'llama-3.2-1b')
                      Default: 'gpt2'
            device: Device to run inference on. Options: 'cpu', 'cuda', or None.
                   If None, automatically detects CUDA availability.
            hf_token: HuggingFace API token for gated models (required for Llama)

        Raises:
            ValueError: If model_key is not in SUPPORTED_MODELS
        """
        # Validate model_key
        if model_key not in SUPPORTED_MODELS:
            raise ValueError(f"Unsupported model: {model_key}. Must be one of {list(SUPPORTED_MODELS.keys())}")

        self.model_key = model_key
        self.model_config = SUPPORTED_MODELS[model_key]
        hf_model_name = self.model_config['hf_model_name']

        # Set device
        if device is None:
            device = 'cuda' if torch.cuda.is_available() else 'cpu'

        self.device = torch.device(device)

        # Load model and tokenizer (all models are ungated)
        print(f"Loading {self.model_config['display_name']} ({hf_model_name}) on {self.device}...")

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(hf_model_name)
            self.model = AutoModelForCausalLM.from_pretrained(hf_model_name)
            print("Model loaded successfully!")
        except Exception as e:
            raise Exception(f"Failed to load {hf_model_name}: {e}")

        # Set pad token if missing (required for TinyLlama and some other models)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        # Move model to device and set to evaluation mode
        self.model.to(self.device)
        self.model.eval()

        print(f"Model loaded successfully!")

    def get_next_token_distribution(
        self,
        context: str,
        min_threshold: float = 0.1,
        secondary_threshold: float = 0.05
    ) -> Dict:
        """
        Get the probability distribution for the next token given a context.

        Uses dynamic threshold-based token selection:
        1. Include all tokens with probability ≥ min_threshold (default 5%)
        2. If remaining probability > 20%, also include tokens ≥ secondary_threshold (3%)
        3. Calculate remaining probability for "other" category

        Args:
            context: The input text context to condition on
            min_threshold: Primary probability threshold (default 0.05 = 5%)
            secondary_threshold: Secondary threshold for flat distributions (default 0.03 = 3%)

        Returns:
            Dictionary containing:
            - tokens: List of token dicts with {token, token_id, probability, is_special}
            - remaining_probability: Probability mass in "other" category
            - context: The input context (echoed back)
            - num_tokens: Number of tokens returned
        """
        # Tokenize the context
        input_ids = self.tokenizer.encode(context, return_tensors='pt').to(self.device)

        # Run forward pass (no gradient needed)
        with torch.no_grad():
            outputs = self.model(input_ids)
            logits = outputs.logits[0, -1, :]  # Get logits for last token

        # Apply softmax to get probabilities
        probabilities = torch.softmax(logits, dim=0)

        # Convert to numpy for easier manipulation
        probs_np = probabilities.cpu().numpy()

        # Primary selection: tokens with probability ≥ min_threshold
        primary_mask = probs_np >= min_threshold
        selected_tokens = []

        for token_id in np.where(primary_mask)[0]:
            prob = float(probs_np[token_id])
            token_str = self.tokenizer.decode([token_id])

            selected_tokens.append({
                'token': token_str,
                'token_id': int(token_id),
                'probability': prob,
                'is_special': token_id in self.tokenizer.all_special_ids
            })

        # Calculate remaining probability
        primary_probability_sum = sum(t['probability'] for t in selected_tokens)
        remaining_probability = 1.0 - primary_probability_sum

        # Secondary selection: if remaining > 20%, include secondary threshold tokens
        if remaining_probability > 0.2:
            secondary_mask = (probs_np >= secondary_threshold) & (~primary_mask)

            for token_id in np.where(secondary_mask)[0]:
                prob = float(probs_np[token_id])
                token_str = self.tokenizer.decode([token_id])

                selected_tokens.append({
                    'token': token_str,
                    'token_id': int(token_id),
                    'probability': prob,
                    'is_special': token_id in self.tokenizer.all_special_ids
                })

            # Recalculate remaining probability
            total_probability_sum = sum(t['probability'] for t in selected_tokens)
            remaining_probability = 1.0 - total_probability_sum

        # Sort by probability (descending)
        selected_tokens.sort(key=lambda x: x['probability'], reverse=True)

        return {
            'tokens': selected_tokens,
            'remaining_probability': remaining_probability,
            'context': context,
            'num_tokens': len(selected_tokens)
        }

    def map_distribution_to_wedges(self, distribution: Dict) -> List[Dict]:
        """
        Map a token probability distribution to wheel wedges.

        Each wedge is allocated sequentially with angle proportional to probability:
        - Wedge angle = (token_probability / 1.0) × 360°
        - Wedges are positioned sequentially (no gaps)
        - "Other" wedge fills remaining space to 360°

        Args:
            distribution: Token distribution from get_next_token_distribution()

        Returns:
            List of wedge dictionaries, each containing:
            - token: Token string
            - token_id: Token ID
            - probability: Token probability
            - start_angle: Starting angle in degrees [0, 360)
            - end_angle: Ending angle in degrees (0, 360]
            - is_special: Whether token is a special token
            - is_other: Whether this is the "other" wedge
        """
        wedges = []
        current_angle = 0.0

        # Create wedges for each token
        for token_info in distribution['tokens']:
            # Calculate wedge angle from probability
            wedge_angle = token_info['probability'] * 360.0

            # Create wedge
            wedge = {
                'token': token_info['token'],
                'token_id': token_info['token_id'],
                'probability': token_info['probability'],
                'start_angle': current_angle,
                'end_angle': current_angle + wedge_angle,
                'is_special': token_info['is_special'],
                'is_other': False
            }

            wedges.append(wedge)
            current_angle += wedge_angle

        # Add "other" wedge for remaining probability
        if distribution['remaining_probability'] > 0:
            other_wedge = {
                'token': '<OTHER>',
                'token_id': -1,
                'probability': distribution['remaining_probability'],
                'start_angle': current_angle,
                'end_angle': 360.0,
                'is_special': False,
                'is_other': True
            }
            wedges.append(other_wedge)

        return wedges

    def get_tokens_with_probabilities(self, distribution: Dict, top_other_count: int = 5) -> List[Dict]:
        """
        Convert distribution to a simple list of tokens with probabilities.

        This is for the frontend to handle all wedge/angle calculations.

        Args:
            distribution: Token distribution from get_next_token_distribution()
            top_other_count: Number of top tokens to include from "other" category (default 5)

        Returns:
            List of dicts with token, token_id, probability, is_special, is_other, and
            optionally other_top_tokens for the "other" category
        """
        tokens_list = []

        # Add all main tokens
        for token_info in distribution['tokens']:
            tokens_list.append({
                'token': token_info['token'],
                'token_id': token_info['token_id'],
                'probability': token_info['probability'],
                'is_special': token_info['is_special'],
                'is_other': False
            })

        # Add "other" category if there's remaining probability
        if distribution['remaining_probability'] > 0:
            # Calculate the count of remaining tokens and get top tokens
            context = distribution['context']
            input_ids = self.tokenizer.encode(context, return_tensors='pt').to(self.device)

            with torch.no_grad():
                outputs = self.model(input_ids)
                logits = outputs.logits[0, -1, :]
                probabilities = torch.softmax(logits, dim=0)
                probs_np = probabilities.cpu().numpy()

            # Get token IDs that are in the main distribution
            included_token_ids = set(t['token_id'] for t in distribution['tokens'])

            # Get all other tokens (not in main distribution) with their probabilities
            other_tokens = []
            for token_id in range(len(probs_np)):
                if token_id not in included_token_ids and probs_np[token_id] > 0:
                    other_tokens.append({
                        'token_id': token_id,
                        'probability': float(probs_np[token_id])
                    })

            # Sort by probability descending
            other_tokens.sort(key=lambda x: x['probability'], reverse=True)

            # Get top N tokens from the "other" category
            top_other_tokens = []
            for i in range(min(top_other_count, len(other_tokens))):
                token_id = other_tokens[i]['token_id']
                token_str = self.tokenizer.decode([token_id])
                top_other_tokens.append({
                    'token': token_str,
                    'token_id': token_id,
                    'probability': other_tokens[i]['probability']
                })

            remaining_count = len(other_tokens)

            tokens_list.append({
                'token': 'Remaining Tokens',
                'token_id': -1,
                'probability': distribution['remaining_probability'],
                'is_special': False,
                'is_other': True,
                'other_top_tokens': top_other_tokens,
                'remaining_count': remaining_count
            })

        return tokens_list

    def sample_token_from_distribution(self, distribution: Dict) -> Dict:
        """
        Sample a token from the probability distribution.

        Uses numpy.random.choice for probabilistic sampling. If "other" is selected,
        samples again from the remaining distribution (tokens below threshold).

        Args:
            distribution: Token distribution from get_next_token_distribution()

        Returns:
            Dictionary containing:
            - token: The selected token string
            - token_id: The selected token ID
            - probability: Probability of the selected token
            - wedge_start: Start angle of the token's wedge
            - wedge_end: End angle of the token's wedge
            - target_angle: Random angle within the wedge (for animation)
            - is_other: Whether "other" was selected
        """
        # Build probability array including "other"
        tokens = distribution['tokens']
        probabilities = [t['probability'] for t in tokens]
        probabilities.append(distribution['remaining_probability'])

        # Normalize to ensure sum is exactly 1.0 (handles floating point errors)
        probabilities = np.array(probabilities)
        probabilities = probabilities / probabilities.sum()

        # Sample from distribution
        sample_idx = np.random.choice(len(probabilities), p=probabilities)

        # Get wedges for angle calculation
        wedges = self.map_distribution_to_wedges(distribution)

        # Check if "other" was selected
        if sample_idx == len(tokens):
            # "Other" was selected - sample from remaining distribution
            selected_wedge = wedges[-1]  # Last wedge is "other"
            target_angle = np.random.uniform(
                selected_wedge['start_angle'],
                selected_wedge['end_angle']
            )
            return self._sample_from_other(distribution, selected_wedge, target_angle)
        else:
            # Regular token was selected
            selected_token = tokens[sample_idx]
            selected_wedge = wedges[sample_idx]

            return {
                'token': selected_token['token'],
                'token_id': selected_token['token_id'],
                'probability': selected_token['probability'],
                'wedge_start': selected_wedge['start_angle'],
                'wedge_end': selected_wedge['end_angle'],
                'target_angle': np.random.uniform(
                    selected_wedge['start_angle'],
                    selected_wedge['end_angle']
                ),
                'is_other': False
            }

    def select_token_from_angle(self, distribution: Dict, landing_angle: float) -> Dict:
        """
        Select a token based on where the wheel landed (landing angle).

        Finds which wedge the landing angle falls into and returns that token.
        If "other" is selected, samples from the remaining distribution.

        Args:
            distribution: Token distribution from get_next_token_distribution()
            landing_angle: Angle where the wheel pointer landed (0-360 degrees)

        Returns:
            Dictionary containing token information (same format as sample_token_from_distribution)
        """
        # Get wedges for the distribution
        wedges = self.map_distribution_to_wedges(distribution)
        tokens = distribution['tokens']

        # Find which wedge the landing angle falls into
        selected_wedge = None
        selected_token = None
        is_other = False

        for i, wedge in enumerate(wedges):
            if wedge['start_angle'] <= landing_angle < wedge['end_angle']:
                selected_wedge = wedge
                if wedge['is_other']:
                    is_other = True
                else:
                    selected_token = tokens[i]
                break

        # Handle edge case where landing_angle == 360.0 (should map to last wedge)
        if selected_wedge is None and landing_angle == 360.0:
            selected_wedge = wedges[-1]
            if selected_wedge['is_other']:
                is_other = True
            else:
                selected_token = tokens[-1]

        if selected_wedge is None:
            raise ValueError(f"Landing angle {landing_angle} does not fall in any wedge")

        if is_other:
            # "Other" was selected - sample from remaining distribution
            return self._sample_from_other(distribution, selected_wedge, landing_angle)
        else:
            # Regular token was selected
            return {
                'token': selected_token['token'],
                'token_id': selected_token['token_id'],
                'probability': selected_token['probability'],
                'wedge_start': selected_wedge['start_angle'],
                'wedge_end': selected_wedge['end_angle'],
                'target_angle': landing_angle,
                'is_other': False
            }

    def select_token_by_id(self, distribution: Dict, token_id: int) -> Dict:
        """
        Select a token by its token ID (for manual selection).

        Finds the token with the matching ID and returns its information.

        Args:
            distribution: Token distribution from get_next_token_distribution()
            token_id: The token ID to select

        Returns:
            Dictionary containing token information (same format as sample_token_from_distribution)
        """
        tokens = distribution['tokens']
        wedges = self.map_distribution_to_wedges(distribution)

        # Find the token with matching ID
        for i, token in enumerate(tokens):
            if token['token_id'] == token_id:
                selected_wedge = wedges[i]
                # Generate a random target angle within the wedge for animation
                target_angle = np.random.uniform(
                    selected_wedge['start_angle'],
                    selected_wedge['end_angle']
                )

                return {
                    'token': token['token'],
                    'token_id': token['token_id'],
                    'probability': token['probability'],
                    'wedge_start': selected_wedge['start_angle'],
                    'wedge_end': selected_wedge['end_angle'],
                    'target_angle': target_angle,
                    'is_other': False
                }

        # Token ID not found in main tokens, check if it's the "other" token
        if token_id == -1:
            # User selected the "other" wedge
            other_wedge = wedges[-1]
            target_angle = np.random.uniform(
                other_wedge['start_angle'],
                other_wedge['end_angle']
            )
            # Sample from remaining distribution
            return self._sample_from_other(distribution, other_wedge, target_angle)

        raise ValueError(f"Token ID {token_id} not found in distribution")

    def _sample_from_other(self, distribution: Dict, other_wedge: Dict, target_angle: float) -> Dict:
        """
        Sample a token from the remaining distribution when "other" is selected.

        Gets all tokens that were excluded from the main distribution and samples
        one based on their probabilities.

        Args:
            distribution: Token distribution from get_next_token_distribution()
            other_wedge: The "other" wedge information
            target_angle: Target angle for animation

        Returns:
            Dictionary containing token information for the sampled token
        """
        # Get the full probability distribution from the model
        # We need to re-run inference to get probabilities for all tokens
        context = distribution['context']
        input_ids = self.tokenizer.encode(context, return_tensors='pt').to(self.device)

        with torch.no_grad():
            outputs = self.model(input_ids)
            logits = outputs.logits[0, -1, :]
            probabilities = torch.softmax(logits, dim=0)
            probs_np = probabilities.cpu().numpy()

        # Get token IDs that are in the main distribution
        included_token_ids = set(t['token_id'] for t in distribution['tokens'])

        # Get all other token IDs and their probabilities
        other_token_ids = []
        other_probs = []

        for token_id in range(len(probs_np)):
            if token_id not in included_token_ids:
                other_token_ids.append(token_id)
                other_probs.append(probs_np[token_id])

        # Normalize probabilities
        other_probs = np.array(other_probs)
        if other_probs.sum() > 0:
            other_probs = other_probs / other_probs.sum()
        else:
            # Fallback to uniform if all probabilities are zero
            other_probs = np.ones(len(other_probs)) / len(other_probs)

        # Sample from the other tokens
        sampled_idx = np.random.choice(len(other_token_ids), p=other_probs)
        sampled_token_id = other_token_ids[sampled_idx]
        sampled_token = self.tokenizer.decode([sampled_token_id])

        return {
            'token': sampled_token,
            'token_id': int(sampled_token_id),
            'probability': float(probs_np[sampled_token_id]),
            'wedge_start': other_wedge['start_angle'],
            'wedge_end': other_wedge['end_angle'],
            'target_angle': target_angle,
            'is_other': True  # Mark that this came from "other"
        }

    def should_end_generation(
        self,
        token_info: Dict,
        context: str,
        max_length: int = 50
    ) -> bool:
        """
        Determine if text generation should stop.

        Stopping conditions:
        1. EOS (end-of-sequence) token is generated
        2. Context length exceeds max_length tokens

        Args:
            token_info: Information about the most recently generated token
            context: Current context string
            max_length: Maximum number of tokens to generate (default 50)

        Returns:
            True if generation should stop, False otherwise
        """
        # Check if EOS token
        eos_token_id = self.tokenizer.eos_token_id
        if token_info['token_id'] == eos_token_id:
            return True

        # Check context length
        context_tokens = self.tokenizer.encode(context)
        if len(context_tokens) >= max_length:
            return True

        return False
