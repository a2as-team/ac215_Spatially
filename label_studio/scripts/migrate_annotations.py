#!/usr/bin/env python3
"""
Script to migrate annotations from one Label Studio project to another.
Matches tasks based on data.project_name and data.file_name.

To get your API key from localhost Label Studio:
1. Open Label Studio in browser (http://localhost:8080)
2. Click on your account icon (top right)
3. Click "Account & Settings"
4. Look for "Access Token" section
5. Copy the token
"""

import requests
import argparse
from typing import List, Dict
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class LabelStudioAnnotationMigrator:
    def __init__(self, base_url: str, api_key: str):
        """
        Initialize the migrator.

        Args:
            base_url: Label Studio base URL (e.g., http://localhost:8080)
            api_key: Label Studio API key
        """
        self.base_url = base_url.rstrip('/')
        self.headers = {
            'Authorization': f'Token {api_key}',
            'Content-Type': 'application/json'
        }

    def get_annotations(self, project_id: int) -> List[Dict]:
        """Get all annotations from a project."""
        url = f"{self.base_url}/api/projects/{project_id}/export?exportType=JSON"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def get_tasks(self, project_id: int) -> List[Dict]:
        """Get all tasks from a project."""
        url = f"{self.base_url}/api/projects/{project_id}/tasks"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def create_annotation(self, task_id: int, annotation_data: Dict) -> Dict:
        """Create an annotation for a task."""
        url = f"{self.base_url}/api/tasks/{task_id}/annotations"

        # Prepare annotation payload
        payload = {
            "result": annotation_data["result"],
            "was_cancelled": annotation_data.get("was_cancelled", False),
            "ground_truth": annotation_data.get("ground_truth", False),
        }

        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()

    def build_task_index(self, tasks: List[Dict]) -> Dict[tuple, Dict]:
        """
        Build an index of tasks by (project_name, file_name) for fast lookup.

        Args:
            tasks: List of tasks from Label Studio

        Returns:
            Dict mapping (project_name, file_name) to task
        """
        index = {}
        for task in tasks:
            data = task.get('data', {})
            project_name = data.get('project_name')
            file_name = data.get('file_name')

            if project_name and file_name:
                key = (project_name, file_name)
                index[key] = task
            else:
                logger.warning(f"Task {task.get('id')} missing project_name or file_name")

        return index

    def migrate_annotations(
        self,
        source_project_id: int,
        target_project_id: int,
        dry_run: bool = False
    ) -> Dict[str, int]:
        """
        Migrate annotations from source project to target project.

        Args:
            source_project_id: Source project ID
            target_project_id: Target project ID
            dry_run: If True, only show what would be migrated without actually doing it

        Returns:
            Dict with statistics about the migration
        """
        logger.info(f"Starting migration from project {source_project_id} to {target_project_id}")

        # Get source annotations
        logger.info("Fetching source annotations...")
        source_annotations = self.get_annotations(source_project_id)
        logger.info(f"Found {len(source_annotations)} annotated tasks in source project")

        # Get target tasks
        logger.info("Fetching target tasks...")
        target_tasks = self.get_tasks(target_project_id)
        logger.info(f"Found {len(target_tasks)} tasks in target project")

        # Build index of target tasks
        logger.info("Building task index...")
        target_task_index = self.build_task_index(target_tasks)

        # Statistics
        stats = {
            'total_source': len(source_annotations),
            'matched': 0,
            'not_matched': 0,
            'migrated': 0,
            'skipped': 0,
            'errors': 0
        }

        not_matched_list = []

        # Process each source annotation
        for source_item in source_annotations:
            # Extract task data
            task_data = source_item.get('data', {})
            project_name = task_data.get('project_name')
            file_name = task_data.get('file_name')

            if not project_name or not file_name:
                logger.warning(f"Source task missing project_name or file_name, skipping")
                stats['skipped'] += 1
                continue

            # Find matching target task
            key = (project_name, file_name)
            target_task = target_task_index.get(key)

            if not target_task:
                logger.warning(f"No matching task found for {project_name} / {file_name}")
                stats['not_matched'] += 1
                not_matched_list.append((project_name, file_name))
                continue

            stats['matched'] += 1

            # Check if task already has annotations
            if target_task.get('is_labeled', False):
                logger.info(f"Task {target_task['id']} ({project_name} / {file_name}) already labeled, skipping")
                stats['skipped'] += 1
                continue

            # Get annotations from source
            annotations = source_item.get('annotations', [])
            if not annotations:
                logger.info(f"No annotations to migrate for {project_name} / {file_name}")
                stats['skipped'] += 1
                continue

            # Migrate each annotation
            for annotation in annotations:
                if dry_run:
                    logger.info(f"[DRY RUN] Would migrate annotation for task {target_task['id']} ({project_name} / {file_name})")
                    stats['migrated'] += 1
                else:
                    try:
                        logger.info(f"Migrating annotation for task {target_task['id']} ({project_name} / {file_name})")
                        self.create_annotation(target_task['id'], annotation)
                        stats['migrated'] += 1
                    except Exception as e:
                        logger.error(f"Error migrating annotation for task {target_task['id']}: {e}")
                        stats['errors'] += 1

        # Print summary
        logger.info("\n" + "="*50)
        logger.info("Migration Summary:")
        logger.info(f"  Total source tasks: {stats['total_source']}")
        logger.info(f"  Matched: {stats['matched']}")
        logger.info(f"  Not matched: {stats['not_matched']}")
        logger.info(f"  Migrated: {stats['migrated']}")
        logger.info(f"  Skipped: {stats['skipped']}")
        logger.info(f"  Errors: {stats['errors']}")

        if not_matched_list:
            logger.info(f"\nNot matched tasks ({len(not_matched_list)}):")
            for project_name, file_name in not_matched_list[:10]:
                logger.info(f"  - {project_name} / {file_name}")
            if len(not_matched_list) > 10:
                logger.info(f"  ... and {len(not_matched_list) - 10} more")

        return stats


def main():
    parser = argparse.ArgumentParser(
        description='Migrate annotations between Label Studio projects',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
To get your API key from localhost Label Studio:
1. Open Label Studio in browser (http://localhost:8080)
2. Click on your account icon (top right)
3. Click "Account & Settings"
4. Look for "Access Token" section
5. Copy the token

You can also set the LABEL_STUDIO_API_KEY environment variable.
        """
    )
    parser.add_argument('--base-url', default='http://localhost:8080', help='Label Studio base URL (default: http://localhost:8080)')
    parser.add_argument('--api-key', help='Label Studio API key (or set LABEL_STUDIO_API_KEY env var)')
    parser.add_argument('--source-project', type=int, required=True, help='Source project ID')
    parser.add_argument('--target-project', type=int, required=True, help='Target project ID')
    parser.add_argument('--dry-run', action='store_true', help='Dry run - show what would be migrated without actually doing it')

    args = parser.parse_args()

    # Get API key from args or environment variable
    api_key = args.api_key or os.environ.get('LABEL_STUDIO_API_KEY')
    if not api_key:
        parser.error("API key required. Provide via --api-key or set LABEL_STUDIO_API_KEY environment variable.\n\n"
                    "To get your API key:\n"
                    "1. Open Label Studio (http://localhost:8080)\n"
                    "2. Click Account icon → Account & Settings\n"
                    "3. Copy the Access Token")

    migrator = LabelStudioAnnotationMigrator(args.base_url, api_key)

    migrator.migrate_annotations(
        source_project_id=args.source_project,
        target_project_id=args.target_project,
        dry_run=args.dry_run
    )

    print("\nMigration completed!")
    if args.dry_run:
        print("This was a DRY RUN. No actual changes were made.")
        print("Run without --dry-run to perform the actual migration.")


if __name__ == '__main__':
    main()
