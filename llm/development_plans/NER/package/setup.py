from setuptools import find_packages
from setuptools import setup

REQUIRED_PACKAGES = [
    "wandb==0.15.11",
    "google-cloud-storage>=2.19.0",
    "datasets>=2.14.0,<3.0.0",
    "transformers>=4.36.0,<4.40.0",
    "accelerate>=0.25.0,<1.0.0",
    "seqeval>=1.2.2",
]

setup(
    name="development_plans_ner_trainer",
    version="0.0.1",
    install_requires=REQUIRED_PACKAGES,
    packages=find_packages(),
    description="Development Plans NER Trainer Application"
)