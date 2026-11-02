"""Runtime HTTP error policy, independent of endpoint discovery protocols."""
from collections.abc import Mapping

import httpx


class RuntimeReportedError(RuntimeError):
    def __init__(self, payload, status, *, class_name=None):
        error = payload.get("error", {})
        if not isinstance(error, Mapping):
            error = {"message": str(error)}
        metadata = error.get("meterless", payload.get("meterless", {}))
        if not isinstance(metadata, Mapping):
            metadata = {}
        self.server_message = str(error.get("message") or f"Runtime request failed ({status}).")
        self.type = error.get("type") or "runtime_error"
        self.code = error.get("code")
        self.status = status
        self.fix = list(metadata.get("fix") or [])
        self.chatCarrier = metadata.get("chat_carrier")
        self.class_name = metadata.get("class", class_name)
        self.routes = metadata.get("routes", {})
        self.meterless = dict(metadata)
        self.carrier_refusal = self.code == "class_carrier_unsupported" or self.chatCarrier is False
        self.should_replan = self.carrier_refusal or self.code == "class_no_route"
        self.retry_allowed = False
        parts = [self.server_message]
        if "fix" in metadata:
            parts.extend(str(item) for item in self.fix)
        elif not self.carrier_refusal:
            hint = self._hint()
            if hint:
                parts.append(hint)
        if status in (401, 403):
            parts.append("Paste the runtime's access token in Settings.")
        super().__init__("\n".join(parts))

    def _hint(self):
        if self.code == "class_not_ready" and self.class_name in ("mesh", "texture"):
            return "Seat the resident 3D lane required for this class."
        if self.code == "mesh_level_unavailable":
            return "A painted model was requested, but no Paint lane is seated."
        if self.code == "auth_rate_limited" and self.status == 429:
            return "Repeated invalid keys were received from the network. Enter the runtime's access token."
        return None

    def as_openai_error(self):
        return {"error": {"message": str(self), "type": self.type, "code": self.code},
                "meterless": dict(self.meterless)}


class RuntimeUnreachableError(RuntimeError):
    def __init__(self, base):
        self.code = "runtime_unreachable"
        self.status = None
        self.fix = []
        self.chatCarrier = None
        self.actions = ("Start the runtime", "Run Auto Detect")
        super().__init__(f"The runtime isn't reachable at {base}. Start the runtime or Run Auto Detect.")


def check_runtime_response(response, *, class_name=None):
    if response.is_success:
        return
    try:
        body = response.json()
    except ValueError:
        body = {"error": {"message": response.text or f"Runtime request failed ({response.status_code})."}}
    if not isinstance(body, Mapping):
        body = {"error": {"message": response.text}}
    raise RuntimeReportedError(body, response.status_code, class_name=class_name)


async def execute_runtime_request(request, route, *, base, invalidate, discover, cloud=None):
    """Callbacks own protocol details. At most one discovery and one jobs attempt."""
    try:
        try:
            return await request(route)
        except RuntimeReportedError as error:
            if not error.should_replan:
                raise
            await invalidate()
            routes = await discover()
            jobs = routes.get("jobs")
            if not jobs or jobs == route:
                raise error
            return await request(jobs)
    except httpx.TransportError as error:
        if cloud is not None:
            return await cloud()
        raise RuntimeUnreachableError(base) from error


def describe_3d_result(job):
    level = job.get("level")
    paint_error = (job.get("paint") or {}).get("error")
    if job.get("status") == "completed" and level == "finished" and paint_error:
        if isinstance(paint_error, Mapping):
            reason = paint_error.get("message") or str(dict(paint_error))
        else:
            reason = str(paint_error)
        return f"finished, not painted: {reason}"
    return str(level or job.get("status") or "Unknown 3D job status")
