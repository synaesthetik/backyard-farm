#!/usr/bin/env python3
"""CLI entry point for synthetic data generation (D-02).

Usage: python scripts/generate_synthetic_data.py [--weeks 6] [--zones zone-01,zone-02]
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'hub', 'bridge'))

from inference.synthetic.generate_synthetic_data import main
import asyncio

asyncio.run(main())
