# fa-fave-downloader
A utility to download your favourites from FurAffinity

[![Build and Test](https://github.com/daxxcat/fa-fave-downloader/actions/workflows/python-package.yml/badge.svg?branch=main)](https://github.com/daxxcat/fa-fave-downloader/actions/workflows/python-package.yml) [![Publish Python Package](https://github.com/daxxcat/fa-fave-downloader/actions/workflows/python-publish.yml/badge.svg)](https://github.com/daxxcat/fa-fave-downloader/actions/workflows/python-publish.yml)


## Installation

### From Source
1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/fa-fave-downloader.git
   cd fa-fave-downloader
   ```

2. Install the package:
   ```bash
   pip install .
   ```

### For Development
```bash
pip install -e .
```

## Development
- Run tests: `python -m pytest`
- Lint code: `flake8 ./src`
- Build: `python -m build`

## Usage
Note you will need python 3.10 or higher to run the tool.

To install the tool from PyPI:
```bash
pip install fa-fave-downloader
```

After installation, run the tool:
```bash
fa-fave-downloader -h

usage: fa-fave-downloader [-h] --username USERNAME [--save-path SAVE_PATH]

FurAffinity favourite downloader

options:
  -h, --help            show this help message and exit
  --username, -u USERNAME
                        REQUIRED: Fur Affinity username to download favorites from
  --save-path, -p SAVE_PATH
                        Directory to save images (default: ./save)
```
