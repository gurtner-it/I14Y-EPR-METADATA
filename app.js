let selectedFiles = [];

function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
    document.querySelector(`.tab[data-tab="${tabName}"]`).classList.add('active');

    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    document.getElementById(tabName).classList.add('active');

    if(tabName == "api_errors") {
        loadApiErrors();
    }

    showOutput('API results will be shown here.');
}

async function loadReadme() {
    try {
        const response = await fetch('../readme.md');  // adjust path if needed
        if (!response.ok) throw new Error('Cannot fetch README.md');
        const markdown = await response.text();
        const html = marked.parse(markdown); // converts markdown to HTML
        document.getElementById('readme').innerHTML = html;
    } catch (err) {
        document.getElementById('readme').innerHTML = `<p style="color:red;">Error loading README.md: ${err.message}</p>`;
    }
}

// Load README once on page load
window.addEventListener('DOMContentLoaded', loadReadme);

async function loadApiErrors() {
    try {
        // Add cache-busting parameter to prevent browser caching
        const cacheBuster = `?t=${new Date().getTime()}`;
        const response = await fetch(`../api_errors_log.txt${cacheBuster}`);
        if (!response.ok) throw new Error('Cannot fetch README.md');
        const html = await response.text();
        showOutput(html);
    } catch (err) {
        showOutput(`<p style="color:red;">Error loading api_errors_log.txt: ${err.message}</p>`, true);
    }
}

// Load README once on page load
window.addEventListener('DOMContentLoaded', loadApiErrors);

async function emptyApiErrors() {
    try {
        const response = await fetch('http://localhost:5001/clear-log'); // your backend route
        if (!response.ok) throw new Error('Failed to clear log');

        showOutput('API errors log has been emptied.');
    } catch (err) {
        showOutput(`Error: ${err.message}`);
    }
}

async function loadTokenFromLog() {
    try {
        const logText = document.getElementById('outputContent').textContent;

        // Extract token between markers
        const match = logText.match(/<token_start>\s*(.*?)\s*<token_end>/);
        if (match && match[1]) {
            const token = match[1].trim();
            document.getElementById('tokenInput').value = token;
            console.log('Token loaded:', token);
        } else {
            console.warn('Token not found in log');
        }
    } catch (err) {
        console.error('Failed to load token from log:', err);
    }
}


async function handleFileSelect(event) {
    const files = Array.from(event.target.files);
    selectedFiles = files;
    updateFileList();
    
    // Fetch current version from first selected file
    if (files.length > 0) {
        await fetchCurrentVersion(files[0].name);
    }
}

async function fetchCurrentVersion(fileName) {
    const versionInput = document.getElementById('version');
    const versionStatus = document.getElementById('version-status');
    
    try {
        // Extract concept name from filename (e.g., "VS_DocumentEntry.classCode_..." -> "DocumentEntry.classCode")
        const conceptMatch = fileName.match(/VS[_ ](.+?)_/);
        if (!conceptMatch) {
            console.warn('Could not extract concept name from filename');
            versionStatus.innerHTML = '⚠️ Could not detect concept name';
            return;
        }
        
        const conceptName = conceptMatch[1];
        
        // Show loading spinner
        versionStatus.innerHTML = '🔄 Fetching current version from I14Y API...';
        versionInput.value = '';
        versionInput.placeholder = 'Loading...';
        
        // Call backend to get concept by name/identifier
        const response = await fetch('http://localhost:5001/api/get-concept-version', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ conceptName: conceptName }),
            signal: AbortSignal.timeout(10000)  // 10 second timeout
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.success && result.version) {
            versionInput.value = result.version;
            versionInput.placeholder = 'e.g., 2.0.3';
            versionStatus.innerHTML = `✅ Current version in I14Y: <strong>${result.version}</strong> - Please increment before transforming`;
            console.log(`✅ Fetched version: ${result.version}`);
        } else {
            // No version found in API - use 1.0.0
            versionInput.value = '1.0.0';
            versionInput.placeholder = 'e.g., 1.0.1';
            versionStatus.innerHTML = 'ℹ️ Concept not found in I14Y. Starting with version <strong>1.0.0</strong>';
            console.log(`ℹ️ No existing version found for ${conceptName}. Using 1.0.0`);
        }
    } catch (error) {
        // API call failed - use 1.0.0 as fallback
        console.warn('Could not fetch current version (backend may not be running):', error.message);
        versionInput.value = '1.0.0';
        versionInput.placeholder = 'e.g., 1.0.1';
        versionStatus.innerHTML = '⚠️ Could not connect to API. Using default version <strong>1.0.0</strong>';
    }
}

function updateFileList() {
    const fileList = document.getElementById('fileList');
    
    if (selectedFiles.length === 0) {
        fileList.innerHTML = '<span style="color: #999;">No files selected</span>';
        return;
    }

    fileList.innerHTML = selectedFiles.map((file, index) => `
        <div class="file-item">
            📄 ${file.name}
            <span class="remove" onclick="removeFile(${index})">×</span>
        </div>
    `).join('');
}

function removeFile(index) {
    selectedFiles.splice(index, 1);
    updateFileList();
}

function updateApiForm() {
    const method = document.getElementById('apiMethod').value;
    const parametersDiv = document.getElementById('apiParameters');
    
    parametersDiv.innerHTML = '';

    if (!method) return;

    const parameters = getParametersForMethod(method);
    
    parameters.forEach(param => {
        const div = document.createElement('div');
        div.className = 'form-group';
        
        if (param.type === 'file') {
            div.innerHTML = `
                <label for="${param.name}">${param.label} ${param.required ? '*' : ''}</label>
                <div class="file-upload">
                    <input type="file" id="${param.name}" name="${param.name}" ${param.required ? 'required' : ''} ${param.accept ? `accept="${param.accept}"` : ''}>
                    <label for="${param.name}" class="file-upload-label">Choose File</label>
                </div>
                <div id="${param.name}-selected" class="selected-file" style="margin-top: 8px; color: #666; font-size: 14px;"></div>
            `;
        } else if (param.type === 'select') {
            div.innerHTML = `
                <label for="${param.name}">${param.label} ${param.required ? '*' : ''}</label>
                <select id="${param.name}" name="${param.name}" ${param.required ? 'required' : ''}>
                    ${param.options.map(opt => `<option value="${opt.value}">${opt.label}</option>`).join('')}
                </select>
            `;
        } else {
            div.innerHTML = `
                <label for="${param.name}">${param.label} ${param.required ? '*' : ''}</label>
                <input type="${param.type}" id="${param.name}" name="${param.name}" placeholder="${param.placeholder || ''}" ${param.required ? 'required' : ''} ${param.value ? `value="${param.value}"` : ''} ${param.disabled ? 'disabled' : ''}>
            `;
        }
        
        parametersDiv.appendChild(div);
    });

    addFileListener();
}

function getParametersForMethod(method) {
    const parameterMap = {
        '-pc': [
            { name: 'filePath', label: 'JSON File Path', type: 'file', required: true, accept: '.json' }
        ],
        '-pmc': [
            { name: 'directoryPath', label: 'Directory Path', type: 'text', required: true, placeholder: 'Path to directory', value: 'AD_VS/Transformed' }
        ],
        '-pcl': [
            { name: 'filePath', label: 'JSON File Path', type: 'file', required: true, accept: '.json' },
            { name: 'conceptId', label: 'Concept ID', type: 'text', required: true, placeholder: 'Concept id: 028c635d-970d-4fa6-b234-aa627ff8aaaf' }
        ],
        '-pmcl': [
            { name: 'directoryPath', label: 'Directory Path', type: 'text', required: true, placeholder: 'Path to directory', value: 'AD_VS/Transformed' }
        ],
        '-gce': [
            { name: 'conceptId', label: 'Concept ID', type: 'text', required: true, placeholder: 'Concept id: 028c635d-970d-4fa6-b234-aa627ff8aaaf' },
            { name: 'message', label: 'Output File', type: 'text', required: false, value: 'Stored in epd_codelist_entry.json', disabled: true }
        ],
        '-gci': [
            { name: 'conceptId', label: 'Concept identifier (OID)', type: 'text', required: true, placeholder: 'Concept identifier: 2.16.756.5.30.1.127.3.10.1.11' },
            { name: 'outputFile', label: 'Output File (optional)', type: 'text', required: false, placeholder: 'output.json' }
        ],
        '-gc': [
            { name: 'publisher', label: 'Publisher', type: 'text', required: false, placeholder: 'e.g. CH_eHealth', value: 'CH_eHealth' },
            { name: 'status', label: 'Status', type: 'select', required: false, options: [
                { value: '', label: 'All' },
                { value: 'Standard', label: 'Standard' },
                { value: 'Incomplete', label: 'Incomplete' },
                { value: 'Candidate', label: 'Candidate' },
                { value: 'Recorded', label: 'Recorded' },
                { value: 'Qualified', label: 'Qualified' },
                { value: 'PreferredStandard', label: 'PreferredStandard' },
                { value: 'Superseded', label: 'Superseded' },
                { value: 'Retired', label: 'Retired' }

            ]},
            { name: 'outputFile', label: 'Output File (optional)', type: 'text', required: false, placeholder: 'output.json' }
        ],
        '-gec': [
            { name: 'outputFile', label: 'Output File (optional)', type: 'text', required: false, placeholder: 'epd_concepts.json', value: 'epd_concepts.json' }
        ],
        '-ucl': [
            { name: 'filePath', label: 'JSON File Path', type: 'file', required: true, accept: '.json' },
            { name: 'conceptId', label: 'Concept ID', type: 'text', required: true, placeholder: 'Concept id: 028c635d-970d-4fa6-b234-aa627ff8aaaf' }
        ],
        '-dcl': [
            { name: 'conceptId', label: 'Concept ID', type: 'text', required: true, placeholder: 'Concept id: 028c635d-970d-4fa6-b234-aa627ff8aaaf' }
        ],
        '-dc': [
            { name: 'conceptId', label: 'Concept ID', type: 'text', required: true, placeholder: 'Concept id: 028c635d-970d-4fa6-b234-aa627ff8aaaf' }
        ],
        '-spl': [
            { name: 'conceptId', label: 'Concept ID', type: 'text', required: true, placeholder: 'Concept id: 028c635d-970d-4fa6-b234-aa627ff8aaaf' },
            { name: 'publicationLevel', label: 'level', type: 'select', required: false, options: [
                { value: 'Internal', label: 'Internal' },
                { value: 'Public', label: 'Public' },
            ]}
        ],
        '-srs': [
            { name: 'conceptId', label: 'Concept ID', type: 'text', required: true, placeholder: 'Concept id: 028c635d-970d-4fa6-b234-aa627ff8aaaf' },
            { name: 'registrationStatus', label: 'Status', type: 'select', required: false, options: [
                { value: '', label: '--- Most important:' },
                { value: 'Recorded', label: 'Recorded (proprietary code)' },
                { value: 'Retired', label: 'Retired' },
                { value: 'Standard', label: 'Standard (e.g. eCH or a defined standard) (CAVE: Can only be set by I14Y support)' },
                { value: '', label: '--- Not relevant:' },
                { value: 'Incomplete', label: 'Incomplete' },
                { value: 'Candidate', label: 'Candidate' },
                { value: 'Qualified', label: 'Qualified' },
                { value: 'PreferredStandard', label: 'PreferredStandard' },
                { value: 'Superseded', label: 'Superseded' },
            ]},
        ],
        '-ucm':  [
            { name: 'fakeFile', label: 'File', type: 'text', required: true, placeholder: 'Stored to codelist_mapping.json', disabled: true }
        ],
    };

    return parameterMap[method] || [];
}

function showOutput(content, isError = false) {
    const output = document.getElementById('output');
    const outputContent = document.getElementById('outputContent');
    
    output.style.display = 'block';
    output.className = `output ${isError ? 'error' : 'success'}`;
    outputContent.textContent = content;
}

function addFileListener() {
    if(!document.getElementById("filePath")) {
        return;
    }

    document.getElementById("filePath").addEventListener("change", function(event) {
        const file = event.target.files[0];
        const selectedFileDiv = document.getElementById("filePath-selected");
        
        if (!file) {
            if (selectedFileDiv) selectedFileDiv.textContent = "";
            return;
        }

        const fileName = file.name;
        
        // Show selected file name
        if (selectedFileDiv) {
            selectedFileDiv.innerHTML = `📄 <strong>Selected:</strong> ${fileName}`;
        }

        // Extract UUID with regex
        const match = fileName.match(
            /([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/
        );

        if (match) {
            const extractedId = match[1];
            console.log("Extracted ID:", extractedId);
            const conceptIdField = document.getElementById("conceptId");
            if (conceptIdField) {
                conceptIdField.value = extractedId;
            }
        } else {
            console.error("❌ No UUID found in filename!");
        }
    });
}

// Form submissions - REAL API CALLS
document.getElementById('transformForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    if (selectedFiles.length === 0) {
        showOutput('Please select at least one file to transform.', true);
        return;
    }

    const formData = new FormData(this);
    
    // Add files to formData
    selectedFiles.forEach((file, index) => {
        formData.append('files', file);
    });

    showOutput('🔄 Processing files... This may take a moment.');

    try {
        // REAL API CALL TO FLASK BACKEND
        const response = await fetch('http://localhost:5001/api/transform', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.success) {
            const output = `✅ Transformation completed successfully!

📁 Files processed:
- ${result.input_files.join('\n- ')}

📄 Output files:
- ${result.output_files.join('\n- ')}

📂 Output folder: 
${result.output_folder}

Details:
${result.stdout}`;
            showOutput(output);
        } else {
            showOutput(`❌ Transformation failed: ${result.error}\n\n${result.stderr || ''}`, true);
        }
    } catch (error) {
        showOutput(`❌ Network error: ${error.message}\n\nMake sure the Flask backend is running on http://localhost:5001`, true);
    }
});

document.getElementById('apiForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const formData = new FormData(this);
    const method = formData.get('apiMethod');
    
    if (!method) {
        showOutput('Please select an API method.', true);
        return;
    }

    showOutput('🔄 Executing API call... Please wait.');

    try {
        // Convert FormData to JSON for API methods
        const data = {};
        for (let [key, value] of formData.entries()) {
            data[key] = value;
        }

        const fileInput = document.getElementById('filePath');
        let response;

        if (fileInput && fileInput.files.length > 0) {
            // File exists → send FormData
            const fileFormData = new FormData();
            fileFormData.append('apiMethod', data.apiMethod);
            if (data.conceptId) fileFormData.append('conceptId', data.conceptId);
            fileFormData.append('filePath', fileInput.files[0]);

            response = await fetch('http://localhost:5001/api/execute', {
                method: 'POST',
                body: fileFormData
            });
        } else {
            // No file → send JSON
            response = await fetch('http://localhost:5001/api/execute', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
        }

        const result = await response.json();

        if (result.success) {
            const output = `API call executed (see logs below for more details)
            
🔧 Method: ${data.apiMethod}
${Object.entries(data).filter(([key]) => key !== 'apiMethod').map(([key, value]) => `📋 ${key}: ${value}`).join('\n')}

${result.stdout}`;
            showOutput(output);

            await loadTokenFromLog();
        } else {
            showOutput(`❌ API call failed: ${result.error}\n\n${result.stdout || ''}`, true);
        }
    } catch (error) {
        showOutput(`❌ Network error: ${error.message}\n\nMake sure the Flask backend is running on http://localhost:5001`, true);
    }
});

// Set default date to today
document.getElementById('dateValidFrom').valueAsDate = new Date();