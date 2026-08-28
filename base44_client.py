"""
ShimiStudio Base44 Client v2.0
Complete Base44 API client for RenderJob management.
Communicates with the deployed Base44 backend function 'shimiStudioAPI'
with automatic fallback to direct entity REST API if configured.
"""

import os
import sys
import time
import json
import base64
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
import requests

from config import (
    BASE44_APP_ID,
    BASE44_API_URL,
    BASE44_ENTITY,
    BASE44_TOKEN,
    WORKER_ID,
    setup_logger,
)

logger = setup_logger("base44_client")


class Base44Client:
    """
    Complete API client for Base44 RenderJob management.
    Uses the deployed backend function 'shimiStudioAPI' primarily,
    with fallback to direct entity REST API.
    """

    def __init__(self, app_id: str = BASE44_APP_ID, entity_name: str = "RenderJob"):
        self.app_id = app_id or BASE44_APP_ID
        self.entity_name = entity_name or BASE44_ENTITY
        self.token = BASE44_TOKEN or os.environ.get("BASE44_TOKEN", "")
        self.backend_url = f"https://solas-{self.app_id}.base44.app/functions/shimiStudioAPI"
        self.api_url = (BASE44_API_URL or "https://api.base44.com").rstrip("/")

    def _request(self, method: str, path: str, **kwargs) -> dict:
        """
        Makes HTTP request directly to Base44 REST API, handling authorization and errors.
        """
        if path.startswith("http://") or path.startswith("https://"):
            url = path
        else:
            url = f"{self.api_url}/{path.lstrip('/')}"

        headers = kwargs.pop("headers", {})
        if self.token and "Authorization" not in headers:
            headers["Authorization"] = f"Bearer {self.token}"
        headers.setdefault("Content-Type", "application/json")

        logger.debug(f"Direct API Request: {method} {url}")
        response = requests.request(method, url, headers=headers, **kwargs)
        response.raise_for_status()
        if response.text.strip():
            return response.json()
        return {}

    def _call_backend(self, action: str, **payload) -> dict:
        """
        Sends action payload to deployed backend function shimiStudioAPI.
        If backend fails or is unavailable, falls back to direct REST API if token exists.
        """
        body = {"action": action, **payload}
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        try:
            resp = requests.post(self.backend_url, json=body, headers=headers, timeout=30)
            if resp.status_code == 200:
                res = resp.json()
                if isinstance(res, dict) and res.get("success") is False:
                    raise RuntimeError(res.get("error", f"Backend function returned failure for action '{action}'"))
                return res
            else:
                logger.warning(f"Backend function HTTP {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.warning(f"Backend call action '{action}' failed: {e}. Attempting fallback...")

        return self._direct_fallback(action, payload)

    def _direct_fallback(self, action: str, payload: dict) -> dict:
        """Fallback methods using direct Entity REST API."""
        entity_path = f"api/apps/{self.app_id}/entities/{self.entity_name}"

        if action == "get_pending":
            limit = payload.get("limit", 5)
            url = f"{entity_path}?query={json.dumps({'status': 'pending'})}&sort=-priority&limit={limit}"
            res = self._request("GET", url)
            data = res if isinstance(res, list) else res.get("items", [])
            return {"success": True, "data": data}

        elif action == "claim":
            job_id = payload.get("job_id")
            worker_id = payload.get("worker_id", WORKER_ID)
            now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            patch_data = {
                "worker_id": worker_id,
                "status": "processing",
                "started_at": now_str,
            }
            res = self._request("PATCH", f"{entity_path}/{job_id}", json=patch_data)
            return {"success": True, "data": res}

        elif action == "update_progress":
            job_id = payload.get("job_id")
            patch_data = {"progress": payload.get("progress", 0)}
            res = self._request("PATCH", f"{entity_path}/{job_id}", json=patch_data)
            return {"success": True, "data": res}

        elif action == "complete":
            job_id = payload.get("job_id")
            now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            patch_data = {
                "status": "completed",
                "output_url": payload.get("output_url", ""),
                "progress": 100,
                "completed_at": now_str,
            }
            if "result_type" in payload:
                patch_data["result_type"] = payload["result_type"]
            res = self._request("PATCH", f"{entity_path}/{job_id}", json=patch_data)
            return {"success": True, "data": res}

        elif action == "fail":
            job_id = payload.get("job_id")
            patch_data = {
                "status": "failed",
                "error_message": payload.get("error_message", "Unknown error"),
            }
            res = self._request("PATCH", f"{entity_path}/{job_id}", json=patch_data)
            return {"success": True, "data": res}

        elif action == "get_job":
            job_id = payload.get("job_id")
            res = self._request("GET", f"{entity_path}/{job_id}")
            return {"success": True, "data": res}

        elif action == "create_job":
            job_data = {
                "job_type": payload.get("job_type"),
                "prompt": payload.get("prompt"),
                "negative_prompt": payload.get("negative_prompt", ""),
                "parameters": json.dumps(payload.get("parameters", {})) if isinstance(payload.get("parameters"), dict) else (payload.get("parameters") or "{}"),
                "status": "pending",
                "priority": payload.get("priority", 1),
                "progress": 0,
            }
            for k in [
                "face_images",
                "reference_image",
                "face_swap_target",
                "voice_text",
                "camera_frames",
                "workflow_id",
                "client_id",
                "result_type",
            ]:
                if k in payload and payload[k] is not None:
                    job_data[k] = payload[k]
            res = self._request("POST", entity_path, json=job_data)
            return {"success": True, "data": res}

        raise RuntimeError(f"Action '{action}' could not be executed via direct API fallback (no valid token/endpoint).")

    def get_pending_jobs(self, limit: int = 5) -> List[dict]:
        """GET pending jobs (status='pending'), sorted by priority desc, limited."""
        res = self._call_backend("get_pending", limit=limit, worker_id=WORKER_ID)
        if isinstance(res, dict):
            if "data" in res and isinstance(res["data"], list):
                return res["data"]
            if "jobs" in res and isinstance(res["jobs"], list):
                return res["jobs"]
            if res.get("success") and isinstance(res.get("result"), list):
                return res["result"]
        if isinstance(res, list):
            return res
        return []

    def claim_job(self, job_id: str, worker_id: str = WORKER_ID) -> dict:
        """PATCH job with worker_id and status='processing' and started_at."""
        res = self._call_backend("claim", job_id=job_id, worker_id=worker_id)
        if isinstance(res, dict):
            return res.get("data", res)
        return res

    def update_progress(self, job_id: str, progress: int) -> dict:
        """PATCH job with progress (0-100)."""
        res = self._call_backend("update_progress", job_id=job_id, progress=progress)
        if isinstance(res, dict):
            return res.get("data", res)
        return res

    def complete_job(self, job_id: str, output_url: str, result_type: str = "image") -> dict:
        """PATCH with status='completed', output_url, completed_at, progress=100."""
        res = self._call_backend(
            "complete",
            job_id=job_id,
            output_url=output_url,
            result_type=result_type,
            progress=100,
            status="completed",
        )
        if isinstance(res, dict):
            return res.get("data", res)
        return res

    def fail_job(self, job_id: str, error_message: str) -> dict:
        """PATCH with status='failed', error_message."""
        res = self._call_backend("fail", job_id=job_id, error_message=error_message, status="failed")
        if isinstance(res, dict):
            return res.get("data", res)
        return res

    def get_job(self, job_id: str) -> dict:
        """GET single job."""
        res = self._call_backend("get_job", job_id=job_id)
        if isinstance(res, dict):
            return res.get("data", res)
        return res

    def create_job(
        self,
        job_type: str,
        prompt: str,
        parameters: Optional[dict] = None,
        priority: int = 1,
        **kwargs,
    ) -> dict:
        """POST new job."""
        payload = {
            "job_type": job_type,
            "prompt": prompt,
            "parameters": parameters or {},
            "priority": priority,
            **kwargs,
        }
        res = self._call_backend("create_job", **payload)
        if isinstance(res, dict):
            return res.get("data", res)
        return res

    def upload_output(self, filepath: str) -> str:
        """
        Upload file to Base44 storage, return URL (use base64 encode or multipart to backend, with public host fallback).
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Output file not found for upload: {filepath}")

        # Try base64 encode to backend function 'upload'
        try:
            with open(path, "rb") as f:
                b64_data = base64.b64encode(f.read()).decode("utf-8")

            ext = path.suffix.lstrip(".").lower()
            mime_type = "image/png"
            if ext in ("jpeg", "jpg"):
                mime_type = "image/jpeg"
            elif ext == "mp4":
                mime_type = "video/mp4"
            elif ext == "webm":
                mime_type = "video/webm"

            res = self._call_backend(
                "upload",
                filename=path.name,
                file_data=f"data:{mime_type};base64,{b64_data}",
                mime_type=mime_type,
            )
            url = None
            if isinstance(res, dict):
                url = res.get("url") or res.get("output_url") or (res.get("data", {}).get("url") if isinstance(res.get("data"), dict) else None)
            if url:
                logger.info(f"Uploaded file via Base44 backend: {url}")
                return url
        except Exception as e:
            logger.warning(f"Backend upload attempt failed: {e}. Trying fallback storage...")

        # Fallback 1: 0x0.st
        try:
            with open(path, "rb") as f:
                resp = requests.post("https://0x0.st", files={"file": (path.name, f)}, timeout=60)
                resp.raise_for_status()
                url = resp.text.strip()
                if url.startswith("http"):
                    logger.info(f"Uploaded via 0x0.st: {url}")
                    return url
        except Exception as e:
            logger.warning(f"0x0.st upload failed: {e}")

        # Fallback 2: catbox.moe
        try:
            with open(path, "rb") as f:
                files = {"reqType": (None, "fileupload"), "fileToUpload": (path.name, f)}
                resp = requests.post("https://catbox.moe/user/api.php", files=files, timeout=60)
                resp.raise_for_status()
                url = resp.text.strip()
                if url.startswith("http"):
                    logger.info(f"Uploaded via catbox.moe: {url}")
                    return url
        except Exception as e:
            logger.warning(f"catbox.moe upload failed: {e}")

        raise RuntimeError(f"Failed to upload output file {path.name} to any endpoint.")
