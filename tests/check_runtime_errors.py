"""Runtime error policy fixtures; no claim of live jobs/3D service integration."""
import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "critic"))
from runtime_errors import (RuntimeReportedError, RuntimeUnreachableError,
                            check_runtime_response, describe_3d_result,
                            execute_runtime_request)


def refusal(code="class_carrier_unsupported", status=409, **metadata):
    return RuntimeReportedError({"error": {"message": "Server reason", "type": "invalid_request_error", "code": code}, "meterless": metadata}, status)


class Messages(unittest.TestCase):
    def test_server_message_always_first(self):
        self.assertEqual(str(refusal("unknown")), "Server reason")

    def test_server_fix_wins(self):
        error = refusal("mesh_level_unavailable", fix=["Seat Paint", "Choose finished"], chat_carrier=True)
        self.assertEqual(str(error), "Server reason\nSeat Paint\nChoose finished")
        self.assertEqual((error.code, error.status, error.fix, error.chatCarrier), ("mesh_level_unavailable", 409, ["Seat Paint", "Choose finished"], True))

    def test_explicit_empty_fix_suppresses_hint(self):
        self.assertEqual(str(refusal("mesh_level_unavailable", fix=[])), "Server reason")

    def test_carrier_code_never_claims_machine_limitation(self):
        self.assertEqual(str(refusal()), "Server reason")

    def test_carrier_false_suppresses_code_hint(self):
        self.assertEqual(str(refusal("mesh_level_unavailable", chat_carrier=False)), "Server reason")

    def test_authentication_statuses_append_token_instruction(self):
        for status in (401, 403):
            with self.subTest(status=status):
                self.assertEqual(str(refusal(status=status, fix=["Server fix"])), "Server reason\nServer fix\nPaste the runtime's access token in Settings.")

    def test_mesh_and_texture_are_resident_only(self):
        for class_name in ("mesh", "texture"):
            with self.subTest(class_name=class_name):
                self.assertIn("Seat the resident 3D lane", str(refusal("class_not_ready", **{"class": class_name})))
                error = refusal("class_not_ready", **{"class": class_name, "fix": ["Seat Shape", "Seat Paint"]})
                self.assertEqual(str(error), "Server reason\nSeat Shape\nSeat Paint")
                self.assertNotIn("retry", str(error).lower())

    def test_paint_lane_missing_on_both_paths(self):
        for status in (503, 409):
            with self.subTest(status=status):
                self.assertIn("no Paint lane is seated", str(refusal("mesh_level_unavailable", status)))

    def test_rate_limit_asks_for_key_without_retry(self):
        error = refusal("auth_rate_limited", 429)
        self.assertIn("Repeated invalid keys", str(error))
        self.assertIn("access token", str(error))
        self.assertFalse(error.retry_allowed)

    def test_completed_partial_model_is_not_painted(self):
        self.assertEqual(describe_3d_result(dict(status="completed", level="finished", paint={"error": {"message": "Paint ran out of memory"}})), "finished, not painted: Paint ran out of memory")
        self.assertEqual(describe_3d_result(dict(status="completed", level="finished")), "finished")
        self.assertEqual(describe_3d_result(dict(status="completed", level="painted")), "painted")

    def test_http_error_keeps_nested_metadata(self):
        response = httpx.Response(409, json={"error": {"message": "Unsupported route", "type": "invalid_request_error", "code": "class_no_route", "meterless": {"fix": ["Use jobs"], "chat_carrier": False}}})
        with self.assertRaises(RuntimeReportedError) as caught:
            check_runtime_response(response)
        error = caught.exception
        self.assertEqual(error.fix, ["Use jobs"])
        self.assertIs(error.chatCarrier, False)
        self.assertEqual(error.as_openai_error()["error"]["code"], "class_no_route")
        self.assertTrue(error.as_openai_error()["error"]["message"].startswith("Unsupported route"))


class Routing(unittest.IsolatedAsyncioTestCase):
    async def invoke(self, request, routes, cloud=None):
        self.invalidate = AsyncMock()
        self.discover = AsyncMock(return_value=routes)
        return await execute_runtime_request(request, "/chat", base="http://fixture/v1", invalidate=self.invalidate, discover=self.discover, cloud=cloud)

    async def test_replan_each_ambiguous_refusal_to_jobs_once(self):
        for error in (refusal(), refusal("class_no_route"), refusal("unknown", chat_carrier=False)):
            with self.subTest(code=error.code):
                request = AsyncMock(side_effect=[error, "job"])
                self.assertEqual(await self.invoke(request, {"jobs": "/jobs"}), "job")
                self.assertEqual(request.await_args_list[1].args, ("/jobs",))
                self.invalidate.assert_awaited_once()
                self.discover.assert_awaited_once()

    async def test_no_jobs_shows_original_server_error(self):
        for error in (refusal(), refusal("class_no_route")):
            request = AsyncMock(side_effect=error)
            with self.assertRaises(RuntimeReportedError) as caught:
                await self.invoke(request, {})
            self.assertIs(caught.exception, error)
            request.assert_awaited_once()
            self.discover.assert_awaited_once()

    async def test_repeated_jobs_refusal_cannot_loop_or_fall_back(self):
        request = AsyncMock(side_effect=[refusal(), refusal("class_no_route")])
        cloud = AsyncMock()
        with self.assertRaises(RuntimeReportedError):
            await self.invoke(request, {"jobs": "/jobs"}, cloud)
        self.assertEqual(request.await_count, 2)
        self.discover.assert_awaited_once()
        cloud.assert_not_awaited()

    async def test_same_route_does_not_retry(self):
        request = AsyncMock(side_effect=refusal())
        with self.assertRaises(RuntimeReportedError):
            await self.invoke(request, {"jobs": "/chat"})
        request.assert_awaited_once()

    async def test_only_transport_can_fall_back(self):
        cloud = AsyncMock(return_value="cloud result")
        for failure in (httpx.ConnectError("offline"), httpx.ReadTimeout("timeout")):
            self.assertEqual(await self.invoke(AsyncMock(side_effect=failure), {}, cloud), "cloud result")
        self.assertEqual(cloud.await_count, 2)

    async def test_typed_rate_limit_and_server_failure_never_fall_back(self):
        for error in (refusal("auth_rate_limited", 429), refusal("mesh_level_unavailable", 503), refusal("class_not_ready", 503)):
            cloud = AsyncMock()
            request = AsyncMock(side_effect=error)
            with self.assertRaises(RuntimeReportedError) as caught:
                await self.invoke(request, {}, cloud)
            self.assertEqual(caught.exception.as_openai_error()["error"]["message"], str(error))
            cloud.assert_not_awaited()
            request.assert_awaited_once()
            self.discover.assert_not_awaited()

    async def test_network_failure_offers_runtime_actions(self):
        with self.assertRaises(RuntimeUnreachableError) as caught:
            await self.invoke(AsyncMock(side_effect=httpx.ConnectError("offline")), {})
        error = caught.exception
        self.assertIn("http://fixture/v1", str(error))
        self.assertEqual(error.actions, ("Start the runtime", "Run Auto Detect"))
        self.assertEqual((error.code, error.status, error.fix, error.chatCarrier), ("runtime_unreachable", None, [], None))

    async def test_programming_error_does_not_fall_back(self):
        cloud = AsyncMock()
        with self.assertRaises(ValueError):
            await self.invoke(AsyncMock(side_effect=ValueError("invalid response")), {}, cloud)
        cloud.assert_not_awaited()


if __name__ == "__main__":
    unittest.main(verbosity=2)
