from setuptools import setup, find_packages

setup(
    name="musig2-protocol",
    version="0.1.0",
    packages=find_packages(where="lib"),
    package_dir={"": "lib"},
    install_requires=[
        "did-peer-2",
        "aries-askar",
        "didcomm-messaging",
    ],
    python_requires=">=3.8",
) 