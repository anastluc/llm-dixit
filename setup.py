from setuptools import setup, find_packages

setup(
    name="dixit_arena",
    version="2.0.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        # API layer
        "fastapi>=0.110.0",
        "uvicorn[standard]>=0.29.0",
        "httpx>=0.27.0",
        "python-dotenv>=1.0.0",
        "pydantic>=2.0.0",
        # Direct provider fallbacks
        "anthropic>=0.25.0",
        "openai>=1.30.0",
        "google-generativeai>=0.7.0",
        "requests>=2.31.0",
        # Firebase storage backend (optional — falls back to local JSON if not installed)
        "firebase-admin>=6.0.0",
    ],
    python_requires=">=3.11",
)
