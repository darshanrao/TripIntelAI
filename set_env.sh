#!/bin/bash

# Instructions:
# 1. Replace the placeholders with your actual API keys
# 2. Run this script with: source set_env.sh

# Set Anthropic API key
export ANTHROPIC_API_KEY="your_anthropic_api_key_here"

# Set Google Places API key
export GOOGLE_PLACES_API_KEY="your_google_places_api_key_here"

# Confirm keys are set
echo "Environment variables set:"
echo "ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:0:5}... (truncated for security)"
echo "GOOGLE_PLACES_API_KEY: ${GOOGLE_PLACES_API_KEY:0:5}... (truncated for security)"

# Instructions for testing
echo ""
echo "Now run your tests with:"
echo "python test_claude.py"
echo "python test_components.py" 