#!/usr/bin/env python3
"""
Test script for new analysis types (no legacy).
"""

import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from app.api.schemas.analysis import AnalysisConfig, AnalysisTypes


def test_new_analysis_types():
    """Test that new analysis types work correctly."""
    print("🧪 Testing New Analysis Types")
    print("=" * 40)
    
    # Test 1: Comprehensive analysis
    config = AnalysisConfig()
    analysis_type = config.get_analysis_type()
    print(f"1. Default config: {analysis_type}")
    assert analysis_type == AnalysisTypes.COMPREHENSIVE
    print("   ✅ Comprehensive analysis works")
    
    # Test 2: Ball only
    config = AnalysisConfig(
        include_ball_detection=True,
        include_racket_detection=False,
        include_pose_detection=False
    )
    analysis_type = config.get_analysis_type()
    print(f"2. Ball only: {analysis_type}")
    assert analysis_type == AnalysisTypes.BALL_ONLY
    print("   ✅ Ball only works")
    
    # Test 3: Racket only
    config = AnalysisConfig(
        include_ball_detection=False,
        include_racket_detection=True,
        include_pose_detection=False
    )
    analysis_type = config.get_analysis_type()
    print(f"3. Racket only: {analysis_type}")
    assert analysis_type == AnalysisTypes.RACKET_ONLY
    print("   ✅ Racket only works")
    
    # Test 4: Pose only
    config = AnalysisConfig(
        include_ball_detection=False,
        include_racket_detection=False,
        include_pose_detection=True
    )
    analysis_type = config.get_analysis_type()
    print(f"4. Pose only: {analysis_type}")
    assert analysis_type == AnalysisTypes.POSE_ONLY
    print("   ✅ Pose only works")
    
    # Test 5: Custom (ball + racket)
    config = AnalysisConfig(
        include_ball_detection=True,
        include_racket_detection=True,
        include_pose_detection=False
    )
    analysis_type = config.get_analysis_type()
    print(f"5. Custom (ball + racket): {analysis_type}")
    assert analysis_type == AnalysisTypes.CUSTOM
    print("   ✅ Custom combination works")
    
    # Test 6: Verify no legacy types exist
    print("\n6. Checking for legacy types...")
    legacy_types = ["ball_tracking", "pose_detection"]
    for legacy_type in legacy_types:
        if hasattr(AnalysisTypes, legacy_type.upper()):
            print(f"   ❌ Legacy type {legacy_type} still exists!")
            return False
        else:
            print(f"   ✅ Legacy type {legacy_type} removed")
    
    print("\n🎉 All new analysis types work correctly!")
    print("📋 Summary:")
    print("  ✅ COMPREHENSIVE (all components)")
    print("  ✅ BALL_ONLY (ball detection only)")
    print("  ✅ RACKET_ONLY (racket detection only)")
    print("  ✅ POSE_ONLY (pose detection only)")
    print("  ✅ CUSTOM (mixed combinations)")
    print("  ✅ Legacy types removed")
    
    return True


if __name__ == "__main__":
    success = test_new_analysis_types()
    sys.exit(0 if success else 1)
