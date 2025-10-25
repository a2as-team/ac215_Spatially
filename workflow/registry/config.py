from pathlib import Path

class RegistryConfig:
    @staticmethod
    def repository_name():
        return "workflow-images"


    @staticmethod
    def images():
        project_root = Path(__file__).parent.parent
        return [
            {
                "name": "data-collector",
                "context": project_root / "data" / "collector",
                "dockerfile": project_root / "data" / "collector" / "Dockerfile"
            },
            {
                "name": "data-processor",
                "context": project_root / "data" / "processor",
                "dockerfile": project_root / "data" / "processor" / "Dockerfile"
            },
        ]