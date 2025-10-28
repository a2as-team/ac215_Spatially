from pipelines import BaseComponent
from kfp import dsl
from registry.config import RegistryConfig


class DevelopmentPlansNERTrainerComponent(BaseComponent):
    """
    Component for fine-tuning NER models on development plans data.

    This component trains on aggregated development plans data from all cities
    stored in GCS. It is model-agnostic and can work with any transformer model:
    - BERT variants (legal-bert, bert-base, etc.)
    - RoBERTa, DistilBERT, ALBERT, etc.

    Examples:
        # Legal BERT (default)
        trainer = DevelopmentPlansNERTrainerComponent(
            model_name="nlpaueb/legal-bert-base-uncased"
        )

        # RoBERTa with more epochs
        trainer = DevelopmentPlansNERTrainerComponent(
            model_name="roberta-base",
            epochs=5
        )

        # DistilBERT for faster training
        trainer = DevelopmentPlansNERTrainerComponent(
            model_name="distilbert-base-uncased",
            batch_size=8
        )
    """

    def __init__(
        self,
        model_name: str = "nlpaueb/legal-bert-base-uncased",
        batch_size: int = 4,
        epochs: int = 3,
        learning_rate: float = 2e-5,
        gradient_accumulation_steps: int = 4,
        accelerator_type: str = "NVIDIA_TESLA_T4",
        accelerator_count: int = 1,
        cpu_limit: str = "4",
        memory_limit: str = "16G",
    ):
        """
        Initialize development plans NER trainer component.

        Args:
            model_name: HuggingFace model name (e.g., "nlpaueb/legal-bert-base-uncased", "roberta-base")
            batch_size: Training batch size per device
            epochs: Number of training epochs
            learning_rate: Learning rate for optimizer
            gradient_accumulation_steps: Gradient accumulation steps (effective batch = batch_size * this)
            accelerator_type: GPU type (e.g., "NVIDIA_TESLA_T4", "NVIDIA_TESLA_V100")
            accelerator_count: Number of GPUs
            cpu_limit: CPU limit for the container
            memory_limit: Memory limit for the container
        """
        super().__init__()
        self.model_name = model_name
        self.batch_size = batch_size
        self.epochs = epochs
        self.learning_rate = learning_rate
        self.gradient_accumulation_steps = gradient_accumulation_steps
        self.accelerator_type = accelerator_type
        self.accelerator_count = accelerator_count
        self.cpu_limit = cpu_limit
        self.memory_limit = memory_limit

    def get_component_name(self):
        """Return the component name"""
        # Include model type for tracking different experiments
        model_short = self.model_name.split("/")[-1]
        return f"development-plans-ner-{model_short}"

    def get_component(self):
        """Return the KFP component for development plans NER training"""
        gcp_region = self.GCP_REGION
        gcp_project = self.GCP_PROJECT

        @dsl.container_component
        def development_plans_ner_trainer_component():
            # Build the training command with parameters
            cmd = (
                f"export GCS_BUCKET_NAME={self.GCS_BUCKET_NAME} && "
                f"export GCP_PROJECT={gcp_project} && "
                f"python /app/run.py "
                f"--batch-size {self.batch_size} "
                f"--epochs {self.epochs} "
                f"--learning-rate {self.learning_rate} "
                f"--gradient-accumulation-steps {self.gradient_accumulation_steps} "
                f"--model-name '{self.model_name}'"
            )

            container_spec = dsl.ContainerSpec(
                image=RegistryConfig.ner_trainer_image(gcp_region, gcp_project)["image_uri"],
                command=["sh", "-c", cmd],
            )
            return container_spec

        return development_plans_ner_trainer_component

    def create_pipeline(self):
        """Create a pipeline for development plans NER training with configurable resources"""
        component_name = self.get_component_name()
        component = self.get_component()

        @dsl.pipeline(name=f"{component_name}-pipeline")
        def development_plans_ner_training_pipeline():
            task = (
                component()
                .set_display_name(component_name)
                .set_cpu_limit(self.cpu_limit)
                .set_memory_limit(self.memory_limit)
            )

            # Add GPU accelerator if specified
            if self.accelerator_type and self.accelerator_count > 0:
                task = task.set_accelerator_type(self.accelerator_type)
                task = task.set_accelerator_limit(self.accelerator_count)

        return development_plans_ner_training_pipeline
