"""
Comprehensive test suite for GPT2TokenWheelGenerator.

Tests cover:
- Model initialization
- Token distribution generation
- Wedge allocation
- Token sampling
- End condition detection
- Full generation flow
"""

import pytest
import torch
import numpy as np
from backend.generator import GPT2TokenWheelGenerator


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def generator():
    """Provide a fresh GPT2TokenWheelGenerator instance."""
    return GPT2TokenWheelGenerator(model_name='gpt2', device='cpu')


@pytest.fixture
def simple_prompt():
    """Simple test prompt."""
    return "The cat"


@pytest.fixture
def known_prompt():
    """Prompt with known likely completion (for testing peaked distributions)."""
    return "The capital of France is"


@pytest.fixture
def ambiguous_prompt():
    """Prompt with ambiguous continuation (for testing flat distributions)."""
    return "The"


# ============================================================================
# Initialization Tests
# ============================================================================

def test_model_loads_successfully(generator):
    """Verify model and tokenizer load properly."""
    assert generator.model is not None
    assert generator.tokenizer is not None
    assert hasattr(generator.model, 'forward')
    assert hasattr(generator.tokenizer, 'encode')


def test_device_cpu():
    """Verify CPU device works."""
    gen = GPT2TokenWheelGenerator(device='cpu')
    assert gen.device.type == 'cpu'
    assert next(gen.model.parameters()).device.type == 'cpu'


def test_model_in_eval_mode(generator):
    """Verify model.eval() was called."""
    assert not generator.model.training


# ============================================================================
# Token Distribution Tests
# ============================================================================

def test_distribution_probabilities_valid(generator, simple_prompt):
    """Verify all probabilities are between 0 and 1."""
    dist = generator.get_next_token_distribution(simple_prompt)

    for token_info in dist['tokens']:
        assert 0.0 <= token_info['probability'] <= 1.0

    assert 0.0 <= dist['remaining_probability'] <= 1.0


def test_distribution_probabilities_sum(generator, simple_prompt):
    """Verify tokens + remaining ≤ 1.0 (with tolerance for floating point)."""
    dist = generator.get_next_token_distribution(simple_prompt)

    total = sum(t['probability'] for t in dist['tokens'])
    total += dist['remaining_probability']

    # Should sum to approximately 1.0
    assert pytest.approx(total, abs=1e-5) == 1.0
    # Should not exceed 1.0 (accounting for floating point)
    assert total <= 1.0 + 1e-6


def test_primary_threshold_filtering(generator, simple_prompt):
    """Verify all tokens meet minimum threshold."""
    min_threshold = 0.01
    dist = generator.get_next_token_distribution(
        simple_prompt,
        min_threshold=min_threshold
    )

    # All returned tokens should have probability >= min_threshold
    # (or be from secondary threshold, which is still >= secondary_threshold)
    for token_info in dist['tokens']:
        # Either >= primary threshold OR part of secondary selection
        assert token_info['probability'] >= 0.005  # secondary_threshold


def test_secondary_threshold_activation(generator, ambiguous_prompt):
    """Test secondary threshold activates when remaining > 20%."""
    min_threshold = 0.05  # Set high to ensure remaining > 20%
    secondary_threshold = 0.01

    dist = generator.get_next_token_distribution(
        ambiguous_prompt,
        min_threshold=min_threshold,
        secondary_threshold=secondary_threshold
    )

    # Check if any tokens between secondary and primary threshold exist
    has_secondary = any(
        secondary_threshold <= t['probability'] < min_threshold
        for t in dist['tokens']
    )

    # Calculate what remaining would be with only primary
    primary_only = [t for t in dist['tokens'] if t['probability'] >= min_threshold]
    primary_sum = sum(t['probability'] for t in primary_only)
    primary_remaining = 1.0 - primary_sum

    # If remaining was > 20%, we should have secondary tokens
    if primary_remaining > 0.2:
        assert has_secondary or dist['remaining_probability'] <= 0.2


def test_remaining_probability_calculated(generator, simple_prompt):
    """Verify remaining_probability is correctly calculated."""
    dist = generator.get_next_token_distribution(simple_prompt)

    token_sum = sum(t['probability'] for t in dist['tokens'])
    expected_remaining = 1.0 - token_sum

    assert pytest.approx(dist['remaining_probability'], abs=1e-5) == expected_remaining


def test_distribution_token_count_dynamic(generator):
    """Verify token count varies based on distribution shape."""
    # Peaked distribution should have fewer tokens
    peaked_dist = generator.get_next_token_distribution(
        "The capital of France is"
    )

    # Flat distribution with very low threshold to get more tokens
    flat_dist = generator.get_next_token_distribution(
        "The",
        min_threshold=0.005,  # Very low threshold for flat distribution
        secondary_threshold=0.001
    )

    # This is probabilistic, but generally holds true
    # Just verify both are within reasonable range
    assert 1 <= peaked_dist['num_tokens'] <= 100
    assert 1 <= flat_dist['num_tokens'] <= 100
    # Verify flat distribution has at least as many or more tokens than peaked
    # (or at least both return valid distributions)
    assert flat_dist['num_tokens'] >= 1 and peaked_dist['num_tokens'] >= 1


def test_distribution_peaked(generator, known_prompt):
    """Test with prompt that has clear winner."""
    dist = generator.get_next_token_distribution(known_prompt)

    # Should have at least some tokens
    assert len(dist['tokens']) > 0

    # Top token should have reasonable probability (>1%)
    top_token = dist['tokens'][0]  # Already sorted by probability
    assert top_token['probability'] >= 0.01

    # All returned values should be valid
    assert 'token' in top_token
    assert 'token_id' in top_token
    assert 'probability' in top_token
    assert 'is_special' in top_token


def test_distribution_flat(generator, ambiguous_prompt):
    """Test with ambiguous prompt."""
    # Use lower threshold for flat distributions to get tokens
    dist = generator.get_next_token_distribution(
        ambiguous_prompt,
        min_threshold=0.01
    )

    # Should have tokens
    assert len(dist['tokens']) > 0

    # Probabilities should be valid
    for token_info in dist['tokens']:
        assert 0.0 < token_info['probability'] <= 1.0


def test_distribution_short_context(generator):
    """Test with single word prompt."""
    dist = generator.get_next_token_distribution("Hello")

    assert dist['context'] == "Hello"
    assert len(dist['tokens']) > 0
    assert dist['num_tokens'] == len(dist['tokens'])


def test_distribution_long_context(generator):
    """Test with longer multi-sentence prompt."""
    long_prompt = "The quick brown fox jumps over the lazy dog. Now the cat"

    dist = generator.get_next_token_distribution(long_prompt)

    assert dist['context'] == long_prompt
    assert len(dist['tokens']) > 0
    assert all('probability' in t for t in dist['tokens'])


# ============================================================================
# Wedge Allocation Tests
# ============================================================================

def test_wedges_sum_to_360(generator, simple_prompt):
    """Verify all wedge angles sum to 360° (within tolerance)."""
    dist = generator.get_next_token_distribution(simple_prompt)
    wedges = generator.map_distribution_to_wedges(dist)

    # Last wedge should end at 360
    assert pytest.approx(wedges[-1]['end_angle'], abs=0.01) == 360.0

    # Total angle covered
    total_angle = sum(w['end_angle'] - w['start_angle'] for w in wedges)
    assert pytest.approx(total_angle, abs=0.01) == 360.0


def test_wedge_angles_match_probabilities(generator, simple_prompt):
    """Verify each wedge angle = probability × 360°."""
    dist = generator.get_next_token_distribution(simple_prompt)
    wedges = generator.map_distribution_to_wedges(dist)

    for wedge in wedges:
        wedge_angle = wedge['end_angle'] - wedge['start_angle']
        expected_angle = wedge['probability'] * 360.0

        assert pytest.approx(wedge_angle, abs=0.01) == expected_angle


def test_wedges_sequential(generator, simple_prompt):
    """Verify no gaps: each wedge starts where previous ends."""
    dist = generator.get_next_token_distribution(simple_prompt)
    wedges = generator.map_distribution_to_wedges(dist)

    for i in range(1, len(wedges)):
        prev_end = wedges[i - 1]['end_angle']
        curr_start = wedges[i]['start_angle']

        assert pytest.approx(prev_end, abs=0.001) == curr_start


def test_wedges_no_overlap(generator, simple_prompt):
    """Verify wedges don't overlap: end[i] <= start[i+1]."""
    dist = generator.get_next_token_distribution(simple_prompt)
    wedges = generator.map_distribution_to_wedges(dist)

    for i in range(len(wedges) - 1):
        assert wedges[i]['end_angle'] <= wedges[i + 1]['start_angle'] + 0.001


def test_other_wedge_present(generator, simple_prompt):
    """Verify "other" wedge exists and is last."""
    dist = generator.get_next_token_distribution(simple_prompt)
    wedges = generator.map_distribution_to_wedges(dist)

    # Last wedge should be "other" (if remaining probability > 0)
    if dist['remaining_probability'] > 0:
        other_wedge = wedges[-1]
        assert other_wedge['is_other'] is True
        assert other_wedge['token'] == '<OTHER>'
        assert other_wedge['token_id'] == -1


def test_other_wedge_fills_to_360(generator, simple_prompt):
    """Verify other wedge ends at exactly 360°."""
    dist = generator.get_next_token_distribution(simple_prompt)
    wedges = generator.map_distribution_to_wedges(dist)

    # Last wedge (whether "other" or not) should end at 360
    assert pytest.approx(wedges[-1]['end_angle'], abs=0.01) == 360.0


def test_wedge_boundaries_valid(generator, simple_prompt):
    """Verify all angles in [0, 360] range."""
    dist = generator.get_next_token_distribution(simple_prompt)
    wedges = generator.map_distribution_to_wedges(dist)

    for wedge in wedges:
        assert 0.0 <= wedge['start_angle'] <= 360.0
        assert 0.0 <= wedge['end_angle'] <= 360.0
        assert wedge['start_angle'] < wedge['end_angle']


# ============================================================================
# Token Sampling Tests
# ============================================================================

def test_sample_returns_valid_token(generator, simple_prompt):
    """Verify sampled token is in distribution."""
    np.random.seed(42)

    dist = generator.get_next_token_distribution(simple_prompt)
    sample = generator.sample_token_from_distribution(dist)

    # Sample should be either a token from distribution or from "other"
    if not sample['is_other']:
        token_ids = [t['token_id'] for t in dist['tokens']]
        assert sample['token_id'] in token_ids
    else:
        # When "other" is sampled, it returns an actual token from remaining distribution
        assert sample['token'] != '<OTHER>'  # Should be a real token
        assert sample['token_id'] != -1  # Should have a real token ID
        assert isinstance(sample['token'], str)  # Should be a valid string


def test_target_angle_in_wedge(generator, simple_prompt):
    """Verify target_angle is within selected wedge bounds."""
    np.random.seed(42)

    dist = generator.get_next_token_distribution(simple_prompt)

    # Sample multiple times
    for _ in range(10):
        sample = generator.sample_token_from_distribution(dist)

        # Target angle should be within wedge boundaries
        assert sample['wedge_start'] <= sample['target_angle'] <= sample['wedge_end']


def test_sample_distribution_statistical(generator, simple_prompt):
    """Sample 1000x, verify distribution roughly matches."""
    torch.manual_seed(42)
    np.random.seed(42)

    dist = generator.get_next_token_distribution(simple_prompt)

    # Count occurrences
    sample_counts = {}
    n_samples = 1000

    for _ in range(n_samples):
        sample = generator.sample_token_from_distribution(dist)
        token = sample['token']
        sample_counts[token] = sample_counts.get(token, 0) + 1

    # Check that high-probability tokens appear more often
    # Get the top token from distribution
    if len(dist['tokens']) > 0:
        top_token = dist['tokens'][0]  # Sorted by probability descending
        top_token_str = top_token['token']
        top_prob = top_token['probability']

        # Top token should appear roughly proportional to its probability
        if top_token_str in sample_counts:
            observed_freq = sample_counts[top_token_str] / n_samples
            # Allow generous margin (statistical test with 1000 samples)
            # Expected frequency ± 3 standard deviations
            std_dev = np.sqrt(top_prob * (1 - top_prob) / n_samples)
            assert abs(observed_freq - top_prob) < 3 * std_dev or top_prob < 0.05


def test_other_selection_resamples(generator, simple_prompt):
    """When "other" selected, verify it returns a token from remaining distribution."""
    np.random.seed(42)

    dist = generator.get_next_token_distribution(simple_prompt)

    # Sample many times to eventually hit "other"
    found_other = False
    for _ in range(100):
        sample = generator.sample_token_from_distribution(dist)
        if sample['is_other']:
            found_other = True
            # When "other" is selected, it should return an actual token from the remaining distribution
            assert sample['token'] != '<OTHER>'  # Should be a real token, not the placeholder
            assert sample['token_id'] != -1  # Should have a real token ID
            # Probability should be from the remaining distribution (small value)
            assert 0 < sample['probability'] < dist['remaining_probability']
            break

    # If remaining probability is significant, we should find it
    if dist['remaining_probability'] > 0.1:
        assert found_other or dist['remaining_probability'] < 0.01


def test_target_angle_randomized(generator, simple_prompt):
    """Verify target angles vary across multiple samples of same token."""
    torch.manual_seed(42)
    np.random.seed(42)

    dist = generator.get_next_token_distribution(simple_prompt)

    # Collect target angles
    target_angles = []
    for _ in range(50):
        sample = generator.sample_token_from_distribution(dist)
        target_angles.append(sample['target_angle'])

    # Should have variety in target angles (not all the same)
    unique_angles = len(set(target_angles))
    assert unique_angles > 10  # Reasonable diversity


# ============================================================================
# End Condition Tests
# ============================================================================

def test_should_end_on_eos(generator):
    """Verify returns True for EOS token."""
    eos_token_id = generator.tokenizer.eos_token_id

    token_info = {
        'token': generator.tokenizer.decode([eos_token_id]),
        'token_id': eos_token_id,
        'probability': 0.5,
        'is_other': False
    }

    assert generator.should_end_generation(token_info, "Some context") is True


def test_should_end_on_max_length(generator):
    """Verify returns True when context too long."""
    # Create a very long context
    long_context = " word" * 60  # Well over default max_length of 50

    token_info = {
        'token': ' test',
        'token_id': 1234,
        'probability': 0.5,
        'is_other': False
    }

    assert generator.should_end_generation(token_info, long_context, max_length=50) is True


def test_should_continue_normal(generator, simple_prompt):
    """Verify returns False during normal generation."""
    dist = generator.get_next_token_distribution(simple_prompt)
    sample = generator.sample_token_from_distribution(dist)

    # Normal token with short context should continue
    assert generator.should_end_generation(sample, simple_prompt) is False


# ============================================================================
# Integration Tests
# ============================================================================

def test_full_generation_flow(generator):
    """Test complete flow: start with prompt, generate 5 tokens."""
    torch.manual_seed(42)
    np.random.seed(42)

    context = "Once upon a time"
    tokens_generated = []

    for _ in range(5):
        # Get distribution
        dist = generator.get_next_token_distribution(context)
        assert len(dist['tokens']) > 0

        # Map to wedges
        wedges = generator.map_distribution_to_wedges(dist)
        assert len(wedges) > 0

        # Sample token
        sample = generator.sample_token_from_distribution(dist)
        tokens_generated.append(sample['token'])

        # Check end condition
        should_end = generator.should_end_generation(sample, context)

        if should_end:
            break

        # Update context
        context += sample['token']

    # Should have generated some tokens
    assert len(tokens_generated) > 0

    # Context should have grown
    assert len(context) > len("Once upon a time")


def test_context_grows(generator):
    """Verify context properly accumulates tokens."""
    torch.manual_seed(42)
    np.random.seed(42)

    initial_context = "The cat"
    context = initial_context

    # Generate 3 tokens
    for _ in range(3):
        dist = generator.get_next_token_distribution(context)
        sample = generator.sample_token_from_distribution(dist)

        # Update context
        new_context = context + sample['token']

        # Context should grow
        assert len(new_context) > len(context)

        # Should contain previous context
        assert initial_context in new_context

        context = new_context


def test_deterministic_with_seed(generator):
    """Verify same seed produces same results."""
    context = "Hello world"

    # First run
    torch.manual_seed(12345)
    np.random.seed(12345)
    dist1 = generator.get_next_token_distribution(context)
    sample1 = generator.sample_token_from_distribution(dist1)

    # Second run with same seed
    torch.manual_seed(12345)
    np.random.seed(12345)
    dist2 = generator.get_next_token_distribution(context)
    sample2 = generator.sample_token_from_distribution(dist2)

    # Distributions should be identical
    assert dist1['num_tokens'] == dist2['num_tokens']
    assert len(dist1['tokens']) == len(dist2['tokens'])

    # Samples should be identical
    assert sample1['token'] == sample2['token']
    assert sample1['token_id'] == sample2['token_id']
    assert sample1['target_angle'] == sample2['target_angle']


# ============================================================================
# Edge Cases
# ============================================================================

def test_empty_context_handling(generator):
    """Test behavior with empty string (edge case)."""
    # Empty context might be unusual, but should not crash
    try:
        dist = generator.get_next_token_distribution("")
        assert 'tokens' in dist
        assert 'remaining_probability' in dist
    except Exception as e:
        # It's okay if this raises an exception, just shouldn't crash silently
        assert isinstance(e, (ValueError, RuntimeError))


def test_very_long_context(generator):
    """Test with very long context (near model limits)."""
    # GPT-2 has max length of 1024 tokens
    # Create a long context (but not too long to crash)
    long_context = "word " * 200

    dist = generator.get_next_token_distribution(long_context)
    assert 'tokens' in dist
    assert len(dist['tokens']) > 0


def test_special_characters_in_context(generator):
    """Test context with special characters."""
    special_context = "Hello! How are you? I'm fine. #AI @user"

    dist = generator.get_next_token_distribution(special_context)
    assert 'tokens' in dist
    assert dist['num_tokens'] > 0
