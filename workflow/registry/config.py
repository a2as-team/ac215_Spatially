from pathlib import Path

class RegistryConfig:
    @staticmethod
    def repository_name():
        return "workflow-images"

    @staticmethod
    def platform():
        """Platform for Docker builds (Vertex AI uses linux/amd64)"""
        return "linux/amd64"

    @staticmethod
    def data_collector_image(gcp_region: str, gcp_project: str):
        project_root = Path(__file__).parent.parent
        return {
            "name": "data-collector",
            "context": project_root / "data" / "collector",
            "dockerfile": project_root / "data" / "collector" / "Dockerfile",
            "image_uri": f"{gcp_region}-docker.pkg.dev/{gcp_project}/{RegistryConfig.repository_name()}/data-collector:latest",
            "platform": RegistryConfig.platform()
        }

    @staticmethod
    def data_processor_image(gcp_region: str, gcp_project: str):
        project_root = Path(__file__).parent.parent
        return {
            "name": "data-processor",
            "context": project_root / "data" / "processor",
            "dockerfile": project_root / "data" / "processor" / "Dockerfile",
            "image_uri": f"{gcp_region}-docker.pkg.dev/{gcp_project}/{RegistryConfig.repository_name()}/data-processor:latest",
            "platform": RegistryConfig.platform()
        }


    @staticmethod
    def images(gcp_region: str, gcp_project: str):
        return [
            RegistryConfig.data_collector_image(gcp_region, gcp_project),
            RegistryConfig.data_processor_image(gcp_region, gcp_project),
        ]