from setuptools import setup, find_packages

setup(
    name="rtabmap_eval",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "evo>=1.30.0",
        "pyyaml",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "rtabmap-eval=rtabmap_eval.__main__:main",
        ],
    },
)
