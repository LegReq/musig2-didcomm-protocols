from setuptools import setup, find_packages

setup(
    name="musig2-protocols",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "did-peer-2",
        "aries-askar",
        "didcomm-messaging",
    ],
    python_requires=">=3.8",
) 