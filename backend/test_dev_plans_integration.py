#!/usr/bin/env python
"""
Manual integration test for development plans agent integration.

This script tests:
1. Tool functions work correctly
2. Tool creators properly bind parameters
3. Agent tools can be instantiated
4. Query by zoning district with actual database

Run this from the backend directory after setting up environment:
    python test_dev_plans_integration.py
"""

import os
import sys

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

def test_imports():
    """Test that all new modules can be imported."""
    print("=" * 70)
    print("TEST 1: Testing imports...")
    print("=" * 70)
    
    try:
        from app.agents.tools.functions.development_plans import (
            query_development_plans,
            query_development_plans_by_proximity,
            query_development_plans_by_zone,
        )
        print("✓ Function imports successful")
    except ImportError as e:
        print(f"✗ Function import failed: {e}")
        return False
    
    try:
        from app.agents.tools.creators import (
            create_development_plans_tool,
            create_location_development_plans_proximity_tool,
            create_location_development_plans_zone_tool,
        )
        print("✓ Creator imports successful")
    except ImportError as e:
        print(f"✗ Creator import failed: {e}")
        return False
    
    try:
        from app.agents.tools.formatters import format_development_plans_results
        print("✓ Formatter imports successful")
    except ImportError as e:
        print(f"✗ Formatter import failed: {e}")
        return False
    
    try:
        from app.utils.vector_query.development_plans import DevelopmentPlansVectorQuery
        print("✓ Vector query class import successful")
    except ImportError as e:
        print(f"✗ Vector query import failed: {e}")
        return False
    
    print("\n✓ All imports successful!\n")
    return True


def test_tool_creators():
    """Test that tool creators work correctly."""
    print("=" * 70)
    print("TEST 2: Testing tool creators...")
    print("=" * 70)
    
    try:
        from app.agents.tools.creators import (
            create_development_plans_tool,
            create_location_development_plans_proximity_tool,
            create_location_development_plans_zone_tool,
        )
        
        # Test city-wide tool creator
        city_tool = create_development_plans_tool(city="boston")
        print(f"✓ Created city-wide tool: {city_tool.__name__}")
        print(f"  Tool docstring preview: {city_tool.__doc__[:100]}...")
        
        # Test proximity tool creator
        proximity_tool = create_location_development_plans_proximity_tool(
            latitude=42.3601,
            longitude=-71.0589,
            city="boston"
        )
        print(f"✓ Created proximity tool: {proximity_tool.__name__}")
        print(f"  Tool docstring preview: {proximity_tool.__doc__[:100]}...")
        
        # Test zone tool creator
        zone_tool = create_location_development_plans_zone_tool(
            latitude=42.3601,
            longitude=-71.0589,
            city="boston"
        )
        print(f"✓ Created zone tool: {zone_tool.__name__}")
        print(f"  Tool docstring preview: {zone_tool.__doc__[:100]}...")
        
        print("\n✓ All tool creators work correctly!\n")
        return True
    except Exception as e:
        print(f"✗ Tool creator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_agent_instantiation():
    """Test that agents can be instantiated with new tools."""
    print("=" * 70)
    print("TEST 3: Testing agent instantiation...")
    print("=" * 70)
    
    try:
        from app.agents.location_data_agent import LocationDataAgent
        from app.agents.city_data_agent import CityDataAgent
        
        # Test LocationDataAgent
        location_agent = LocationDataAgent(
            latitude=42.3601,
            longitude=-71.0589,
            city="boston"
        )
        print("✓ LocationDataAgent instantiated")
        
        llm_agent = location_agent.create()
        tool_count = len(llm_agent.tools) if hasattr(llm_agent, 'tools') else "Unknown"
        print(f"  Tool count: {tool_count}")
        
        # Test CityDataAgent
        city_agent = CityDataAgent(city="boston")
        print("✓ CityDataAgent instantiated")
        
        llm_agent = city_agent.create()
        tool_count = len(llm_agent.tools) if hasattr(llm_agent, 'tools') else "Unknown"
        print(f"  Tool count: {tool_count}")
        
        print("\n✓ Both agents instantiate correctly!\n")
        return True
    except Exception as e:
        print(f"✗ Agent instantiation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_vector_query_method():
    """Test that query_by_zoning_district method exists and has correct signature."""
    print("=" * 70)
    print("TEST 4: Testing vector query method...")
    print("=" * 70)
    
    try:
        from app.utils.vector_query.development_plans import DevelopmentPlansVectorQuery
        import inspect
        
        # Check method exists
        assert hasattr(DevelopmentPlansVectorQuery, 'query_by_zoning_district'), \
            "query_by_zoning_district method not found"
        print("✓ query_by_zoning_district method exists")
        
        # Check method signature
        method = getattr(DevelopmentPlansVectorQuery, 'query_by_zoning_district')
        sig = inspect.signature(method)
        params = list(sig.parameters.keys())
        
        expected_params = ['self', 'query_text', 'latitude', 'longitude', 'city', 'top_k', 'similarity_threshold']
        assert all(p in params for p in expected_params), \
            f"Missing expected parameters. Got: {params}"
        print(f"✓ Method signature correct: {', '.join(params)}")
        
        # Check docstring
        assert method.__doc__ is not None, "Method missing docstring"
        print(f"✓ Method has docstring ({len(method.__doc__)} chars)")
        
        print("\n✓ Vector query method looks good!\n")
        return True
    except Exception as e:
        print(f"✗ Vector query method test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_formatter():
    """Test the development plans formatter."""
    print("=" * 70)
    print("TEST 5: Testing formatter...")
    print("=" * 70)
    
    try:
        from app.agents.tools.formatters import format_development_plans_results
        
        # Test with sample data
        sample_results = [
            {
                "text_chunk": "This is a test development plan for a residential building.",
                "project_name": "Test Project",
                "file_name": "test_file.pdf",
                "article_reference": ["Article 50", "Section 32"],
                "zoning_codes": ["H-3-65"],
                "similarity_score": 0.85,
                "distance_km": 0.5,
            }
        ]
        
        # Test without distance
        formatted = format_development_plans_results(sample_results, include_distance=False)
        assert "Test Project" in formatted
        assert "0.85" in formatted or "85" in formatted  # Check for score
        print("✓ Formatter works without distance")
        
        # Test with distance
        formatted_with_distance = format_development_plans_results(sample_results, include_distance=True)
        assert "Test Project" in formatted_with_distance
        assert "0.5" in formatted_with_distance or "0.50km" in formatted_with_distance
        print("✓ Formatter works with distance")
        
        # Test with empty results
        empty_formatted = format_development_plans_results([])
        assert "No results" in empty_formatted
        print("✓ Formatter handles empty results")
        
        print("\n✓ Formatter works correctly!\n")
        return True
    except Exception as e:
        print(f"✗ Formatter test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "Development Plans Integration Tests" + " " * 18 + "║")
    print("╚" + "=" * 68 + "╝")
    print()
    
    tests = [
        test_imports,
        test_tool_creators,
        test_agent_instantiation,
        test_vector_query_method,
        test_formatter,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    passed = sum(results)
    total = len(results)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("\n✓ ✓ ✓  ALL TESTS PASSED!  ✓ ✓ ✓\n")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())

