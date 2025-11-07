import os
import subprocess
from pathlib import Path
from .config import RegistryConfig


def build_and_push_to_gcp(
    image_name: str,
    context_path: Path,
    dockerfile_path: Path,
    gcp_project: str,
    gcp_region: str,
    repository_name: str,
    platform: str = "linux/amd64",
    tag: str = "latest",
    cleanup_after_push: bool = False,
):
    """Build and push a Docker image to GCP Artifact Registry.

    Args:
        image_name: Name of the Docker image
        context_path: Path to the build context
        dockerfile_path: Path to the Dockerfile
        gcp_project: GCP project ID
        gcp_region: GCP region
        repository_name: Name of the Artifact Registry repository
        platform: Target platform (default: linux/amd64)
        tag: Image tag (default: latest)
        cleanup_after_push: Remove local image after successful push
    """

    # Construct the full image URI
    image_uri = f"{gcp_region}-docker.pkg.dev/{gcp_project}/{repository_name}/{image_name}:{tag}"

    print(f"\n{'='*80}")
    print(f"Building and pushing: {image_name}")
    print(f"Context: {context_path}")
    print(f"Dockerfile: {dockerfile_path}")
    print(f"Platform: {platform}")
    print(f"Destination: {image_uri}")
    print(f"{'='*80}\n")

    try:
        # Build the image for specified platform
        print(f"Building image: {image_name}...")
        build_cmd = [
            "docker", "build",
            "--platform", platform,
            "-t", image_uri,
            "-f", str(dockerfile_path),
            str(context_path)
        ]
        subprocess.run(build_cmd, check=True)
        print(f"Successfully built: {image_uri}")

        # Configure docker to use gcloud as credential helper
        print(f"\nConfiguring Docker authentication for GCP...")
        auth_cmd = ["gcloud", "auth", "configure-docker", f"{gcp_region}-docker.pkg.dev", "--quiet"]
        subprocess.run(auth_cmd, check=True)

        # Push the image
        print(f"\nPushing image: {image_uri}...")
        push_cmd = ["docker", "push", image_uri]
        subprocess.run(push_cmd, check=True)
        print(f"Successfully pushed: {image_uri}")

        # Clean up local image if requested
        if cleanup_after_push:
            print(f"\nCleaning up local image: {image_uri}...")
            cleanup_cmd = ["docker", "rmi", image_uri]
            subprocess.run(cleanup_cmd, check=True)
            print(f"Successfully removed local image: {image_uri}")

        return True

    except subprocess.CalledProcessError as e:
        print(f"Error building/pushing {image_name}: {e}")
        return False


def publish_local_docker_images(
    to_where: str = "gcp",
    images: list[str] | None = None,
    tag: str = "latest",
    cleanup_after_push: bool = False,
):
    """
    Publish local Docker images to a container registry.

    Args:
        to_where: Destination registry ("gcp" or "dockerhub")
        images: List of specific image names to publish. If None, publishes all images.
        tag: Tag to use for the images (default: "latest")
        cleanup_after_push: Remove local images after successful push to save disk space
    """
    if to_where == "gcp":
        # Get required environment variables
        try:
            gcp_project = os.environ["GCP_PROJECT"]
            gcp_region = os.environ.get("GCP_REGION", "us-central1")
        except KeyError as e:
            raise ValueError(f"Required environment variable not set: {e}")

        # Get configuration from RegistryConfig
        repository_name = RegistryConfig.repository_name()
        all_configs = RegistryConfig.images(gcp_region, gcp_project)

        # Filter to specific images if requested
        if images:
            configs_to_build = [c for c in all_configs if c["name"] in images]
            if not configs_to_build:
                raise ValueError(f"No matching images found. Available: {[c['name'] for c in all_configs]}")
        else:
            configs_to_build = all_configs

        # Build and push each image
        results = []
        for config in configs_to_build:
            success = build_and_push_to_gcp(
                image_name=config["name"],
                context_path=config["context"],
                dockerfile_path=config["dockerfile"],
                gcp_project=gcp_project,
                gcp_region=gcp_region,
                repository_name=repository_name,
                platform=config["platform"],
                tag=tag,
                cleanup_after_push=cleanup_after_push,
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

        # Return success if all images succeeded
        return all(success for _, success in results)

    elif to_where == "dockerhub":
        raise NotImplementedError("Dockerhub is not implemented yet")
    else:
        raise ValueError(f"Invalid value for to_where: {to_where}")