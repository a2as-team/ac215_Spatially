#!/usr/bin/env python3
"""
Run script for Label Studio Development Plans NER Annotation

Prepares PDF data for Label Studio annotation (local setup).
Document types are city-specific and dynamically loaded.

Usage:
    # Prepare all documents for a city
    python label_studio/development_plans/run.py --city boston --doc-type all

    # Filter by city-specific document type
    python label_studio/development_plans/run.py --city boston --doc-type spra
    python label_studio/development_plans/run.py --city boston --doc-type bpda

    # The script will show available doc-types for the selected city

After running this script:
    1. Install Label Studio: pip install label-studio
    2. Start it: label-studio start
    3. Import the generated JSON file in the Label Studio UI
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.smart_arg_parser import SmartArgItem, SmartArgParser
from label_studio.development_plans import (
    DevelopmentPlansLabelStudio,
)


def main():
    # Step 1: Parse city first
    city_schema = {
        "city": SmartArgItem(
            flags=["--city"],
            prompt="The city of data to prepare",
            arg_type=str,
            required=True,
        ),
    }
    city_parser = SmartArgParser(city_schema)
    city_args = city_parser.parse()
    city = city_args.get("city")

    # Step 2: Create service and get city-specific document types
    service = DevelopmentPlansLabelStudio(city=city)
    doc_types = service.get_document_types()

    # Build options string for prompt
    doc_type_options = []
    for key, description in doc_types.items():
        doc_type_options.append(f"{key} ({description})")
    options_str = ", ".join(doc_type_options)

    # Step 3: Parse doc_type with city-specific options shown
    doc_type_schema = {
        "doc_type": SmartArgItem(
            flags=["--doc-type"],
            prompt=f"Select document type for {city}\nOptions: {options_str}",
            arg_type=str,
            required=True,
        ),
    }
    doc_type_parser = SmartArgParser(doc_type_schema)
    doc_type_args = doc_type_parser.parse()
    doc_type = doc_type_args.get("doc_type")

    if not doc_type:
        raise ValueError("doc_type is required")

    # Validate doc_type against city-specific options
    if doc_type not in doc_types:
        print(f"\n❌ Invalid doc_type: '{doc_type}' for city: '{city}'")
        print(f"\n📋 Valid document types for {city}:")
        for key, description in doc_types.items():
            print(f"   • {key}: {description}")
        return 1

    # Handle "all" - create separate files for each document type
    if doc_type == "all":
        print(f"\n🔧 Preparing annotation data for {city}: all document types\n")
        print(f"   Creating separate import files for each document type...\n")

        created_files = []
        total_tasks = 0

        # Get all doc types except "all"
        doc_types_to_process = {k: v for k, v in doc_types.items() if k != "all"}

        for idx, (dt_key, dt_desc) in enumerate(doc_types_to_process.items(), 1):
            print(
                f"[{idx}/{len(doc_types_to_process)}] Processing {dt_key} ({dt_desc})..."
            )

            tasks = service.prepare(doc_type_filter=dt_key)

            if tasks:
                import_file = service.import_file(doc_type=dt_key)
                created_files.append((dt_key, import_file, len(tasks)))
                total_tasks += len(tasks)
                print(f"   ✓ Created {len(tasks)} tasks → {import_file}\n")
            else:
                print(f"   ⚠️  No tasks found for {dt_key}\n")

        print(
            f"\n✅ Successfully prepared {total_tasks} total tasks across {len(created_files)} files"
        )
        print(f"\n📋 Created import files:")
        for dt_key, import_file, task_count in created_files:
            print(f"   • {dt_key}: {import_file} ({task_count} tasks)")

        print(f"\n📋 Next steps:")
        print(
            f"   1. Start Label Studio: docker compose -f docker-compose.dev.yml up label-studio"
        )
        print(f"   2. Open http://localhost:8080")
        print(f"   3. Import each file separately in Label Studio UI")
        print()

    else:
        # Single document type
        doc_type_filter = doc_type

        print(f"\n🔧 Preparing annotation data for {city}: {doc_type}\n")

        tasks = service.prepare(doc_type_filter=doc_type_filter)

        if not tasks:
            print("\n❌ No tasks were created. Check logs above for errors.")
            return 1

        import_file = service.import_file(doc_type=doc_type)

        print(f"\n✅ Successfully prepared {len(tasks)} tasks")
        print(f"   Import file: {import_file}")
        print(f"\n📋 Next steps:")
        print(f"   1. Install Label Studio: pip install label-studio")
        print(f"   2. Start Label Studio: label-studio start")
        print(f"   3. Open http://localhost:8080")
        print(f"   4. Import file: {import_file}")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
