#!/usr/bin/env python3
"""
Script to migrate annotations from one Label Studio project to another.
Matches tasks based on data.project_name.

Usage:
    source secrets/ac215-spatially-project.env
    python migrate_annotations.py \\
        --source-project 1 \\
        --target-project 2 \\
        --dry-run

The script uses legacy token authentication.
"""

import argparse
from typing import List, Dict
import logging
import os
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class LabelStudioAnnotationMigrator:
    def __init__(self, base_url: str, legacy_token: str):
        """
        Initialize the migrator with legacy token authentication.

        Args:
            base_url: Label Studio base URL (e.g., http://localhost:8080)
            legacy_token: Legacy authentication token
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Token {legacy_token}'
        })
        logger.info("Using legacy token authentication")

    def get_annotations(self, project_id: int) -> List[Dict]:
        """Get all annotations from a project."""
        url = f"{self.base_url}/api/projects/{project_id}/export?exportType=JSON"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def get_tasks(self, project_id: int) -> List[Dict]:
        """Get all tasks from a project."""
        url = f"{self.base_url}/api/projects/{project_id}/tasks?page_size=10000"
        response = self.session.get(url)
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

        response = self.session.post(url, json=payload)
        response.raise_for_status()
        return response.json()

    def build_task_index(self, tasks: List[Dict]) -> Dict[str, Dict]:
        """
        Build an index of tasks by project_name for fast lookup.

        Args:
            tasks: List of tasks from Label Studio

        Returns:
            Dict mapping project_name to task
        """
        index = {}
        for task in tasks:
            data = task.get('data', {})
            project_name = data.get('project_name')

            if project_name:
                index[project_name] = task
            else:
                logger.warning(f"Task {task.get('id')} missing project_name")

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

            if not project_name:
                logger.warning(f"Source task missing project_name, skipping")
                stats['skipped'] += 1
                continue

            # Find matching target task
            target_task = target_task_index.get(project_name)

            if not target_task:
                logger.warning(f"No matching task found for {project_name}")
                stats['not_matched'] += 1
                not_matched_list.append(project_name)
                continue

            stats['matched'] += 1

            # Check if task already has annotations
            if target_task.get('is_labeled', False):
                logger.info(f"Task {target_task['id']} ({project_name}) already labeled, skipping")
                stats['skipped'] += 1
                continue

            # Get annotations from source
            annotations = source_item.get('annotations', [])
            if not annotations:
                logger.info(f"No annotations to migrate for {project_name}")
                stats['skipped'] += 1
                continue

            # Migrate each annotation
            for annotation in annotations:
                if dry_run:
                    logger.info(f"[DRY RUN] Would migrate annotation for task {target_task['id']} ({project_name})")
                    stats['migrated'] += 1
                else:
                    try:
                        logger.info(f"Migrating annotation for task {target_task['id']} ({project_name})")
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
            for project_name in not_matched_list[:10]:
                logger.info(f"  - {project_name}")
            if len(not_matched_list) > 10:
                logger.info(f"  ... and {len(not_matched_list) - 10} more")

        return stats


def main():
    parser = argparse.ArgumentParser(
        description='Migrate annotations between Label Studio projects',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage:
    source secrets/ac215-spatially-project.env
    python migrate_annotations.py --source-project 1 --target-project 2 --dry-run
        """
    )
    parser.add_argument('--base-url', default='http://localhost:8080', help='Label Studio base URL (default: http://localhost:8080)')
    parser.add_argument('--legacy-token', help='Legacy authentication token (or set LABEL_STUDIO_LEGACY_TOKEN env var)')
    parser.add_argument('--source-project', type=int, required=True, help='Source project ID')
    parser.add_argument('--target-project', type=int, required=True, help='Target project ID')
    parser.add_argument('--dry-run', action='store_true', help='Dry run - show what would be migrated without actually doing it')

    args = parser.parse_args()

    # Get legacy token from args or environment variable
    legacy_token = args.legacy_token or os.environ.get('LABEL_STUDIO_LEGACY_TOKEN')

    if not legacy_token:
        parser.error("Legacy token required. Set LABEL_STUDIO_LEGACY_TOKEN environment variable or use --legacy-token.")

    migrator = LabelStudioAnnotationMigrator(args.base_url, legacy_token)

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

"""
source secrets/ac215-spatially-project.env
python label_studio/scripts/migrate_annotations.py \
    --legacy-token $LABEL_STUDIO_LEGACY_TOKEN \
    --source-project 2 \
    --target-project 18 \
    --dry-run
"""