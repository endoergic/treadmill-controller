import os
import sys
from pathlib import Path

os.environ.setdefault("GPIOZERO_PIN_FACTORY", "mock")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
