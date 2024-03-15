## kskit module

Functionality for cancer screening data pipeline including DICOM image importing and processing.

Initially conceived for french breast cancer screening program during the execution of deep.piste study

## Documentation

kskit documentation can be found at: [https://epiconcept-paris.github.io/kskit/](https://epiconcept-paris.github.io/kskit/)

### Prerequisites

**Ubuntu**

For using `opencv`, you might need to install:
```bash
sudo apt insall ffmpeg libsm6 libxext6  -y
```

For using `pyzbar`:
```bash
sudo apt install zbar-tools
```

### Installation

```bash
poetry install
```

### Installation for contributors

1. Download source code

```bash
git clone https://github.com/Epiconcept-Paris/kskit.git
cd kskit
```

2. Install kskit

```bash
poetry install --dev-dependency
```

3. Launch tests

First method
```bash
poetry shell
pytest
```

Second method
```bash
poetry pytest
```

### Checking installation

Open a python interpreter and try to deidentify a dicom file:
```python
from kskit.dicom.deid_mammogram import deidentify_image_png

deidentify_image_png(
    "/path/to/mammogram.dcm",
    "/path/to/processed/output-folder",
    "output-filename"
)
```
## Tools for developers

### Installation

```bash
poetry install --dev-dependency
```

### Usage

Format your files with `python3 -m autopep8 --in-place file/to/format`

Lint your files with `python3 -m pylint file/to/lint`


### Run Tests

Run all tests
```py
pytest
```

Run a specific test file
```py
pytest test/test_df2dicom.py
```

Run all except OCR tests
```py
pytest --ignore=test/test_ocr_deidentification.py --ignore=test/test_df2dicom
```

Show full error message
```py
pytest test/test_df2dicom.py --showlocals
```

### Calculate Tests Coverage

1. Produce the `.coverage` file
```py
coverage run --omit="*/test*" -m pytest
```

2. Visualize the coverage report in the terminal
```py
coverage report -i
```

3. Produce an HTML report with test coverage

(The report will be available in `htmlcov/index.html` )
```py
coverage html -i
```

### Documentation

Run development server
```py
mkdocs serve
```

Deploy documentation to GitHub Pages
```py
mkdocs gh-deploy
```
