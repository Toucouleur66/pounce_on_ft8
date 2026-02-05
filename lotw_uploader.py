# lotw_uploader.py

import os
import json
import subprocess
import requests
import tempfile
from datetime import datetime

from logger import get_logger

from constants import LOTW_UPLOAD_CACHE_FILE

log = get_logger(__name__)


class LoTWUploader:
    def __init__(self, username, password, tqsl_path=None, tqsl_dir=None, location=None, signing_password=None):
        """
            Initialize LoTW uploader

            Args:
                username: LoTW username (usually callsign)
                password: LoTW account password (for downloads)
                tqsl_path: Path to tqsl executable (optional, will try to find it)
                tqsl_dir: Path to .tqsl directory (optional, will use default)
                location: Station location name in TQSL (optional)
                signing_password: Password for certificate signing (optional)
        """
        self.username = username
        self.password = password
        self.tqsl_path = tqsl_path or self._find_tqsl()
        self.tqsl_dir = tqsl_dir
        self.location = location
        self.signing_password = signing_password
        self.cache_file = LOTW_UPLOAD_CACHE_FILE

    def _find_tqsl(self):
        """Try to find tqsl executable in common locations"""
        if os.name == 'nt':  # Windows
            common_paths = [
                r"C:\Program Files (x86)\TrustedQSL\tqsl.exe",
                r"C:\Program Files\TrustedQSL\tqsl.exe",
            ]
        elif os.name == 'posix':  # macOS/Linux
            common_paths = [
                "/Applications/TrustedQSL.app/Contents/MacOS/tqsl",
                "/usr/bin/tqsl",
                "/usr/local/bin/tqsl",
            ]
        else:
            return None

        for path in common_paths:
            if os.path.exists(path):
                return path

        # Try to find in PATH
        try:
            result = subprocess.run(['which', 'tqsl'], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass

        return None

    @staticmethod
    def get_cache_info():
        try:
            if os.path.exists(LOTW_UPLOAD_CACHE_FILE):
                with open(LOTW_UPLOAD_CACHE_FILE, 'r') as f:
                    data = json.load(f)
                    return (
                        data.get('last_upload_time'),
                        data.get('total_uploaded', 0),
                        data.get('last_callsign', ''),
                        data.get('last_band', '')
                    )
        except Exception as e:
            log.error(f"Error reading LoTW upload cache: {e}")
        return None, 0, '', ''

    def update_cache(self, callsign, band):
        try:
            data = {
                'last_upload_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'total_uploaded': self.get_cache_info()[1] + 1,
                'last_callsign': callsign,
                'last_band': band
            }
            with open(self.cache_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            log.error(f"Error updating LoTW upload cache: {e}")

    def sign_and_upload_with_tqsl(self, adif_content):
        """
            Sign ADIF data with TQSL and upload directly to LoTW

            Args:
                adif_content: String containing ADIF data

            Returns:
                Tuple of (success, message)
        """
        if not self.tqsl_path or not os.path.exists(self.tqsl_path):
            return False, "TQSL executable not found. Please configure TQSL path in settings."

        try:
            # Create temporary file for input ADIF
            with tempfile.NamedTemporaryFile(mode='w', suffix='.adi', delete=False, encoding='utf-8') as temp_adif:
                temp_adif.write(adif_content)
                temp_adif_path = temp_adif.name

            # Build tqsl command with -u flag for direct upload
            cmd = [self.tqsl_path, '-d', '-u', '-a', 'compliant', '-x']

            if self.location:
                cmd.extend(['-l', self.location])

            if self.signing_password:
                cmd.extend(['-p', self.signing_password])

            # Add input file
            cmd.append(temp_adif_path)

            log.warning(f"Running TQSL command: {' '.join(cmd[:cmd.index('-p')] + ['***'] + cmd[cmd.index('-p')+2:]) if '-p' in cmd else ' '.join(cmd)}")

            # Set up environment with custom TQSL directory if specified
            env = os.environ.copy()
            if self.tqsl_dir:
                env['TQSLDIR'] = self.tqsl_dir
                log.warning(f"Using TQSL directory: {self.tqsl_dir}")

            # Run TQSL with upload
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,  # Longer timeout for upload
                env=env
            )

            # Clean up temporary file
            try:
                os.unlink(temp_adif_path)
            except:
                pass

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "Unknown error"
                log.error(f"TQSL upload failed: {error_msg}")
                return False, f"TQSL upload failed: {error_msg}"

            # Check output for success indicators
            output = result.stdout or result.stderr or ""

            if "accepted" in output.lower() or "uploaded" in output.lower() or "successful" in output.lower():
                log.info("TQSL upload successful")
                return True, "Upload successful"
            elif result.returncode == 0:
                # If return code is 0, consider it success even without explicit message
                log.info("TQSL upload completed (return code 0)")
                return True, "Upload completed"
            else:
                log.warning(f"TQSL upload unclear result: {output}")
                return False, f"Upload result unclear: {output[:200]}"

        except subprocess.TimeoutExpired:
            log.error("TQSL upload timeout")
            return False, "TQSL upload timeout"
        except Exception as e:
            log.error(f"TQSL upload error: {e}")
            return False, f"TQSL upload error: {str(e)}"

    def upload_qso(self, adif_record):
        """
            Upload a QSO to LoTW using TQSL

            Args:
                adif_record: ADIF formatted QSO record

            Returns:
                Tuple of (success, message)
        """
        return self.sign_and_upload_with_tqsl(adif_record)

    def download_qsos(self, qsl_since=None, qso_since=None, callsign=None, mode=None, band=None):
        """
            Download QSOs/QSLs from LoTW

            Args:
                qsl_since: Download QSLs confirmed since this date (YYYY-MM-DD)
                qso_since: Download QSOs received since this date (YYYY-MM-DD)
                callsign: Filter by callsign
                mode: Filter by mode
                band: Filter by band

            Returns:
                Tuple of (success, adif_data_or_error_message)
        """
        try:
            params = {
                'login': self.username,
                'password': self.password,
                'qso_query': '1',
                'qso_qsl': 'yes',
                'qso_qsldetail': 'yes',
                'qso_mydetail': 'yes',
                'qso_withown': 'yes'
            }

            if qsl_since:
                params['qso_qslsince'] = qsl_since
            if qso_since:
                params['qso_qsorxsince'] = qso_since
            if callsign:
                params['qso_callsign'] = callsign
            if mode:
                params['qso_mode'] = mode
            if band:
                params['qso_band'] = band

            log.debug(f"Downloading from LoTW: {self.DOWNLOAD_URL}")
            log.debug(f"Parameters: login={self.username}, filters={callsign or 'all'}/{mode or 'all'}/{band or 'all'}")

            response = requests.get(
                self.DOWNLOAD_URL,
                params=params,
                timeout=60
            )

            if response.status_code == 200:
                # Verify response contains ADIF data
                if 'ARRL Logbook of the World Status Report' in response.text or '<EOH>' in response.text:
                    log.info(f"LoTW download successful, received {len(response.text)} bytes")
                    return True, response.text
                else:
                    log.warning("LoTW download response does not appear to be valid ADIF")
                    return False, "Invalid response format"
            elif response.status_code == 401:
                log.error("LoTW authentication failed")
                return False, "Authentication failed - check username and password"
            else:
                log.error(f"LoTW download failed with status {response.status_code}")
                return False, f"Download failed: {response.status_code}"

        except requests.exceptions.Timeout:
            log.error("LoTW download timeout")
            return False, "Download timeout"
        except Exception as e:
            log.error(f"LoTW download error: {e}")
            return False, f"Download error: {str(e)}"

    def test_connection(self):
        # Try to download QSLs from the last day to test connection
        from datetime import date, timedelta
        yesterday = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')

        success, result = self.download_qsos(qsl_since=yesterday)

        if success:
            return True, "Connection successful"
        else:
            return False, result
