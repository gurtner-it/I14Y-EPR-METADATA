## 🎯 What This Does

This toolkit provides two main capabilities:

1. **Data Transformation** (`AD_I14Y_transformator.py`): Converts healthcare code lists from CSV/XML formats into i14y-compliant JSON structures
2. **API Management** (`I14Y_API_handling.py`): Automates the upload, update, and management of concepts and code lists via the i14y REST API

# AD_I14Y Transformator

A Python script that transforms CSV and XML files (XML is recommended) into JSON format for i14y interoperability standards, specifically designed for Swiss eHealth systems.

## Overview

This tool converts healthcare code lists from CSV or XML formats (XML is recommended) into standardized JSON format compatible with i14y (interoperability) requirements. It handles multilingual content (German, English, French, Italian, Romansh) and maintains proper code system relationships.

## Features

- **Multi-format support**: Processes both CSV and XML input files (XML is recommended)
- **Multilingual**: Supports 5 languages (de-CH, en-US, fr-CH, it-CH, rm-CH)
- **Flexible output**: Can create new concepts or update existing ones
- **Batch processing**: Processes entire folders of files
- **Configurable**: Uses environment variables for sensitive data

## Prerequisites

- Python 3.1+
- Required packages: See requirements.txt

## Installation

1. Clone or download the script files
```bash
git clone https://github.com/PeroGrgic/EPD_Metadata.git
cd EPD_Metadata
```
2. Create virtual environement
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install required dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the same directory (see Configuration section)

## Configuration

Create a `.env` file with the following variables:

```env
# I14Y_API_handling.py Stuff

#API_MODE=PROD
API_MODE=ABN

# PROD ID & Secret
PROD_CLIENT_ID=i14y_prod_ehealth_epd
PROD_CLIENT_SECRET=your_secret
PROD_TOKEN_URL=https://identity.bit.admin.ch/realms/bfs-sis-p/protocol/openid-connect/token
PROD_BASE_API_URL=https://api.i14y.admin.ch/api/partner/v1

# ABN ID & Secret
ABN_CLIENT_ID=i14y_abn_ehealth_epd
ABN_CLIENT_SECRET=your_secret
ABN_TOKEN_URL=https://identity-a.bit.admin.ch/realms/bfs-sis-a/protocol/openid-connect/token
ABN_BASE_API_URL=https://api-a.i14y.admin.ch/api/partner/v1

# Logging
log_level=INFO




# AD_I14Y_transformator.py Stuff

# Default responsible persons
DEFAULT_RESPONSIBLE_EMAIL=pero.grgic@e-health-suisse.ch
DEFAULT_DEPUTY_EMAIL=stefanie.neuenschwander@e-health-suisse.ch

# Publisher information
PUBLISHER_IDENTIFIER=CH_eHealth
PUBLISHER_NAME=eHealth Suisse

# Default values
DEFAULT_VERSION=2.0.0
DEFAULT_PUBLICATION_LEVEL=Internal
DEFAULT_CONCEPT_TYPE=CodeList
DEFAULT_VALUE_TYPE=String
DEFAULT_VALUE_MAX_LENGTH=30

# Period defaults
DEFAULT_PERIOD_START=2024-06-01
DEFAULT_PERIOD_END=2100-06-01
```

## Usage

### Basic Usage

```bash
python AD_I14Y_transformator.py <responsible_key> <deputy_key> <input_folder> <output_folder> <valid_from_date> [options]
```

### Parameters

- `responsible_key`: Key for responsible person (PGR, SNE)
- `deputy_key`: Key for deputy person (PGR, SNE)
- `input_folder`: Path to folder containing CSV/XML files to process (XML is recommended)
- `output_folder`: Path where JSON output files will be saved
- `valid_from_date`: Date from which concept is valid (YYYY-MM-DD format)
- `[options]`: Optional flags

### Options

- `-n`: Create new concept (default: create new version of existing concept)

### Examples

**Process files to create new versions:**
```bash
python AD_I14Y_transformator.py PGR SNE ./AD_VS/CSV ./AD_VS/Transformed 2024-12-01
```

**Process files to create new concepts:**
```bash
python AD_I14Y_transformator.py PGR SNE ./AD_VS/CSV ./AD_VS/Transformed 2024-12-01 -n
```

## Input File Formats

### CSV Format
- First row: Contains Value Set name and identifier
- Second row: Column headers with language codes
- Data rows: Code entries with multilingual labels

Example CSV structure:
```
Value Set ExampleSet - 1.0.0
Code,System,de-CH preferred,en-US preferred,fr-CH preferred,...
001,SYSTEM1,German Label,English Label,French Label,...
```

### XML Format
Expected XML structure with `<valueSet>` root containing:
- Value set metadata (name, id)
- Source code systems
- Concept entries with designations

## Output Format

The script generates JSON files in i14y format containing:
- Concept metadata (name, description, identifiers)
- Code list entries with multilingual names
- Annotations (code systems, periods, designations)
- Publisher and responsible person information

## Supported Code Lists

The script includes mappings for various healthcare code lists:
- Document types and classes
- Healthcare facility types
- Professional roles and specializations
- Audit trail event types
- And many more...

## File Structure

```
project/
├── AD_I14Y_transformator.py    # Main script
├── .env                        # Configuration file
├── README.md                   # This documentation
├── AD_VS/CSV                   # Input CSV files
├── AD_VS/XML                   # Input XML files
├── AD_VS/Transformed           # Input CSV/XML files
```

## Notes

- The script processes files with names matching pattern `VS_<name>_(...)` or `VS <name>_(...)`
- Output files are named `<name>_transformed.json`
- All dates are set with default validity periods (can be customized in `.env`)


# I14Y API Handling Script

This Python script provides a client interface for interacting with the [i14y API service](https://www.i14y.admin.ch) to manage *concepts* and *codelists* (value sets). It supports automated upload, update, retrieval, and deletion operations for structured terminology data used in healthcare contexts such as the Swiss Electronic Patient Record (EPR).

## 🧰 Features

- **Environment-based configuration** (PROD / TEST)
- **OAuth2 token management** using `client_credentials` grant
- **POST** new concepts and codelist entries
- **DELETE** and update existing codelist entries
- **Batch upload** for concepts and codelists from a directory
- **Error logging** to file for failed API requests

---

### 2. API Operations

#### Upload Operations
```bash
# Post a single new concept
python I14Y_API_handling.py -pc path/to/concept.json

# Post multiple concepts from directory
python I14Y_API_handling.py -pmc path/to/concepts/directory

# Post codelist entries to existing concept
python I14Y_API_handling.py -pcl path/to/codelist.json concept_id

# Post multiple codelists from directory
python I14Y_API_handling.py -pmcl path/to/codelists/directory
```

#### Management Operations
```bash
# Update codelist entries (delete old + post new)
python I14Y_API_handling.py -ucl path/to/codelist.json concept_id

# Delete all codelist entries for a concept
python I14Y_API_handling.py -dcl concept_id
```

## 📁 Project Structure

```text
├── I14Y_API_handling.py
├── .env
├── AD_VS/
│   ├── CSV
│   ├── Transformed
│   │   ├── CodeList
│   │   └── Concepts
│   └── XML
└── AF_VS/
    └── api_errors_log.txt  # Error log file (auto-generated)
```

## ⚙️ Prerequisites

- Python 3.1+
- Valid API credentials for i14y (client ID, secret, etc.)
- `.env` file with required variables
- JSON files to upload (transformed value sets or concept definitions)

---

## 🔐 .env Configuration

Create a `.env` file in the root directory with the following structure:

```env
# I14Y_API_handling.py Stuff

#API_MODE=PROD
API_MODE=ABN

# PROD ID & Secret
PROD_CLIENT_ID=i14y_prod_ehealth_epd
PROD_CLIENT_SECRET=your_secret
PROD_TOKEN_URL=https://identity.bit.admin.ch/realms/bfs-sis-p/protocol/openid-connect/token
PROD_BASE_API_URL=https://api.i14y.admin.ch/api/partner/v1

# ABN ID & Secret
ABN_CLIENT_ID=i14y_abn_ehealth_epd
ABN_CLIENT_SECRET=your_secret
ABN_TOKEN_URL=https://identity-a.bit.admin.ch/realms/bfs-sis-a/protocol/openid-connect/token
ABN_BASE_API_URL=https://api-a.i14y.admin.ch/api/partner/v1

# Logging
log_level=INFO