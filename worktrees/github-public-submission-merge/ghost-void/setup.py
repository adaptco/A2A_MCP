from setuptools import setup, find_packages

setup(
    name="a2a_mcp",
    version="1.1.0",
    packages=find_packages(),
    install_requires=[
        "httpx",
        "asyncio",
        "sqlalchemy",
        "psycopg2-binary",
        "pydantic",
        "pytest",
        "pytest-asyncio"
    ],
    author="Antigravity",
    description="Agentic Runtime Middleware for CI/CD and MLOps",
    python_requires=">=3.8",
)
