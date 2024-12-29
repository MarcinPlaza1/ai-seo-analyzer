from setuptools import setup, find_packages

setup(
    name="seo-mvp",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pydantic>=2.6.1,<3.0.0",
        line.strip()
        for line in open("requirements.txt")
        if line.strip() and not line.startswith("#")
    ],
    python_requires='>=3.10,<3.11',
) 