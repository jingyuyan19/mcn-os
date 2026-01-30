# Sanity Client SSL Fix Summary

## Problem
- Sanity MCP server was enabled (41 tools, ~60k tokens per request)
- CLAUDE.md mentioned SSL issues as a workaround reason
- Python Sanity client lacked explicit SSL configuration

## Solution Implemented

### 1. Enhanced SSL Configuration (`middleware/lib/sanity_client.py`)

**Changes**:
- Added explicit certifi CA bundle usage
- Implemented `requests.Session` with persistent connections
- Added retry logic (3 attempts, exponential backoff)
- Added 30-second timeouts on all requests
- Enhanced error logging with SSL details

**Benefits**:
- Robust SSL certificate verification
- Automatic retry on transient failures (429, 500, 502, 503, 504)
- Better error diagnostics
- Connection reuse for performance

### 2. Updated Requirements (`middleware/requirements.txt`)

**Added**:
```txt
requests>=2.32.0
certifi>=2026.1.4  # SSL CA certificates
urllib3>=2.0.0     # Required for retry logic
```

**Why**: Ensures SSL certificates stay current and retry logic is available

### 3. Disabled Sanity MCP Server (`~/.claude.json`)

**Impact**: Saves ~60,000 tokens per request

**Before**:
```json
"mcpServers": {
  "Sanity": {
    "type": "http",
    "url": "https://mcp.sanity.io"
  }
}
```

**After**: Section removed entirely

### 4. Updated Documentation (`CLAUDE.md`)

- Removed "Sanity MCP Workaround for SSL Issues" section
- Added "Sanity Client SSL Configuration" section
- Removed SSL errors from Error Recovery table
- Updated with proper usage examples

## Testing

**Test Script**: `middleware/test_ssl_config.py`

**Results**:
```
✅ Client initialized:
   Base URL: https://4t6f8tmh.api.sanity.io/v2024-01-01
   Session type: Session
   SSL verify: /usr/local/lib/python3.11/site-packages/certifi/cacert.pem
   Adapters: ['https://', 'http://']

✅ Query successful!
✅ Patch successful!
✅ All SSL tests passed! Client is robust.
```

## Token Savings

**Before**: ~60k tokens overhead from 41 Sanity MCP tools
**After**: 0 tokens (MCP server disabled)

**Annual savings** (assuming 1000 requests/day):
- Tokens saved: 60k × 1000 × 365 = ~22 billion tokens/year
- Cost savings: Significant reduction in API costs

## Recommendations

1. ✅ **Use Python client exclusively** - No need for MCP fallback
2. ✅ **Keep certifi updated** - Run `pip install --upgrade certifi` periodically
3. ✅ **Monitor logs** - Check for SSL warnings in production
4. ⚠️ **Consider connection pooling** - For high-volume scenarios

## Migration Guide

**No changes needed!** The enhanced client is backwards compatible.

All existing code using `get_sanity_client()` will automatically benefit from:
- SSL improvements
- Retry logic
- Better error handling

## Files Modified

1. `middleware/lib/sanity_client.py` - Enhanced SSL configuration
2. `middleware/requirements.txt` - Added SSL dependencies
3. `CLAUDE.md` - Updated documentation
4. `~/.claude.json` - Disabled MCP server
5. `middleware/test_ssl_config.py` - New test file

## Verification

Run the test to verify SSL is working:
```bash
docker exec mcn_core python /app/middleware/test_ssl_config.py
```

## Rollback (if needed)

If issues occur:
```bash
# Re-enable MCP server
# Edit ~/.claude.json and add back:
"mcpServers": {
  "Sanity": {
    "type": "http",
    "url": "https://mcp.sanity.io"
  }
}
```

**Status**: ✅ COMPLETE - SSL fixed, MCP disabled, tokens saved
