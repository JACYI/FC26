# -*- coding: utf-8 -*-
"""Thin wrapper — delegates to src.login."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.login import main

if __name__ == "__main__":
    main()
