import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="cli-spectrogram", 
    version="0.2.2",
    author="Caileigh Fitzgerald",
    author_email="cfitzgerald@whoi.edu",
    description="Simple python module that creates spectrograms in the command line",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/caileighf/cli-spectrogram",
    download_url="https://github.com/caileighf/cli-spectrogram/archive/0.2.2.tar.gz",
    install_requires=['numpy', 'pathlib'],
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
