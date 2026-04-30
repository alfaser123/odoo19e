from . import models  # noqa

def _patch_llm_api_service_timeout():
    from odoo.addons.ai.utils.llm_api_service import LLMApiService

    if getattr(LLMApiService, "_ai_timeout_patched", False):
        return

    original_request = LLMApiService._request

    def _request_patched(
        self, method: str, endpoint: str, headers: dict[str, str], body: dict,
        data=None, files=None, params=None,
        base_url=None, timeout: int = 30
    ):
        cfg = self.env["ir.config_parameter"].sudo().get_param(
            "ai.request_timeout_seconds", "90"
        )
        try:
            cfg_timeout = int(cfg)
        except Exception:
            cfg_timeout = 90

        eff_timeout = cfg_timeout if timeout == 30 else timeout

        return original_request(
            self,
            method=method,
            endpoint=endpoint,
            headers=headers,
            body=body,
            data=data,
            files=files,
            params=params,
            base_url=base_url,
            timeout=eff_timeout,
        )

    LLMApiService._request = _request_patched
    LLMApiService._ai_timeout_patched = True

_patch_llm_api_service_timeout()
