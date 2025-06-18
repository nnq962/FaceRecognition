import os
import requests
from dotenv import load_dotenv
from utils.logger_config import LOGGER
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class EduLiveAPI:
    def __init__(self):
        load_dotenv()
        self.base_url = "https://school-beta-api.edulive.net/api/public"
        self.token = os.getenv("X_API_TOKEN")

        if not self.token:
            LOGGER.error("Missing X_API_TOKEN in environment variables")
            raise ValueError("Missing X_API_TOKEN")

        self.headers = {
            "X-Api-Token": self.token,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        }

        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def get_classes(self, server_id):
        """
        Lấy classes theo server_id
        """
        url = f"{self.base_url}/classes/{server_id}"
        return self._get(url, f"class {server_id}")

    def get_pupils_by_class_id(self, class_id):
        """
        Lấy pupils của class_id
        """
        url = f"{self.base_url}/classes/list-pupils/{class_id}"
        return self._get(url, f"pupils of class {class_id}")
    
    def get_staffs(self, server_id):
        """
        Lấy staffs của server_id
        """
        url = f"{self.base_url}/staffs/{server_id}"
        return self._get(url, f"staffs of server {server_id}")

    def _get(self, url, description):
        try:
            response = self.session.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            LOGGER.info(f"Fetched {description} successfully")
            return data
        except requests.HTTPError as e:
            LOGGER.error(f"HTTP error while fetching {description}: {e.response.status_code} - {e.response.text}")
        except requests.RequestException as e:
            LOGGER.error(f"Request error while fetching {description}: {e}")
        except Exception as e:
            LOGGER.error(f"Unexpected error while fetching {description}: {e}")

api = EduLiveAPI()