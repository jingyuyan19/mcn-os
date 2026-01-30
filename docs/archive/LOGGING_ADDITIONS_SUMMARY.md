# Comprehensive Structured Logging Implementation

## Overview

Added detailed structured logging to planning session components for improved observability and debugging. All logs use JSON-structured `extra={}` fields for easy parsing and traceability.

## Files Modified

### 1. `/mnt/data_ssd/mcn/middleware/lib/planning_session.py`

#### Session Lifecycle Logging

**Session Start** (Line 84-95)
```python
logger.info(
    "Planning session started",
    extra={
        "topic_id": topic_id,
        "artist_id": artist_id,
        "artist_name": artist_name,
        "topic_title": topic_title[:100],
        "threshold": threshold,
        "timestamp": start_time.isoformat(),
        "ir_report_size": len(ir_report)
    }
)
```
- Logs when planning session begins
- Includes topic and artist identifiers for traceability
- Records persona alignment threshold
- Captures IR report size for performance analysis

**Parallel Agent Execution Start** (Line 221-228)
```python
logger.info(
    "Starting parallel agent execution",
    extra={
        "topic_id": topic_id,
        "artist_id": artist_id,
        "agent_count": 4
    }
)
```
- Marks the beginning of 4-agent parallel execution
- Provides context for performance monitoring

#### Agent Execution Logging

**Individual Agent Completion** (Line 271-280)
```python
logger.info(
    "Agent execution completed",
    extra={
        "topic_id": topic_id,
        "artist_id": artist_id,
        "agent_name": name,
        "success": success,
        "output_size_bytes": output_size
    }
)
```
- Logs each agent's completion status
- Tracks output size for performance analysis
- Enables per-agent debugging

**Agent Failure** (Line 252-261)
```python
logger.error(
    "Agent execution failed",
    extra={
        "topic_id": topic_id,
        "artist_id": artist_id,
        "agent_name": name,
        "error": str(result)
    },
    exc_info=result
)
```
- Captures agent failures with full exception info
- Includes agent name for targeted debugging

**Parallel Execution Summary** (Line 285-294)
```python
logger.info(
    "Parallel agent execution completed",
    extra={
        "topic_id": topic_id,
        "artist_id": artist_id,
        "successful_agents": success_count,
        "total_agents": len(agent_names),
        "success_rate": round(success_count / len(agent_names), 2)
    }
)
```
- Provides aggregate metrics on agent execution
- Calculates success rate for monitoring

#### Persona Gate Logging

**Gate Failure** (Line 117-129)
```python
logger.warning(
    "Persona gate check failed",
    extra={
        "topic_id": topic_id,
        "artist_id": artist_id,
        "alignment_score": round(alignment_score, 3),
        "threshold": threshold,
        "gate_status": gate_status,
        "duration_seconds": round(duration, 2),
        "angle_suggestion": persona_result.get("angle_adjustment", ""),
        "voice_suggestions_count": len(persona_result.get("voice_suggestions", []))
    }
)
```
- WARNING level for gate failures
- Includes alignment score vs threshold comparison
- Logs suggested adjustments for content creators
- Tracks session duration

**Gate Success** (Line 146-155)
```python
logger.info(
    "Persona gate check passed",
    extra={
        "topic_id": topic_id,
        "artist_id": artist_id,
        "alignment_score": round(alignment_score, 3),
        "threshold": threshold,
        "gate_status": gate_status
    }
)
```
- Confirms gate passage with alignment metrics

#### Session Completion Logging

**Successful Completion** (Line 161-173)
```python
logger.info(
    "Planning session completed successfully",
    extra={
        "topic_id": topic_id,
        "artist_id": artist_id,
        "gate_passed": True,
        "duration_seconds": round(duration, 2),
        "hook_candidates_count": len(creative_brief.get("hookCandidates", [])),
        "viral_score": round(creative_brief.get("overallViralScore", 0), 3),
        "risk_level": creative_brief.get("riskLevel", "unknown"),
        "risk_factors_count": len(creative_brief.get("riskFactors", []))
    }
)
```
- INFO level for successful sessions
- Includes creative brief metrics
- Tracks viral score and risk assessment
- Logs session duration for performance analysis

**Exception Handling** (Line 186-195)
```python
logger.error(
    "Planning session failed with exception",
    extra={
        "topic_id": topic_id,
        "artist_id": artist_id,
        "error": str(e),
        "duration_seconds": round(duration, 2)
    },
    exc_info=True
)
```
- ERROR level with full exception traceback
- Includes session duration even on failure

---

### 2. `/mnt/data_ssd/mcn/middleware/lib/gemini_client.py`

#### Report Size Monitoring

**Large Report Warning** (Line 69-77)
```python
logger.warning(
    "Large research report detected",
    extra={
        "artist_id": artist_id,
        "artist_name": artist_name,
        "report_size_chars": report_size,
        "estimated_tokens": report_size // 4
    }
)
```
- WARNING level for reports exceeding 100K characters
- Estimates token count for context window planning
- Helps identify performance bottlenecks

#### Creative Brief Usage Logging

**Brief Applied** (Line 95-107)
```python
logger.info(
    "Creative brief applied to storyboard generation",
    extra={
        "artist_id": artist_id,
        "artist_name": artist_name,
        "alignment_score": round(alignment_score, 3),
        "viral_score": round(viral_score, 3),
        "risk_level": risk_level,
        "recommended_hook_type": recommended_hook.get("hookType", "unknown"),
        "hook_candidates_count": len(creative_brief.get("hookCandidates", [])),
        "engagement_hooks_count": len(creative_brief.get("engagementHooks", []))
    }
)
```
- INFO level when creative brief is used
- Logs key brief metrics:
  - Alignment score (persona fit)
  - Viral score (engagement potential)
  - Risk level (content safety)
  - Hook recommendations
  - Engagement hook count

**No Brief** (Line 109-116)
```python
logger.info(
    "Storyboard generation without creative brief",
    extra={
        "artist_id": artist_id,
        "artist_name": artist_name,
        "reason": "No creative brief provided"
    }
)
```
- INFO level when brief is not available
- Distinguishes between two execution paths

#### Storyboard Generation Results

**Success** (Line 192-205)
```python
logger.info(
    "Storyboard generated successfully",
    extra={
        "artist_id": artist_id,
        "artist_name": artist_name,
        "scene_count": len(storyboard),
        "total_duration_seconds": total_duration,
        "a_roll_scenes": a_roll_count,
        "b_roll_scenes": b_roll_count,
        "aspect_ratio": aspect_ratio,
        "style": style,
        "creative_brief_used": brief_used
    }
)
```
- INFO level for successful storyboard generation
- Logs scene composition metrics:
  - Total scene count
  - A-roll (host) vs B-roll (visual) breakdown
  - Total duration
  - Video format and style
  - Whether creative brief was used

**JSON Parse Error** (Line 209-218)
```python
logger.error(
    "Failed to parse storyboard response as JSON",
    extra={
        "artist_id": artist_id,
        "artist_name": artist_name,
        "error": str(e),
        "creative_brief_used": brief_used
    },
    exc_info=True
)
```
- ERROR level for JSON parsing failures
- Includes full exception traceback
- Tracks whether brief was used (for debugging)

**General Failure** (Line 221-232)
```python
logger.error(
    "Storyboard generation failed",
    extra={
        "artist_id": artist_id,
        "artist_name": artist_name,
        "error": str(e),
        "creative_brief_used": brief_used,
        "duration_seconds": duration_seconds,
        "aspect_ratio": aspect_ratio
    },
    exc_info=True
)
```
- ERROR level for any generation failure
- Includes full exception traceback
- Logs generation parameters for debugging

---

## Logging Levels Used

| Level | Usage | Examples |
|-------|-------|----------|
| **INFO** | Normal flow, successful operations | Session start/completion, agent completion, storyboard generation |
| **WARNING** | Degraded conditions, gate failures | Large reports, persona gate failures |
| **ERROR** | Failures and exceptions | Agent failures, JSON parse errors, generation failures |

---

## Structured Data Fields

All logs include these fields in `extra={}`:

### Common Fields
- `topic_id`: Topic identifier for traceability
- `artist_id`: Artist identifier for filtering
- `artist_name`: Human-readable artist name
- `error`: Error message (when applicable)
- `duration_seconds`: Execution time (rounded to 2 decimals)

### Planning Session Fields
- `threshold`: Persona alignment threshold
- `alignment_score`: Actual alignment score (rounded to 3 decimals)
- `gate_status`: Gate check result (GATE_PASSED/GATE_FAILED)
- `hook_candidates_count`: Number of hook options
- `viral_score`: Viral potential score
- `risk_level`: Content risk assessment
- `risk_factors_count`: Number of identified risks

### Agent Execution Fields
- `agent_name`: Name of the agent (hook_master, persona_guardian, etc.)
- `agent_count`: Total agents in parallel execution
- `successful_agents`: Count of successful agents
- `success_rate`: Percentage of successful agents
- `output_size_bytes`: Size of agent output

### Storyboard Generation Fields
- `scene_count`: Number of scenes generated
- `total_duration_seconds`: Total video duration
- `a_roll_scenes`: Count of host speaking scenes
- `b_roll_scenes`: Count of visual scenes
- `aspect_ratio`: Video format (9:16, 16:9, etc.)
- `style`: Content style (informative, entertaining, etc.)
- `creative_brief_used`: Boolean indicating brief usage
- `report_size_chars`: Size of research report
- `estimated_tokens`: Estimated token count

---

## Usage Examples

### Filtering Logs by Topic
```bash
# Find all logs for a specific topic
grep '"topic_id": "topic-123"' logs.json

# Using jq for JSON logs
cat logs.json | jq 'select(.topic_id == "topic-123")'
```

### Monitoring Gate Failures
```bash
# Find all persona gate failures
grep '"Persona gate check failed"' logs.json

# With jq
cat logs.json | jq 'select(.message == "Persona gate check failed")'
```

### Performance Analysis
```bash
# Find slow sessions (>30 seconds)
cat logs.json | jq 'select(.duration_seconds > 30)'

# Average session duration
cat logs.json | jq '[.[] | select(.message == "Planning session completed successfully") | .duration_seconds] | add / length'
```

### Agent Success Rate Monitoring
```bash
# Find sessions with agent failures
cat logs.json | jq 'select(.success_rate < 1.0)'
```

---

## Integration with Monitoring

These structured logs are designed for:

1. **ELK Stack (Elasticsearch, Logstash, Kibana)**
   - JSON fields automatically indexed
   - Easy dashboard creation for metrics
   - Real-time alerting on failures

2. **CloudWatch / DataDog**
   - Structured fields enable custom metrics
   - Automatic parsing of numeric fields
   - Log-based alarms on thresholds

3. **Splunk**
   - JSON extraction for field-based searches
   - Custom visualizations from metrics
   - Correlation analysis across topics/artists

4. **Local JSON Logging**
   - `jq` for ad-hoc analysis
   - Python scripts for batch processing
   - Easy debugging with full context

---

## Best Practices

1. **Always include topic_id** - Enables end-to-end tracing
2. **Round numeric values** - Improves log readability
3. **Use appropriate log levels** - INFO for normal flow, WARNING for degradation, ERROR for failures
4. **Include context in errors** - Full exception traceback with `exc_info=True`
5. **Track metrics** - Duration, counts, scores for performance analysis

---

## Summary

- **9 structured logging points** in planning_session.py
- **6 structured logging points** in gemini_client.py
- **All logs include topic_id** for traceability
- **JSON-structured extra fields** for easy parsing
- **Comprehensive metrics** for performance monitoring and debugging
