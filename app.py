from flask import Flask, request, jsonify, render_template_string, send_file
from flask_cors import CORS
import os
import sys
import subprocess
import tempfile
import json
import logging
import shutil
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
AD_VS_FOLDER = 'AD_VS'
OUTPUT_FOLDER = os.path.join(AD_VS_FOLDER, 'Transformed')
ALLOWED_EXTENSIONS = {'xml', 'json'}
        
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def run_python_script(script_name, args, working_dir=None):
    """Execute a Python script with given arguments"""
    try:
        cmd = ['python3', script_name] + args
        logger.info(f"Executing command: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        return {
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'stdout': '',
            'stderr': 'Command timed out after 5 minutes',
            'returncode': -1
        }
    except Exception as e:
        return {
            'success': False,
            'stdout': '',
            'stderr': str(e),
            'returncode': -1
        }

@app.route('/')
def index():
    """Serve the HTML GUI"""
    # You would put your HTML content here or serve it from a file
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>I14Y Python GUI</title>
        <meta charset="UTF-8">
    </head>
    <body>
        <h1>I14Y Python GUI Backend Running</h1>
        <p>The Flask backend is running. Please use the frontend HTML file to access the GUI.</p>
        <p>Backend endpoints:</p>
        <ul>
            <li>POST /api/transform - Transform files</li>
            <li>POST /api/execute - Execute API commands</li>
        </ul>
        <a href="http://localhost:8080/" target="_Blank">Open GUI</a>
    </body>
    </html>
    """)

@app.route('/api/transform', methods=['POST'])
def transform_files():
    """Handle file transformation requests"""
    try:
        # 1️⃣ Clean up old uploads and output folders
        for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER]:
            if os.path.exists(folder):
                shutil.rmtree(folder, ignore_errors=True)
                logger.info(f"Deleted folder: {folder}")
            os.makedirs(folder, exist_ok=True)

        # Get form data
        responsible_key = request.form.get('responsibleKey')
        deputy_key = request.form.get('deputyKey')
        date_valid_from = request.form.get('dateValidFrom')
        version = request.form.get('version', '1.0.0')  # Get version, default to 1.0.0
        create_new = request.form.get('createNew') == 'true'
        
        # Validate required fields. Either a default version or per-file versions must be provided.
        if not all([responsible_key, deputy_key, date_valid_from]) or (not version and not versions_map):
            return jsonify({
                'success': False,
                'error': 'Missing required fields: responsible_key, deputy_key, date_valid_from, and version(s)'
            }), 400
        
        # Handle file uploads
        if 'files' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No files uploaded'
            }), 400
        
        files = request.files.getlist('files')
        if not files or files[0].filename == '':
            return jsonify({
                'success': False,
                'error': 'No files selected'
            }), 400

        # Create temporary directories
        output_folder = os.path.join(AD_VS_FOLDER, 'Transformed')
        os.makedirs(output_folder, exist_ok=True)
        
        uploaded_files = []
        
        try:
            # Save uploaded files
            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(UPLOAD_FOLDER, filename)
                    file.save(filepath)
                    uploaded_files.append(filename)
                    logger.info(f"Saved file: {filepath}")
            
            if not uploaded_files:
                return jsonify({
                    'success': False,
                    'error': 'No valid files uploaded (only XML allowed)'
                }), 400
            
            # Collect per-file versions if provided (same order as files)
            versions_list = request.form.getlist('versions') or []
            # Build a mapping from saved filename -> version (use uploaded_files which contains secure filenames)
            versions_map = {}
            for i, fname in enumerate(uploaded_files):
                if i < len(versions_list) and versions_list[i]:
                    versions_map[fname] = versions_list[i]

            # Prepare arguments for the transformation script
            args = [
                responsible_key,
                deputy_key,
                UPLOAD_FOLDER,
                output_folder,
                date_valid_from,
                version  # default version parameter (used as fallback)
            ]

            # Pass versions_map as JSON string as an optional extra argument
            if versions_map:
                args.append(json.dumps(versions_map))

            if create_new:
                args.append('-n')
            
            # Execute the transformation script
            # Replace 'your_transform_script.py' with the actual script name
            result = run_python_script('AD_I14Y_transformator.py', args)
            
            if result['success']:
                output_files = []

                if os.path.exists(output_folder):
                    output_files = [
                        f for f in os.listdir(output_folder)
                        if not f.startswith('.')  # ignores .DS_Store, .gitkeep, etc.
                    ]
                
                return jsonify({
                    'success': True,
                    'message': 'Files transformed successfully',
                    'input_files': uploaded_files,
                    'output_files': output_files,
                    'stdout': result['stdout'],
                    'output_folder': output_folder
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Transformation failed',
                    'stderr': result['stderr'],
                    'stdout': result['stdout']
                }), 500
                
        finally:
            # Optional: Clean up temporary files after some time
            # You might want to implement a cleanup job
            pass
            
    except Exception as e:
        logger.error(f"Error in transform_files: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@app.route('/api/execute', methods=['POST'])
def execute_api_command():
    """Handle API command execution"""
    try:
        # Detect if this is a multipart/form-data request (file upload) or JSON
        if request.content_type and request.content_type.startswith('multipart/form-data'):
            data = request.form.to_dict()
        else:
            data = request.get_json(force=True) or {}

        method = data.get('apiMethod')
        
        if not method:
            return jsonify({
                'success': False,
                'error': 'No API method specified'
            }), 400
        
        # Build arguments based on method
        args = [method]
        
        # Handle different methods and their parameters
        if method in ['-pc', '-pcl', '-ucl']:
            print(request.files)
            if 'filePath' in request.files:
                # Save uploaded file
                file = request.files['filePath']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(UPLOAD_FOLDER, filename)
                    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                    file.save(file_path)
                    args.append(file_path)
                else:
                    return jsonify({'success': False, 'error': 'Invalid file type'}), 400
            elif request.is_json:
                # If already sending a path from backend/server-side
                file_path = request.json.get('filePath')
                if file_path:
                    args.append(file_path)
                else:
                    return jsonify({'success': False, 'error': 'No file provided'}), 400
                
            if method in ['-pcl', '-ucl'] and 'conceptId' in data:
                args.append(str(data['conceptId']))
                
        elif method in ['-pmc', '-pmcl']:
            # Methods that need directory path
            if 'directoryPath' in data:
                args.append(str(data['directoryPath']))
                
        elif method in ['-gce', '-gci', '-dcl', '-dc']:
            # Methods that need concept ID
            if 'conceptId' in data:
                args.append(str(data['conceptId']))
            if method == '-gci' and 'outputFile' in data and data['outputFile']:
                args.append(data['outputFile'])
        
        elif method == '-srs':
            # Set registration status - requires: status, concept_id
            # Handle optional file upload (just for convenience, not sent to API)
            if 'registrationStatus' in data and data['registrationStatus']:
                args.append(str(data['registrationStatus']))
            if 'conceptId' in data and data['conceptId']:
                args.append(str(data['conceptId']))

        elif method == '-spl':
            # Set publication level - requires: level, concept_id
            # Handle optional file upload (just for convenience, not sent to API)
            if 'publicationLevel' in data and data['publicationLevel']:
                args.append(str(data['publicationLevel']))
            if 'conceptId' in data and data['conceptId']:
                args.append(str(data['conceptId']))
                
        elif method in ['-mspl', '-msrs']:
            # Batch operations for setting status/publication level
            # Requires: directory path and status/level
            if 'directoryPath' in data and data['directoryPath']:
                args.append(str(data['directoryPath']))
            if method == '-mspl' and 'publicationLevel' in data and data['publicationLevel']:
                args.append(str(data['publicationLevel']))
            elif method == '-msrs' and 'registrationStatus' in data and data['registrationStatus']:
                args.append(str(data['registrationStatus']))

        elif method == '-gc':
            # Get concepts with filters
            if 'publisher' in data and data['publisher']:
                args.append(f"--publisher={data['publisher']}")
            if 'status' in data and data['status']:
                args.append(f"--status={data['status']}")
            if 'outputFile' in data and data['outputFile']:
                args.append(data['outputFile'])
                
        elif method == '-gec':
            # Get EPD concepts
            if 'outputFile' in data and data['outputFile']:
                args.append(data['outputFile'])

        # Execute the API script
        # Replace 'I14Y_API_handling.py' with the actual script name
        result = run_python_script('I14Y_API_handling.py', args)
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': f'API command {method} executed successfully',
                'stdout': result['stdout'],
                'stderr': result['stderr']
            })
        else:
            return jsonify({
                'success': False,
                'error': f'API command failed: {result["stderr"]}',
                'stdout': result['stdout']
            }), 500
            
    except Exception as e:
        logger.error(f"Error in execute_api_command: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@app.route('/clear-log', methods=['get'])
def clear_log():
    log_path = 'api_errors_log.txt'
    with open(log_path, 'w') as f:
        f.write('')
    return 'Log cleared'


@app.route('/api/download-artdecor', methods=['POST'])
def download_artdecor():
    """Accept a YAML/TXT upload (or use default file) and download XML value sets into AD_VS/XML"""
    try:
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(os.path.join(AD_VS_FOLDER, 'XML'), exist_ok=True)

        use_default = request.form.get('useDefault') == 'true'
        yaml_path = None

        if not use_default:
            if 'yamlFile' not in request.files:
                return jsonify({'success': False, 'error': 'No YAML file uploaded and "use default" not checked'}), 400
            file = request.files['yamlFile']
            if file.filename == '':
                return jsonify({'success': False, 'error': 'Empty filename uploaded'}), 400
            filename = secure_filename(file.filename)
            yaml_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(yaml_path)
        else:
            # default file in workspace
            default_path = os.path.join(os.getcwd(), 'SwissEprValueSetPackage_20240607.txt')
            if not os.path.exists(default_path):
                return jsonify({'success': False, 'error': f'Default file not found: {default_path}'}), 400
            yaml_path = default_path

        output_dir = os.path.join(AD_VS_FOLDER, 'XML')

        # Run downloader script
        result = run_python_script('artdecor_downloader.py', [yaml_path, output_dir])

        if result['success']:
            return jsonify({'success': True, 'stdout': result['stdout'], 'stderr': result['stderr'], 'output_dir': output_dir})
        else:
            return jsonify({'success': False, 'stdout': result['stdout'], 'stderr': result['stderr'], 'error': 'Downloader script failed'}), 500

    except Exception as e:
        logger.error(f"Error in download_artdecor: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/get-concept-version', methods=['POST'])
def get_concept_version():
    """Get current version of a concept by name"""
    try:
        data = request.get_json()
        concept_name = data.get('conceptName')
        
        if not concept_name:
            return jsonify({'success': False, 'error': 'No concept name provided'}), 400
        
        logger.info(f"Fetching version for concept: {concept_name}")
        
        # Use I14Y API to get concept info
        result = run_python_script('I14Y_API_handling.py', ['-gec', 'temp_concepts.json'])
        
        if result['success']:
            # Load the temp file and find matching concept
            try:
                if not os.path.exists('temp_concepts.json'):
                    logger.warning("temp_concepts.json was not created")
                    return jsonify({'success': False, 'error': 'Concepts file not created'})
                
                with open('temp_concepts.json', 'r', encoding='utf-8') as f:
                    concepts_data = json.load(f)
                    
                # Search for concept by name
                if concepts_data and 'data' in concepts_data:
                    for concept in concepts_data['data']:
                        # Check if name matches in any language
                        names = concept.get('name', {})
                        if concept_name in names.values():
                            version = concept.get('version', '1.0.0')
                            if os.path.exists('temp_concepts.json'):
                                os.remove('temp_concepts.json')  # Clean up
                            logger.info(f"Found version {version} for {concept_name}")
                            return jsonify({'success': True, 'version': version})
                
                if os.path.exists('temp_concepts.json'):
                    os.remove('temp_concepts.json')  # Clean up
                logger.info(f"Concept {concept_name} not found in I14Y")
                return jsonify({'success': False, 'message': 'Concept not found'})
            except Exception as e:
                logger.error(f"Error parsing concepts: {str(e)}")
                if os.path.exists('temp_concepts.json'):
                    os.remove('temp_concepts.json')
                return jsonify({'success': False, 'error': f'Error parsing concepts: {str(e)}'})
        else:
            logger.error(f"Failed to fetch concepts: {result.get('stderr', 'Unknown error')}")
            return jsonify({'success': False, 'error': 'Failed to fetch concepts from I14Y API'})
            
    except Exception as e:
        logger.error(f"Error in get_concept_version: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/download/<path:filepath>')
def download_file(filepath):
    """Download generated files"""
    try:
        # Security check - ensure file is in temp folder
        if not filepath.startswith('temp/'):
            return jsonify({'error': 'Invalid file path'}), 403
            
        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True)
        else:
            return jsonify({'error': 'File not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Create api_errors_log.txt if it doesn't exist
    log_file = 'api_errors_log.txt'
    if not os.path.exists(log_file):
        with open(log_file, 'w') as f:
            f.write('')
        print(f"✅ Created {log_file}")
    
    print("🚀 Starting I14Y Flask Backend...")
    print("📁 Upload folder:", os.path.abspath(UPLOAD_FOLDER))
    print("📁 Temp folder:", os.path.abspath(AD_VS_FOLDER))
    print("🌐 Server will be available at: http://localhost:5001")
    print("\n" + "="*50)
    
    # Run the Flask app
    app.run(debug=True, host='0.0.0.0', port=5001)