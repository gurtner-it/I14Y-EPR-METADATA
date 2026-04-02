#!/usr/bin/env python3
"""artdecor_downloader.py

Reads a YAML/TXT package file that contains entries with 'valueSetName' and 'sourceUrl'.
It converts any 'format=json' in the URL to 'format=xml', downloads the XML content and
saves files into the provided output directory (default: AD_VS/XML).

Usage:
    python3 artdecor_downloader.py /path/to/SwissEprValueSetPackage_20240607.txt /path/to/output_dir
"""

import os
import re
import sys
import requests
import time
from urllib.parse import urlparse, parse_qs
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def parse_package_file(path):
    """Simple parser to extract (valueSetName, sourceUrl) pairs from the package file."""
    pairs = []
    current_name = None
    url_re = re.compile(r"sourceUrl\s*:\s*(\S+)", re.IGNORECASE)
    name_re = re.compile(r"-\s*valueSetName\s*:\s*(.+)", re.IGNORECASE)

    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            # skip commented lines
            if line.lstrip().startswith('#'):
                continue
            if not line:
                continue
            mname = name_re.match(line)
            if mname:
                current_name = mname.group(1).strip()
                continue
            murl = url_re.search(line)
            if murl:
                url = murl.group(1).strip()
                # Remove any surrounding quotes
                if url.startswith('"') and url.endswith('"'):
                    url = url[1:-1]
                pairs.append((current_name or 'unknown', url))
                current_name = None
    return pairs


def convert_to_xml_url(url):
    # If format=json present, replace with format=xml
    if 'format=' in url:
        return re.sub(r'format=[^&]+', 'format=xml', url, flags=re.IGNORECASE)
    # If missing, append format=xml
    sep = '&' if '?' in url else '?'
    return url + sep + 'format=xml'


def sanitize_filename(name):
    # Use valueSetName if available, else derive from URL path or id param
    name = name or 'valueSet'
    name = re.sub(r"[\\/\s]+", '_', name)
    name = re.sub(r"[^0-9A-Za-z._-]", '', name)
    return name


def create_session(retries=2, backoff_factor=0.5, status_forcelist=(429, 503, 504)):
    session = requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=["GET", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


def download_url_to_file(session, url, dest_path, timeout=30):
    headers = {'Accept': 'application/xml, text/xml, */*', 'User-Agent': 'EPD_Metadata/1.0'}
    try:
        r = session.get(url, headers=headers, timeout=timeout)
        if not r.ok:
            return False, f'HTTP {r.status_code} {r.reason} for URL: {url}'
        r.raise_for_status()
        with open(dest_path, 'wb') as f:
            f.write(r.content)
        return True, None
    except requests.exceptions.HTTPError as e:
        return False, f'HTTP error: {e}'
    except requests.exceptions.ConnectionError as e:
        return False, f'Connection error: {e}'
    except requests.exceptions.Timeout:
        return False, f'Request timed out after {timeout}s: {url}'
    except Exception as e:
        return False, str(e)


def pick_name_from_url(url):
    # Try to use id query param
    try:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        if 'id' in qs and qs['id']:
            return qs['id'][0]
        # else use path segments
        parts = [p for p in parsed.path.split('/') if p]
        if parts:
            return parts[-1]
    except Exception:
        pass
    return None


def main(argv):
    if len(argv) < 2:
        print('Usage: artdecor_downloader.py <package_file> <output_dir>')
        return 2

    package_file = argv[0]
    output_dir = argv[1]

    if not os.path.exists(package_file):
        print(f'Package file not found: {package_file}')
        return 3

    os.makedirs(output_dir, exist_ok=True)

    pairs = parse_package_file(package_file)
    if not pairs:
        print('No entries found in package file.')
        return 4

    successes = 0
    failures = []

    session = create_session()

    for idx, (name, url) in enumerate(pairs, start=1):
        xml_url = convert_to_xml_url(url)
        # Validate URL - if missing scheme, try to fix if it looks like a host/path
        parsed = urlparse(xml_url)
        if not parsed.scheme:
            # skip obviously invalid placeholder values
            if xml_url.strip().lower() in ('url', 'http://url', 'https://url'):
                print(f'  -> SKIPPED: invalid placeholder URL: {xml_url}')
                failures.append({'name': name or 'unknown', 'url': xml_url, 'error': 'invalid placeholder URL'})
                continue
            # try to prepend https:// when it looks like a domain/path
            if '.' in xml_url.split('?')[0] or xml_url.startswith('//'):
                if xml_url.startswith('//'):
                    xml_url = 'https:' + xml_url
                else:
                    xml_url = 'https://' + xml_url
                parsed = urlparse(xml_url)
        # After fix, if still no scheme -> skip
        if not parsed.scheme:
            print(f'  -> SKIPPED: cannot determine scheme for URL: {xml_url}')
            failures.append({'name': name or 'unknown', 'url': xml_url, 'error': 'no URL scheme'})
            continue
        base_name = sanitize_filename(name) if name else None
        if not base_name or base_name == 'unknown':
            guessed = pick_name_from_url(xml_url)
            base_name = sanitize_filename(guessed or f'valueSet_{idx}')
        filename = f"{base_name}.xml"
        dest_path = os.path.join(output_dir, filename)

        print(f'Downloading ({idx}/{len(pairs)}): {base_name} ← {xml_url}')
        ok, err = download_url_to_file(session, xml_url, dest_path)
        if ok:
            print(f'  -> Saved: {dest_path}')
            successes += 1
            # be polite
            time.sleep(0.2)
        else:
            print(f'  -> FAILED: {err}')
            failures.append({'name': base_name, 'url': xml_url, 'error': err})

    print('\nSummary:')
    print(f'  Total entries: {len(pairs)}')
    print(f'  Successful downloads: {successes}')
    print(f'  Failures: {len(failures)}')
    if failures:
        for f in failures:
            print(f"   - {f['name']}: {f['error']}")

    return 0 if not failures else 5


if __name__ == '__main__':
    exit_code = main(sys.argv[1:])
    sys.exit(exit_code)
