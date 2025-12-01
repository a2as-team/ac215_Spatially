import os
import subprocess
import tempfile
from pathlib import Path
from config import PackageConfig


def package_and_upload(
    package_name: str,
    package_dir: Path,
    gcs_bucket: str,
    gcs_path: str,
) -> bool:
    """Package trainer code and upload to GCS.

    Args:
        package_name: Name of the package (e.g., "ner-trainer")
        package_dir: Path to the package directory to tar
        gcs_bucket: GCS bucket name
        gcs_path: Path within bucket (e.g., "packages/ner-trainer.tar.gz")

    Returns:
        True if successful, False otherwise
    """
    print(f"\n{'='*80}")
    print(f"Packaging: {package_name}")
    print(f"Source: {package_dir}")
    print(f"Destination: gs://{gcs_bucket}/{gcs_path}")
    print(f"{'='*80}\n")

    try:
        # Verify package directory exists
        if not package_dir.exists():
            raise FileNotFoundError(f"Package directory not found: {package_dir}")

        # Create temporary directory for build artifacts
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            tar_file = temp_path / f"{package_name}.tar"
            tar_gz_file = temp_path / f"{package_name}.tar.gz"

            # Create tar archive
            print(f"Creating tar archive...")
            # We want to tar the CONTENTS of package_dir (not the dir itself)
            # so setup.py/pyproject.toml are at root of archive
            # Use -C to cd into package_dir and tar . (current directory contents)
            subprocess.run(
                [
                    "tar", "cvf", str(tar_file),
                    "-C", str(package_dir),
                    "."
                ],
                check=True,
                capture_output=True  # Suppress verbose tar output
            )
            print(f"Created: {tar_file.name}")

            # Compress with gzip
            print(f"Compressing with gzip...")
            subprocess.run(["gzip", str(tar_file)], check=True)
            print(f"Compressed: {tar_gz_file.name}")

            # Upload to GCS
            gcs_uri = f"gs://{gcs_bucket}/{gcs_path}"
            print(f"\nUploading to GCS...")
            subprocess.run(
                ["gsutil", "cp", str(tar_gz_file), gcs_uri],
                check=True
            )
            print(f"Successfully uploaded: {gcs_uri}")

        return True

    except subprocess.CalledProcessError as e:
        print(f"Error packaging/uploading {package_name}: {e}")
        return False
    except Exception as e:
        print(f"Error processing {package_name}: {e}")
        return False


def publish_trainer_packages(
    packages: list[str] | None = None,
) -> bool:
    """Publish trainer packages to GCS.

    Args:
        packages: List of specific package names to publish. If None, publishes all.

    Returns:
        True if all packages succeeded, False otherwise
    """
    # Get all package configurations
    all_configs = PackageConfig.packages()

    # Filter to specific packages if requested
    if packages:
        configs_to_build = [c for c in all_configs if c["name"] in packages]
        if not configs_to_build:
            raise ValueError(
                f"No matching packages found. Available: {[c['name'] for c in all_configs]}"
            )
    else:
        configs_to_build = all_configs

    # Package and upload each trainer
    results = []
    for config in configs_to_build:
        success = package_and_upload(
            package_name=config["name"],
            package_dir=config["package_dir"],
            gcs_bucket=config["bucket"],
            gcs_path=config["gcs_path"],
        )
        results.append((config["name"], success))

    # Print summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    for name, success in results:
        status = "SUCCESS" if success else "FAILED"
        print(f"{name:40} {status}")
    print(f"{'='*80}\n")

    # Return success if all packages succeeded
    return all(success for _, success in results)
