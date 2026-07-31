#!/usr/bin/env python3
"""Entry script for the hello-skill demo.

Proves Level-3 script execution: the harness only runs this when a skill is
selected and an executor is told to run it.
"""
import sys
from datetime import datetime

name = sys.argv[1] if len(sys.argv) > 1 else "world"
now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
print(f"Hello, {name}! (from hello-skill)")
print(f"timestamp = {now}")
print(f"python    = {sys.version.split()[0]}")
