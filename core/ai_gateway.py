"""Single official entry point for all AI — re-exports core.ai."""

from core.ai import (
    AIInsightResult,
    PROVIDERS,
    build_local_fallback_insight,
    cache_key,
    call_provider,
    extract_json_block,
    get_financial_insights,
    load_ai_config_from_settings,
    parse_ai_response,
    provider_is_configured,
    read_cache,
    request_financial_insights,
    resolve_provider_api_key,
    resolve_provider_model,
    test_connection,
    write_cache,
)

# Backward-compatible private aliases used in tests
_cache_key = cache_key
_read_cache = read_cache
_write_cache = write_cache
_call_provider = call_provider
_parse_ai_response = parse_ai_response
_extract_json_block = extract_json_block
from core.ai.cache import CACHE_DIR as _CACHE_DIR

__all__ = [
    "AIInsightResult",
    "PROVIDERS",
    "build_local_fallback_insight",
    "get_financial_insights",
    "load_ai_config_from_settings",
    "provider_is_configured",
    "request_financial_insights",
    "resolve_provider_api_key",
    "resolve_provider_model",
    "test_connection",
]