"""HTTP client for transmitting observation batches to the Home Lab FastAPI backend."""

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from noop_agent.sync.retry import parse_retry_after

logger = logging.getLogger(__name__)

USER_AGENT = "NOOP-Windows-Collector/1.0.0"


@dataclass
class IngestResult:
    """Result of an ingestion batch upload."""

    success: bool
    status_code: int
    batch_id: str
    accepted: int = 0
    duplicates: int = 0
    rejected: int = 0
    message: str = ""
    retry_after: Optional[float] = None
    auth_error: bool = False
    rate_limited: bool = False
    server_error: bool = False
    network_error: bool = False
    response_payload: Optional[Dict[str, Any]] = None
    error_detail: Optional[str] = None


class BatchUploader:
    """Uploads staged observation batches to the Home Lab server."""

    def __init__(
        self,
        server_url: str,
        token: Optional[str] = None,
        timeout_seconds: float = 15.0,
    ):
        clean_url = server_url.rstrip("/")
        if not clean_url.endswith("/ingest/batches"):
            if clean_url.endswith("/api/v1"):
                self.endpoint_url = f"{clean_url}/ingest/batches"
            else:
                self.endpoint_url = f"{clean_url}/api/v1/ingest/batches"
        else:
            self.endpoint_url = clean_url

        self.token = token
        self.timeout_seconds = timeout_seconds

    def _build_request_payload(
        self,
        batch_id: str,
        device_id: str,
        records: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Construct the IngestBatchRequest JSON payload."""
        # Clean each record to match server IngestRecord schema
        cleaned_records = []
        for r in records:
            cleaned = {
                "record_id": r["record_id"],
                "type": r.get("type", "unknown"),
                "timestamp": r["timestamp"],
                "reception_timestamp": r.get("reception_timestamp"),
                "data_origin": r.get("data_origin", "live"),
                "validation_status": r.get("validation_status", "valid"),
                "protocol_version": r.get("protocol_version", 4),
                "decoder_version": r.get("decoder_version", "1.0.0"),
                "raw_frame_hex": r.get("raw_frame_hex"),
                "char_uuid": r.get("char_uuid"),
                "inner_type": r.get("inner_type"),
                "value": r.get("value"),
                "unit": r.get("unit"),
                "source": r.get("source"),
                "metadata": r.get("metadata"),
            }
            cleaned_records.append(cleaned)

        return {
            "schema_version": 1,
            "device_id": device_id,
            "batch_id": batch_id,
            "records": cleaned_records,
        }

    async def post_batch_async(
        self,
        batch_id: str,
        device_id: str,
        records: List[Dict[str, Any]],
    ) -> IngestResult:
        """Asynchronously upload a batch (using httpx if available, fallback to thread executor)."""
        import asyncio
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.post_batch, batch_id, device_id, records)

    def post_batch(
        self,
        batch_id: str,
        device_id: str,
        records: List[Dict[str, Any]],
    ) -> IngestResult:
        """Synchronously upload a batch of records with full error classification."""
        payload = self._build_request_payload(batch_id, device_id, records)
        body_bytes = json.dumps(payload).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        req = Request(
            self.endpoint_url,
            data=body_bytes,
            headers=headers,
            method="POST",
        )

        try:
            with urlopen(req, timeout=self.timeout_seconds) as resp:
                status_code = resp.status
                resp_bytes = resp.read()
                try:
                    resp_json = json.loads(resp_bytes.decode("utf-8"))
                except Exception:
                    resp_json = {}

                return IngestResult(
                    success=True,
                    status_code=status_code,
                    batch_id=batch_id,
                    accepted=resp_json.get("accepted", len(records)),
                    duplicates=resp_json.get("duplicates", 0),
                    rejected=resp_json.get("rejected", 0),
                    message=resp_json.get("message", "Batch accepted"),
                    response_payload=resp_json,
                )

        except HTTPError as e:
            status_code = e.code
            retry_after = parse_retry_after(e.headers.get("Retry-After") if e.headers else None)
            err_msg = ""
            resp_json = None
            try:
                err_bytes = e.read()
                resp_json = json.loads(err_bytes.decode("utf-8"))
                err_msg = resp_json.get("detail", str(resp_json))
            except Exception:
                err_msg = str(e)

            auth_error = status_code in (401, 403)
            rate_limited = status_code == 429
            server_error = 500 <= status_code < 600

            if auth_error:
                logger.error("Authentication rejected by server (HTTP %d): %s", status_code, err_msg)
            elif rate_limited:
                logger.warning("Rate limit exceeded (HTTP 429). Retry-After: %s", retry_after)
            elif server_error:
                logger.warning("Server error during ingestion (HTTP %d): %s", status_code, err_msg)
            else:
                logger.warning("HTTP error during ingestion (HTTP %d): %s", status_code, err_msg)

            return IngestResult(
                success=False,
                status_code=status_code,
                batch_id=batch_id,
                retry_after=retry_after,
                auth_error=auth_error,
                rate_limited=rate_limited,
                server_error=server_error,
                response_payload=resp_json,
                error_detail=err_msg,
            )

        except URLError as e:
            logger.warning("Network connection failure during ingestion to %s: %s", self.endpoint_url, e)
            return IngestResult(
                success=False,
                status_code=0,
                batch_id=batch_id,
                network_error=True,
                error_detail=str(e),
            )

        except Exception as e:
            logger.error("Unexpected error transmitting batch %s: %s", batch_id, e)
            return IngestResult(
                success=False,
                status_code=0,
                batch_id=batch_id,
                network_error=True,
                error_detail=str(e),
            )
