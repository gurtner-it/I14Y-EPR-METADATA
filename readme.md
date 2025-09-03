## 🎯 What This Does

This toolkit provides two main capabilities:

1. **Data Transformation** (`AD_I14Y_transformator.py`): Converts healthcare code lists from XML formats into I14Y-compliant JSON structures
2. **API Management** (`I14Y_API_handling.py`): Automates the upload, update, and management of concepts and code lists via the I14Y REST API

# AD_I14Y Transformator

A Python script that transforms XML files into JSON format for I14Y interoperability standards, specifically designed for Swiss eHealth systems.

## Overview

This tool converts healthcare code lists from formats into standardized JSON format compatible with I14Y (interoperability) requirements. It handles multilingual content (German, English, French, Italian, Romansh) and maintains proper code system relationships.

## Prerequisites

- Python 3.1+
- Required packages: See requirements.txt

## Installation

1. Clone or download the script files
```bash
git clone https://github.com/ehealthsuisse/I14Y-EPR-METADATA.git
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
DEFAULT_RESPONSIBLE_SHORT_NAME=PGR

DEFAULT_DEPUTY_EMAIL=stefanie.neuenschwander@e-health-suisse.ch
DEFAULT_DEPUTY_SHORT_NAME=SNE

# Publisher information
PUBLISHER_IDENTIFIER=CH_eHealth
PUBLISHER_NAME=eHealth Suisse

# Default values
DEFAULT_VERSION=2.0.2
DEFAULT_PUBLICATION_LEVEL=Internal
DEFAULT_CONCEPT_TYPE=CodeList
DEFAULT_VALUE_TYPE=String
DEFAULT_VALUE_MAX_LENGTH=30

# Period defaults
DEFAULT_PERIOD_START=2024-06-01
DEFAULT_PERIOD_END=2100-06-01
```


# 🖥️ Launching the GUI

This project provides a simple web-based interface for interacting with the scripts.

## 1. Start the Flask Backend

Open a terminal and run:

```bash
python app.py
```

> By default, the backend will run on port `5001`.

## 2. Serve the Frontend

Open another terminal and start a simple HTTP server:

```bash
python -m http.server 8080
```

> The frontend will now be available on port `8080`.

## 3. Access the Application

Open your web browser and navigate to:

```
http://localhost:8080
```

> The GUI will communicate with the backend running on port `5001`.


## Usage via terminal

### Basic Usage

```bash
python AD_I14Y_transformator.py <responsible_key> <deputy_key> <input_folder> <output_folder> <valid_from_date> [options]
```

### Parameters

- `responsible_key`: Key for responsible person (PGR, SNE)
- `deputy_key`: Key for deputy person (PGR, SNE)
- `input_folder`: Path to folder containing XML files to process
- `output_folder`: Path where JSON output files will be saved
- `valid_from_date`: Date from which concept is valid (YYYY-MM-DD format)
- `[options]`: Optional flags

### Options

- `-n`: Create new concept (default: create new version of existing concept)

### Examples

**Process files to create new versions:**
```bash
python AD_I14Y_transformator.py PGR SNE ./AD_VS/XML ./AD_VS/Transformed 2026-06-01
```

**Process files to create new concepts:**
```bash
python AD_I14Y_transformator.py PGR SNE ./AD_VS/XML ./AD_VS/Transformed 2026-06-01 -n
```

## Input File Format

### XML Format
Expected XML structure with `<valueSet>` root containing:
- Value set metadata (name, id)
- Source code systems
- Concept entries with designations

## Output Format

The script generates JSON files in I14Y format containing:
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
├── AD_VS/XML                   # Input XML files
├── AD_VS/Transformed           # Output Json files
```

## Notes

- The script processes files with names matching pattern `VS_<name>_(...)` or `VS <name>_(...)`
- Output files are named `<name>-<i14y-identifier>-transformed.json`
- All dates are set with default validity periods (can be customized in `.env`)


# I14Y API Handling Script

This Python script provides a client interface for interacting with the [i14y API service](https://www.i14y.admin.ch) to manage *concepts* and *codelists* (value sets). It supports automated upload, update, retrieval operations for structured terminology data used in Swiss Electronic Patient Record (EPD).

## 🧰 Features

- **Environment-based configuration** (PROD / ABN)
- **OAuth2 token management** using `client_credentials` grant
- **POST** new concepts and codelist entries
- **DELETE** and update existing codelist entries
- **Batch upload** for concepts and codelists from a directory
- **Error logging** to file for failed API requests

---

## Limitations

- **Deleting locked concetps**: This can only be done via I14Y offical support, not via the API

---

### 2. API Operations

#### Upload Operations
```bash
# Post a single new concept
python I14Y_API_handling.py -pc AD_VS/XML/VS_DocumentEntry.authorSpeciality_(download_2025-02-07T13_10_56).xml

# Post multiple concepts from directory
python I14Y_API_handling.py -pmc AD_VS/XML/

# Post codelist entries to existing concept
python I14Y_API_handling.py -pcl AD_VS/Transformed/DocumentEntry.authorSpeciality_download_2025-02-07T13_10_56_f5c1267f-33b9-4298-810f-13759a67c58c_transformed.json f5c1267f-33b9-4298-810f-13759a67c58c



# Post multiple codelists from directory
python I14Y_API_handling.py -pmcl AD_VS/Transformed
```

#### Management Operations
```bash
# Update codelist entries (delete old + post new)
python I14Y_API_handling.py -ucl AD_VS/Transformed/DocumentEntry.authorSpeciality_download_2025-02-07T13_10_56_f5c1267f-33b9-4298-810f-13759a67c58c_transformed.json f5c1267f-33b9-4298-810f-13759a67c58c

# Delete all codelist entries for a concept
python I14Y_API_handling.py -dcl f5c1267f-33b9-4298-810f-13759a67c58c
```

## 📁 Project Structure

```text
├── I14Y_API_handling.py
├── .env
├── AD_VS/
│   ├── Transformed
│   │   ├── CodeList
│   │   └── Concepts
│   └── XML
└── AF_VS/
    └── api_errors_log.txt  # Error log file (auto-generated)
```

## ⚙️ Prerequisites

- Python 3.1+
- Valid API credentials for I14Y (client ID & secret)
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