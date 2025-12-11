# I14Y EPR Metadata Management Toolkit

## 🎯 What This Does

This toolkit provides a complete workflow for managing healthcare code lists in the Swiss I14Y interoperability platform:

1. **Data Transformation** (`AD_I14Y_transformator.py`): Converts XML files into I14Y-compliant JSON structures (automatically creates both concepts and codelists)
2. **API Management** (`I14Y_API_handling.py`): Handles upload and management of concepts and code lists via I14Y REST API
3. **Registration Status Management**: Sets concepts to "Recorded" status
4. **Manual Platform Verification**: Final verification through I14Y web interface

## 📋 Complete Workflow

### Step 1: Transform XML to JSON (Creates Concepts & Codelists)
Transform XML files into I14Y-compatible JSON format. This step automatically generates both concept definitions and their associated code lists.

### Step 2: Upload New Concept Versions
Upload the transformed concept definitions to I14Y platform.

### Step 3: Upload Code Lists
Upload the code list entries to the previously created concepts.

### Step 4: Set Registration Status to "Recorded"
Update the concept registration status to make them officially recorded.

### Step 5: Manual Verification via I14Y GUI
Log into the I14Y web platform to verify the status and content of uploaded concepts.

---

# Installation & Setup

## Prerequisites

- Python 3.7+
- Valid I14Y API credentials
- Access to I14Y web platform for manual verification

## Installation

1. Clone the repository:
```bash
git clone https://github.com/ehealthsuisse/I14Y-EPR-METADATA.git
cd I14Y-EPR-METADATA
```

2. Create virtual environment (once only):
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file (see Configuration section)

## Configuration

Create a `.env` file in your root folder `I14Y-EPR-METADATA` with the following variables:

```env
# API Configuration
#API_MODE=PROD
API_MODE=ABN

# PROD Credentials
PROD_CLIENT_ID=i14y_prod_ehealth_epd
PROD_CLIENT_SECRET=your_secret
PROD_TOKEN_URL=https://identity.i14y.c.bfs.admin.ch/realms/bfs-sis-p/protocol/openid-connect/token
PROD_BASE_API_URL=https://api.i14y.admin.ch/api/partner/v1

# ABN Credentials
ABN_CLIENT_ID=i14y_abn_ehealth_epd
ABN_CLIENT_SECRET=your_secret
ABN_TOKEN_URL=https://identity.i14y.a.c.bfs.admin.ch/realms/bfs-sis-a/protocol/openid-connect/token
ABN_BASE_API_URL=https://api-a.i14y.admin.ch/api/partner/v1

# Logging
log_level=INFO

# Transformation Configuration
DEFAULT_RESPONSIBLE_EMAIL=pero.grgic@e-health-suisse.ch
DEFAULT_RESPONSIBLE_SHORT_NAME=PGR

DEFAULT_DEPUTY_EMAIL=stefanie.neuenschwander@e-health-suisse.ch
DEFAULT_DEPUTY_SHORT_NAME=SNE

PUBLISHER_IDENTIFIER=CH_eHealth
PUBLISHER_NAME=eHealth Suisse

# Note: Version numbers are fetched from I14Y API or default to 1.0.0
DEFAULT_PUBLICATION_LEVEL=Internal
DEFAULT_CONCEPT_TYPE=CodeList
DEFAULT_VALUE_TYPE=String
DEFAULT_VALUE_MAX_LENGTH=30

DEFAULT_PERIOD_START=2024-06-01
DEFAULT_PERIOD_END=2100-06-01
```

## 📁 Project Structure

```
project/
├── AD_I14Y_transformator.py           # Step 1: XML to JSON transformation
├── I14Y_API_handling.py               # Steps 2-4: API operations
├── app.py                             # Optional: Web GUI
├── .env                               # Configuration
├── requirements.txt                   # Dependencies
├── api_errors_log.txt                 # Error logging
├── AD_VS/
│   ├── XML/                          # Input: Original XML files
│   └── Transformed/
│       ├── Concepts/                 # Output: Concept JSON files
│       └── Codelists/                # Output: Codelist JSON files
```

---

# 🔄 Step-by-Step Workflow

## Step 1: Transform XML Files to JSON

Transform XML files into I14Y-compliant JSON format. This automatically creates both concept definitions and code lists.

### Via Command Line:
```bash
# Process files and create new concept versions (existing concepts)
python AD_I14Y_transformator.py PGR SNE ./AD_VS/XML ./AD_VS/Transformed 2026-06-01 2.0.3

# Create completely new concepts (with -n flag)
python AD_I14Y_transformator.py PGR SNE ./AD_VS/XML ./AD_VS/Transformed 2026-06-01 1.0.0 -n
```

### Parameters:
- `responsible_key`: Responsible person (PGR, SNE)
- `deputy_key`: Deputy person (PGR, SNE)  
- `input_folder`: Path to XML files
- `output_folder`: Path for JSON output
- `valid_from_date`: Validity start date (YYYY-MM-DD)
- `version`: Version number (e.g., 2.0.3)
- `-n`: Optional flag to create new concepts (if omitted, creates new versions of existing concepts)

### Version Management:
**Important:** Always increment the version number when updating existing concepts!

1. **For new concepts** (with `-n` flag): Start with `1.0.0`
2. **For existing concepts**: 
   - Get current version from I14Y API
   - Increment appropriately:
     - Major changes: `2.0.0` → `3.0.0`
     - Minor updates: `2.0.0` → `2.1.0`
     - Patches: `2.0.0` → `2.0.1`

**GUI automatically fetches the current version from I14Y** when you select XML files, making version management easier.

### Output:
- **Concepts**: `AD_VS/Transformed/Concepts/` - Concept definition files
- **Codelists**: `AD_VS/Transformed/Codelists/` - Code list entry files

## Step 2: Upload Concept Versions

Upload the transformed concept definitions to I14Y.

```bash
# Upload single concept
python I14Y_API_handling.py -pc AD_VS/Transformed/Concepts/concept-file.json

# Upload multiple concepts from directory
python I14Y_API_handling.py -pmc AD_VS/Transformed/Concepts/
```

## Step 3: Upload Code Lists

Upload code list entries to the previously created concepts.

```bash
# Upload single codelist
python I14Y_API_handling.py -pcl AD_VS/Transformed/Codelists/codelist-file.json <concept-identifier>

# Upload multiple codelists from directory
python I14Y_API_handling.py -pmcl AD_VS/Transformed/Codelists/
```

## Step 4: Set Registration Status to "Recorded"

Update concept status to make them officially recorded.

```bash
# Set single concept to recorded status
python I14Y_API_handling.py -srs Recorded <concept-identifier>

# Note: For batch operations, you'll need to script individual -srs calls
# as there is no batch method for setting registration status
```

## Step 5: Manual Verification via I14Y GUI

1. **Login to I14Y Platform:**
   - **ABN Environment**: https://www.i14y-a.admin.ch
   - **PROD Environment**: https://www.i14y.admin.ch

2. **Navigate to Your Concepts:**
   - Go to "My Concepts" or search for your uploaded concepts
   - Verify concept status shows as "Recorded"
   - Check concept content and code list entries
   - Confirm multilingual content is displayed correctly

3. **Verification Checklist:**
   - ✅ Concept status = "Recorded"
   - ✅ Code list entries are present
   - ✅ Multilingual names display correctly
   - ✅ Metadata (responsible persons, validity dates) is accurate

---

# 🖥️ Optional: Web GUI Interface

For a user-friendly interface, you can use the included web application:

## 1. Start Flask Backend:
```bash
source .venv/bin/activate  # (optional) On Windows: .venv\Scripts\activate
python app.py
```
The backend will run on `http://localhost:5001`

## 2. Serve Frontend:
```bash
python -m http.server 8080
```

## 3. Access Application:
Open browser to: `http://localhost:8080` (or check `http://localhost:5001` for backend status)

---

# 📊 API Operations Reference

## Upload Operations:
```bash
# Concepts
-pc <file>          # Post single concept
-pmc <directory>    # Post multiple concepts

# Codelists  
-pcl <file> <uuid>  # Post single codelist
-pmcl <directory>   # Post multiple codelists
```

## Management Operations:
```bash
# Updates
-ucl <file> <uuid>  # Update codelist (delete old + post new)
-dcl <uuid>         # Delete all codelist entries
-dc <uuid>          # Delete concept

# Status & Publication Management
-srs <status> <uuid>  # Set registration status (e.g., Recorded, Standard)
-spl <level> <uuid>   # Set publication level (e.g., Internal, Public)
```

## Retrieval Operations:
```bash
-gc [filters]       # Get concepts with filters (--publisher, --status, etc.)
-gec [output_file]  # Get all EPD concepts
-gci <OID> [file]   # Get concept by identifier (OID)
-gce <uuid>         # Get codelist entries
-ucm                # Update codelist mapping from API
```

---

# 📝 Important Notes

## Version Management:
**CRITICAL: Always use proper version numbers!**

### Version Numbering Rules:
- Use semantic versioning: `MAJOR.MINOR.PATCH` (e.g., `2.0.3`)
- **New concepts**: Start with `1.0.0`
- **Updating existing concepts**: Always increment the version
  - **Major changes** (breaking changes): `2.0.0` → `3.0.0`
  - **Minor changes** (new features): `2.0.0` → `2.1.0`
  - **Patch** (bug fixes, small updates): `2.0.0` → `2.0.1`

### How Versioning Works:
1. **GUI (Recommended)**: 
   - Select XML files → System automatically fetches current version from I14Y API
   - You see the current version and must increment it manually
   - If concept doesn't exist or API fails: defaults to `1.0.0`

2. **Command Line**:
   - Manually check current version: `python I14Y_API_handling.py -gci <OID>`
   - Provide the new version as 6th parameter
   - Example: `python AD_I14Y_transformator.py PGR SNE ./AD_VS/XML ./AD_VS/Transformed 2026-06-01 2.0.3`

### Important:
- **Never reuse version numbers** - each upload must have a unique version
- **No hardcoded defaults** - Version is always fetched from API or set to `1.0.0`
- **Backend must be running** for automatic version fetching in GUI

## Transformation Notes:
- Processes files matching `VS_<name>_(...)` or `VS <name>_(...)`
- Automatically generates both concept and codelist JSON files
- Output files include I14Y identifiers in filenames
- Supports multilingual content (DE, EN, FR, IT, RM)

## API Notes:
- OAuth2 authentication with automatic token refresh
- Error logging to `api_errors_log.txt`
- Supports both ABN (test) and PROD environments
- Rate limiting and retry logic included

## Workflow Notes:
- **Step 1** must be completed before Steps 2-3
- **Step 2** (concept upload) must succeed before Step 3 (codelist upload)
- **Step 4** can only be performed after successful upload
- **Step 5** provides final verification and is mandatory for production
- The `-n` flag in Step 1 creates completely new concepts; without it, new versions of existing concepts are created

## Limitations:
- Locked concepts can only be deleted via I14Y official support
- Manual GUI verification is required for final approval
- Some operations may require elevated privileges in production environment

---

# 🆘 Troubleshooting

## Common Issues:
1. **Authentication failures**: Check `.env` credentials and ensure API_MODE is set correctly (PROD or ABN)
2. **Concept not found**: Ensure Step 2 completed successfully before Step 3
3. **Permission denied**: Verify API permissions for your environment
4. **Status update failed**: Check if concept is in correct state for status change
5. **Flask import errors**: Ensure Flask and Flask-Cors are installed (`pip install -r requirements.txt`)
6. **Wrong environment**: Check `.env` file - ensure API_MODE is uncommented for desired environment (PROD or ABN)

## Support:
- Check `api_errors_log.txt` for detailed error information
- Verify environment configuration in `.env`
- Ensure proper sequence of workflow steps