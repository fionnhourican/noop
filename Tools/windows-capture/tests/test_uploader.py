"""Unit tests for BatchUploader and HTTP ingestion protocol."""

import asyncio
import io
import json
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

from noop_agent.sync.uploader import BatchUploader, IngestResult


class TestUploader(unittest.TestCase):
    """Test suite for HTTP batch uploader."""

    def test_url_normalization(self):
        up1 = BatchUploader("http://localhost:8080")
        self.assertEqual(up1.endpoint_url, "http://localhost:8080/api/v1/ingest/batches")

        up2 = BatchUploader("http://localhost:8080/api/v1/")
        self.assertEqual(up2.endpoint_url, "http://localhost:8080/api/v1/ingest/batches")

        up3 = BatchUploader("http://localhost:8080/api/v1/ingest/batches")
        self.assertEqual(up3.endpoint_url, "http://localhost:8080/api/v1/ingest/batches")

    def test_build_request_payload(self):
        up = BatchUploader("http://localhost:8080", token="secret-token")
        records = [
            {
                "record_id": "rec-123",
                "type": "heart_rate",
                "timestamp": "2026-11-16T12:00:00Z",
                "reception_timestamp": "2026-11-16T12:00:01Z",
                "data_origin": "live",
                "validation_status": "valid",
                "protocol_version": 4,
                "decoder_version": "1.0.0",
                "raw_frame_hex": "aa0700...",
                "char_uuid": "2a37",
                "inner_type": 40,
                "value": 72,
                "unit": "bpm",
                "source": "ble",
                "metadata": {"rr": [820, 830]},
            }
        ]

        payload = up._build_request_payload("batch-999", "dev-4.0", records)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["device_id"], "dev-4.0")
        self.assertEqual(payload["batch_id"], "batch-999")
        self.assertEqual(len(payload["records"]), 1)
        self.assertEqual(payload["records"][0]["record_id"], "rec-123")
        self.assertEqual(payload["records"][0]["value"], 72)

    @patch("noop_agent.sync.uploader.urlopen")
    def test_successful_upload_200_ok(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 200
        resp_data = {
            "status": "success",
            "batch_id": "batch-1",
            "accepted": 5,
            "duplicates": 1,
            "rejected": 0,
            "message": "Batch processed successfully",
        }
        mock_resp.read.return_value = json.dumps(resp_data).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        up = BatchUploader("http://localhost:8080", token="test-token")
        res = up.post_batch("batch-1", "dev-1", [{"record_id": "r1", "timestamp": "2026-11-16T12:00:00Z"}])

        self.assertTrue(res.success)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.accepted, 5)
        self.assertEqual(res.duplicates, 1)
        self.assertEqual(res.rejected, 0)
        self.assertFalse(res.auth_error)
        self.assertFalse(res.rate_limited)

    @patch("noop_agent.sync.uploader.urlopen")
    def test_auth_error_401(self, mock_urlopen):
        err = HTTPError(
            url="http://localhost:8080",
            code=401,
            msg="Unauthorized",
            hdrs={},
            fp=io.BytesIO(b'{"detail": "Invalid or revoked bearer token"}'),
        )
        mock_urlopen.side_effect = err

        up = BatchUploader("http://localhost:8080", token="bad-token")
        res = up.post_batch("batch-1", "dev-1", [{"record_id": "r1", "timestamp": "2026-11-16T12:00:00Z"}])

        self.assertFalse(res.success)
        self.assertEqual(res.status_code, 401)
        self.assertTrue(res.auth_error)
        self.assertIn("Invalid or revoked bearer token", res.error_detail)

    @patch("noop_agent.sync.uploader.urlopen")
    def test_rate_limit_429_with_retry_after(self, mock_urlopen):
        err = HTTPError(
            url="http://localhost:8080",
            code=429,
            msg="Too Many Requests",
            hdrs={"Retry-After": "45"},
            fp=io.BytesIO(b'{"detail": "Rate limit exceeded"}'),
        )
        mock_urlopen.side_effect = err

        up = BatchUploader("http://localhost:8080")
        res = up.post_batch("batch-1", "dev-1", [{"record_id": "r1", "timestamp": "2026-11-16T12:00:00Z"}])

        self.assertFalse(res.success)
        self.assertEqual(res.status_code, 429)
        self.assertTrue(res.rate_limited)
        self.assertEqual(res.retry_after, 45.0)

    @patch("noop_agent.sync.uploader.urlopen")
    def test_server_error_503(self, mock_urlopen):
        err = HTTPError(
            url="http://localhost:8080",
            code=503,
            msg="Service Unavailable",
            hdrs={},
            fp=io.BytesIO(b'{"detail": "Database unavailable"}'),
        )
        mock_urlopen.side_effect = err

        up = BatchUploader("http://localhost:8080")
        res = up.post_batch("batch-1", "dev-1", [{"record_id": "r1", "timestamp": "2026-11-16T12:00:00Z"}])

        self.assertFalse(res.success)
        self.assertEqual(res.status_code, 503)
        self.assertTrue(res.server_error)

    @patch("noop_agent.sync.uploader.urlopen")
    def test_network_connection_error(self, mock_urlopen):
        mock_urlopen.side_effect = URLError("Connection refused")

        up = BatchUploader("http://localhost:8080")
        res = up.post_batch("batch-1", "dev-1", [{"record_id": "r1", "timestamp": "2026-11-16T12:00:00Z"}])

        self.assertFalse(res.success)
        self.assertEqual(res.status_code, 0)
        self.assertTrue(res.network_error)

    @patch("noop_agent.sync.uploader.urlopen")
    def test_async_post_batch(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b'{"status": "success", "accepted": 1}'
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        up = BatchUploader("http://localhost:8080")
        res = asyncio.run(
            up.post_batch_async("batch-1", "dev-1", [{"record_id": "r1", "timestamp": "2026-11-16T12:00:00Z"}])
        )
        self.assertTrue(res.success)
        self.assertEqual(res.status_code, 200)


if __name__ == "__main__":
    unittest.main()
