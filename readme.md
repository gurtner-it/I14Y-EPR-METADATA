# AD_I14Y Transformator

A Python script that transforms CSV and XML files into JSON format for i14y interoperability standards, specifically designed for Swiss eHealth systems.

## Overview

This tool converts healthcare code lists from CSV or XML formats into standardized JSON format compatible with i14y (interoperability) requirements. It handles multilingual content (German, English, French, Italian, Romansh) and maintains proper code system relationships.

## Features

- **Multi-format support**: Processes both CSV and XML input files
- **Multilingual**: Supports 5 languages (de-CH, en-US, fr-CH, it-CH, rm-CH)
- **Flexible output**: Can create new concepts or update existing ones
- **Batch processing**: Processes entire folders of files
- **Configurable**: Uses environment variables for sensitive data

## Prerequisites

- Python 3.6+
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
source .venv/bin/activate
```

3. Install required dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the same directory (see Configuration section)

## Configuration

Create a `.env` file with the following variables:

```env
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
- `input_folder`: Path to folder containing CSV/XML files to process
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

## Troubleshooting

### Common Issues

1. **Missing .env file**: Make sure the `.env` file exists and contains required variables
2. **File format errors**: Ensure CSV files use semicolon (;) as delimiter and double quotes for text
3. **Date format**: Use YYYY-MM-DD format for valid_from_date parameter

### Error Messages

- `Usage: python script_name.py...`: Not enough command line arguments provided
- File processing errors will show which file caused the issue

## Contributing

When modifying the script:
1. Keep the existing class structure for compatibility
2. Add new code list IDs to the `codeListsId` enum
3. Update the `.env` file for new configuration options
4. Test with both CSV and XML input formats

## Notes

- The script processes files with names matching pattern `VS_<name>_(...)` or `VS <name>_(...)`
- Output files are named `<name>_transformed.json`
- All dates are set with default validity periods (can be customized in `.env`)
- The TODO comment mentions ValidFrom dates at code level need to be made dynamic

## Support

For issues or questions about this transformation tool, contact the responsible persons listed in your `.env` configuration.