#!/usr/bin/env python3
"""
Script to download YOLO models for the tennis coach application.
This is optional - models will be downloaded automatically when needed.
"""

import logging
import sys
from pathlib import Path

# Add the app directory to the path so we can import from it
sys.path.insert(0, str(Path(__file__).parent.parent))


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def download_models() -> None:
    """Download YOLO models that will be used by the application."""
    try:
        from ultralytics import YOLO

        # Create ml_models directory if it doesn't exist
        ml_models_dir = Path(__file__).parent / "ml_models"
        ml_models_dir.mkdir(exist_ok=True)

        models_to_download = [
            ("ml_models/yolov8n.pt", "nano model - faster, smaller"),
            ("ml_models/yolov8s.pt", "small model - better accuracy"),
        ]

        logger.info("Starting YOLO model downloads...")

        for model_path, description in models_to_download:
            logger.info(f"Downloading {model_path} ({description})...")
            try:
                # This will download the model if it doesn't exist locally
                YOLO(model_path)
                logger.info(f"✅ Successfully downloaded {model_path}")
            except (OSError, RuntimeError, ImportError) as e:
                logger.error(f"❌ Failed to download {model_path}: {e}")

        logger.info("Model download process completed!")
        logger.info(
            "Note: Models will be downloaded automatically when needed if not present."
        )

    except ImportError:
        logger.error(
            "❌ Ultralytics not installed. Please install it with: pip install ultralytics"
        )
        sys.exit(1)


if __name__ == "__main__":
    download_models()
