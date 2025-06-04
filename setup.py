from setuptools import setup, find_packages

setup(
    name="musig2-protocols",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "websockets",
        "aiojobs",
        "aries-askar",
        "didcomm-messaging[askar, did-peer]",
        "buidl @ git+https://github.com/buidl-bitcoin/buidl-python@c0b7d57"
    ],
    python_requires=">=3.8",
) 