# telemetry_service.py

import base64
import hashlib
import hmac
import json
import os
import time
import uuid
import threading
import requests
from pathlib import Path
from logger import get_logger

log = get_logger(__name__)

class TelemetryService:
    """
    Telemetry service for tracking user activity and sending heartbeats to the API.

    Features:
    - HMAC-based authentication with installation_id and installation_secret
    - Automatic registration on first run (when my_call is set)
    - Sends heartbeat every 60 seconds
    - Silent operation - continues retrying if API is unreachable
    """

    def __init__(self, api_base_url="https://f5ukw.com/api", config_dir=None):
        self.api_base_url = api_base_url.rstrip('/')

        # Config directory setup
        if config_dir is None:
            config_dir = Path.home() / ".dx-pounce"
        else:
            config_dir = Path(config_dir)

        config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = config_dir / "telemetry_config.json"

        # State
        self.installation_id = None
        self.installation_secret = None
        self.registered = False
        self.running = False
        self.heartbeat_thread = None

        # User data (will be updated by the main application)
        self.my_call = None
        self.my_grid = None
        self.band = None
        self.ip_address = None

        # Load existing config if available
        self._load_config()

    def _load_config(self):
        # Load installation credentials from config file
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.installation_id = config.get('installation_id')
                    self.installation_secret = config.get('installation_secret')
                    self.registered = config.get('registered', False)

                    if self.installation_id and self.installation_secret:
                        log.info(f"Loaded telemetry config: {self.installation_id}")
        except Exception as e:
            log.error(f"Error loading telemetry config: {e}")

    def _save_config(self):
        try:
            config = {
                'installation_id': self.installation_id,
                'installation_secret': self.installation_secret,
                'registered': self.registered
            }
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            log.info(f"Saved telemetry config: {self.installation_id}")
        except Exception as e:
            log.error(f"Error saving telemetry config: {e}")

    def _generate_credentials(self):
        """Generate new installation credentials."""
        self.installation_id = str(uuid.uuid4())
        self.installation_secret = base64.b64encode(os.urandom(32)).decode('ascii')
        self.registered = False
        self._save_config()
        log.info(f"Generated new telemetry credentials: {self.installation_id}")

    @staticmethod
    def _b64(data: bytes) -> str:
        """Base64 encode bytes."""
        return base64.b64encode(data).decode("ascii")

    @staticmethod
    def _body_hash(body_obj) -> str:
        """Create SHA256 hash of JSON body."""
        if body_obj is None:
            body_obj = {}
        s = json.dumps(body_obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        return TelemetryService._b64(hashlib.sha256(s).digest())

    def _sign(self, method: str, path: str, ts: int, nonce: str, body_obj) -> str:
        """
        Create HMAC signature for request.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: URL path (e.g., /api/heartbeat)
            ts: Unix timestamp
            nonce: Random nonce string
            body_obj: Request body as dict

        Returns:
            Base64-encoded HMAC signature
        """
        secret = base64.b64decode(self.installation_secret)
        canonical = "\n".join([
            method.upper(),
            path,
            str(ts),
            nonce,
            self._body_hash(body_obj)
        ])
        mac = hmac.new(secret, canonical.encode("utf-8"), hashlib.sha256).digest()
        return self._b64(mac)

    def _make_authenticated_request(self, method: str, path: str, body_obj=None, timeout=10):
        """
        Make an authenticated request to the API.

        Args:
            method: HTTP method
            path: URL path
            body_obj: Request body (for POST/PUT)
            timeout: Request timeout in seconds

        Returns:
            Response object or None if failed
        """
        try:
            url = f"{self.api_base_url}{path}"
            ts = int(time.time())
            nonce = str(uuid.uuid4())
            signature = self._sign(method, path, ts, nonce, body_obj)

            headers = {
                'Content-Type': 'application/json',
                'X-Client-Id': self.installation_id,
                'X-Timestamp': str(ts),
                'X-Nonce': nonce,
                'X-Signature': signature
            }

            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, json=body_obj, timeout=timeout)
            elif method.upper() == 'PUT':
                response = requests.put(url, headers=headers, json=body_obj, timeout=timeout)
            else:
                log.error(f"Unsupported HTTP method: {method}")
                return None

            return response

        except requests.exceptions.RequestException as e:
            log.debug(f"Request to {path} failed: {e}")
            return None
        except Exception as e:
            log.error(f"Error making authenticated request: {e}")
            return None

    def register(self):
        """
        Register this installation with the API.
        Only called when my_call is set.
        """
        if self.registered:
            log.debug("Already registered, skipping registration")
            return True

        if not self.my_call:
            log.debug("Cannot register without my_call")
            return False

        if not self.installation_id or not self.installation_secret:
            self._generate_credentials()

        try:
            # Simple registration with installation_id
            # The server will hash and store the secret
            body = {
                'installation_id': self.installation_id,
                'installation_secret': self.installation_secret,
                'callsign': self.my_call
            }

            url = f"{self.api_base_url}/register"
            response = requests.post(url, json=body, timeout=10)

            if response.status_code == 200 or response.status_code == 201:
                self.registered = True
                self._save_config()
                log.info(f"Successfully registered with API: {self.installation_id}")
                return True
            elif response.status_code == 409:
                # Already registered
                self.registered = True
                self._save_config()
                log.info(f"Installation already registered: {self.installation_id}")
                return True
            else:
                log.warning(f"Registration failed with status {response.status_code}: {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            log.debug(f"Registration request failed (will retry later): {e}")
            return False
        except Exception as e:
            log.error(f"Error during registration: {e}")
            return False

    def update_user_data(self, my_call=None, my_grid=None, band=None, ip_address=None):
        """
        Update user data that will be sent in heartbeats.

        Args:
            my_call: User's callsign
            my_grid: User's grid square
            band: Current band
            ip_address: User's IP address
        """
        if my_call is not None:
            self.my_call = my_call

            # Try to register if we have a callsign but haven't registered yet
            if not self.registered:
                self.register()

        if my_grid is not None:
            self.my_grid = my_grid

        if band is not None:
            self.band = band

        if ip_address is not None:
            self.ip_address = ip_address

    def send_heartbeat(self):
        """Send a heartbeat to the API with current user data."""
        if not self.registered:
            # Try to register first
            if not self.register():
                return False

        if not self.my_call:
            log.debug("Cannot send heartbeat without callsign")
            return False

        try:
            body = {
                'callsign': self.my_call,
                'grid': self.my_grid or '',
                'band': self.band or '',
                'ip_address': self.ip_address or ''
            }

            response = self._make_authenticated_request('POST', '/heartbeat', body)

            if response and response.status_code in [200, 201]:
                log.debug(f"Heartbeat sent successfully")
                return True
            elif response:
                log.warning(f"Heartbeat failed with status {response.status_code}: {response.text}")
                return False
            else:
                log.debug("Heartbeat request failed (will retry)")
                return False

        except Exception as e:
            log.error(f"Error sending heartbeat: {e}")
            return False

    def _heartbeat_loop(self):
        """Background thread that sends heartbeats every 60 seconds."""
        log.info("Heartbeat loop started")

        while self.running:
            try:
                self.send_heartbeat()
            except Exception as e:
                log.error(f"Error in heartbeat loop: {e}")

            # Wait 60 seconds, but check every second if we should stop
            for _ in range(60):
                if not self.running:
                    break
                time.sleep(1)

        log.info("Heartbeat loop stopped")

    def start(self):
        """Start the telemetry service and begin sending heartbeats."""
        if self.running:
            log.warning("Telemetry service already running")
            return

        self.running = True
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()
        log.info("Telemetry service started")

    def stop(self):
        """Stop the telemetry service."""
        if not self.running:
            return

        log.info("Stopping telemetry service...")
        self.running = False

        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=5)

        log.info("Telemetry service stopped")
