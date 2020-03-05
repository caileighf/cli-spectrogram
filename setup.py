import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="cli-spectrogram", 
    version="0.0.1",
    author="Caileigh Fitzgerald",
    author_email="cfitzgerald@whoi.edu",
    description="Simple python module that creates spectrograms in the command line",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/caileighf/cli-spectrogram",
    install_requires=['numpy==1.13.3', 'pathlib==1.0.1'],
    packages=setuptools.find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console :: Curses",
        "Topic :: Scientific/Engineering :: Visualization",
        "Topic :: Software Development :: User Interfaces",
        "Programming Language :: Python",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires='>=2.7',
    entry_points={
        'console_scripts': [
        'cli_spectrogram = cli_spectrogram.cli_spectrogram:main',
        ],
    },
)
