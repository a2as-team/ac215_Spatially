#!/usr/bin/env python3
"""
Run script for Boston Development Plans Parser

This parser creates labeled training data for your zoning relief prediction model.
Uses open source models via Ollama - no API keys needed!

Usage:
    # Default (uses llama3.2)
    python parser/development_plans/run.py

    # Use a different Ollama model
    python parser/development_plans/run.py --model qwen2.5

Prerequisites:
    1. Install Ollama: https://ollama.ai
    2. Pull a model: ollama pull llama3.2
    3. Start Ollama: ollama serve
"""

import os
import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from collector.development_plans.boston import BostonDevelopmentPlansCollector
from parser.development_plans.boston import BostonDevelopmentPlansParser
from utils.smart_arg_parser import SmartArgItem, SmartArgParser


def main():
    schema = {
        "city": SmartArgItem(
            flags=["--city"],
            prompt="The city of data to parse",
            arg_type=str,
            required=True,
        ),
        "model": SmartArgItem(
            flags=["--model"],
            prompt="The model to use",
            arg_type=str,
            required=False,
            default="llama3.2",
        ),
    }
    parser = SmartArgParser(schema)
    args = parser.parse()
    collector = BostonDevelopmentPlansCollector()
    parser = BostonDevelopmentPlansParser(collector, args["model"])
    parser.parse()


if __name__ == "__main__":
    main()
