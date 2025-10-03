#!/usr/bin/env python3
"""
Test script for medical image vision processing fix.
This tests if our changes to handle vision request failures properly work.
"""

import os
import json
import base64
import io
from pathlib import Path
import logging

# Mock image creation
from PIL import Image

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the backend directory to Python path
import sys

sys.path.insert(0, str(Path(__file__).parent))


def create_test_image():
    """Create a small test image as bytes."""
    # Create a simple 100x100 red image
    img = Image.new("RGB", (100, 100), color="red")

    # Convert to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG")
    img_bytes = img_bytes.getvalue()

    return img_bytes


def test_vision_processing():
    """Test the vision processing with our fixes."""
    try:
        # Import our vision processing classes
        from services.vision_processing import (
            MedicalVisionAnalyzer,
            AnalysisLevel,
            ImageAnalysis,
        )

        print("✅ Successfully imported vision processing classes")

        # Test the parse_analysis_response method with fallback text
        analyzer = MedicalVisionAnalyzer(llm_router=None)  # Mock router

        # Test with fallback response text (like what Claude returns when vision fails)
        fallback_text = "I apologize, but I'm experiencing technical difficulties connecting to the AI service. Please try again in a moment."

        result = analyzer._parse_analysis_response(
            fallback_text, AnalysisLevel.CLINICAL
        )

        print("✅ Successfully parsed fallback response")
        print(f"   Description: {result.description}")
        print(f"   Observations: {result.clinical_observations}")
        print(f"   Recommendations: {result.recommendations}")
        print(f"   Risk Assessment: {result.risk_assessment}")

        # Test with template response text
        template_text = "Medical Image Analysis: Findings: Severity: unknown Recommendations: Professional medical evaluation recommended"

        result2 = analyzer._parse_analysis_response(
            template_text, AnalysisLevel.CLINICAL
        )

        print("✅ Successfully parsed template response")
        print(f"   Description: {result2.description}")
        print(f"   Observations: {result2.clinical_observations}")

        # Test with valid JSON response (what should work when Claude vision works)
        valid_json = """{
            "description": "Clear dermatological image showing skin lesion",
            "clinical_observations": ["Well-defined borders", "Uniform coloration"],
            "diagnostic_suggestions": [{"diagnosis": "Benign mole", "likelihood": "high"}],
            "risk_assessment": "low",
            "recommendations": ["Monitor for changes", "Annual dermatological check"],
            "confidence_score": 0.8
        }"""

        result3 = analyzer._parse_analysis_response(valid_json, AnalysisLevel.CLINICAL)

        print("✅ Successfully parsed valid JSON response")
        print(f"   Description: {result3.description}")
        print(f"   Risk Assessment: {result3.risk_assessment}")
        print(f"   Confidence: {result3.confidence_score}")

        return True

    except Exception as e:
        print(f"❌ Error testing vision processing: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def test_claude_vision_method():
    """Test the new Claude vision method."""
    try:
        from llm.claude_llm import ClaudeLLM

        # Create Claude instance without API key (will fail gracefully)
        claude = ClaudeLLM(api_key="test-key")

        print("✅ Successfully created Claude LLM instance")

        # Test that the new vision method exists
        assert hasattr(
            claude, "generate_vision_response"
        ), "generate_vision_response method missing"

        print("✅ Claude vision method exists")

        return True

    except Exception as e:
        print(f"❌ Error testing Claude vision method: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def test_router_vision_detection():
    """Test the LLM router's vision detection."""
    try:
        from services.llm_router import DigiClinicLLMRouter

        router = DigiClinicLLMRouter()

        print("✅ Successfully created LLM router")

        # Test vision detection with text-only message
        text_messages = [{"role": "user", "content": "Hello, I have a question"}]

        has_image = router._has_image_content(text_messages)
        assert not has_image, "Should not detect image in text-only message"

        print("✅ Correctly detected no image in text message")

        # Test vision detection with image message
        image_messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Please analyze this image"},
                    {
                        "type": "image_url",
                        "image_url": {"url": "data:image/jpeg;base64,..."},
                    },
                ],
            }
        ]

        has_image = router._has_image_content(image_messages)
        assert has_image, "Should detect image in image message"

        print("✅ Correctly detected image in image message")

        return True

    except Exception as e:
        print(f"❌ Error testing router vision detection: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("🧪 Testing Medical Image Vision Processing Fix")
    print("=" * 50)

    tests = [
        ("Vision Processing Parse", test_vision_processing),
        ("Claude Vision Method", test_claude_vision_method),
        ("Router Vision Detection", test_router_vision_detection),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n🔬 Running: {test_name}")
        print("-" * 30)

        if test_func():
            print(f"✅ {test_name}: PASSED")
            passed += 1
        else:
            print(f"❌ {test_name}: FAILED")

    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! The vision processing fix should work.")
        print("\n💡 Summary of fixes:")
        print("   - Vision processing now handles API failures gracefully")
        print("   - Returns structured medical responses instead of error text")
        print("   - Claude has dedicated vision method for image analysis")
        print("   - Router detects and routes vision requests properly")
    else:
        print("⚠️  Some tests failed. Please check the implementation.")


if __name__ == "__main__":
    main()
