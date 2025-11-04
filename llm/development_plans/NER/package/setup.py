from setuptools import find_packages
from setuptools import setup

REQUIRED_PACKAGES = [
    "wandb==0.15.11",
    "google-cloud-storage>=2.19.0",
    "datasets>=4.2.0",
    "transformers>=4.57.1",
    "accelerate>=1.10.1",
    "seqeval>=1.2.2",
]

setup(
    name="development_plans_ner_trainer",
    version="0.0.1",
    install_requires=REQUIRED_PACKAGES,
    packages=find_packages(),
    description="Development Plans NER Trainer Application"
)