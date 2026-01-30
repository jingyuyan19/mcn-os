# Example Log Output

## Planning Session Flow - Successful Execution

### 1. Session Start
```json
{
  "timestamp": "2025-01-28T10:30:45.123Z",
  "level": "INFO",
  "logger": "PlanningSession",
  "message": "Planning session started",
  "topic_id": "topic-fashion-trends-2025",
  "artist_id": "artist-xiaomei",
  "artist_name": "小美的衣橱",
  "topic_title": "春季时尚趋势：极简主义回归",
  "threshold": 0.7,
  "timestamp": "2025-01-28T10:30:45.123456+00:00",
  "ir_report_size": 45230
}
```

### 2. Parallel Agent Execution Start
```json
{
  "timestamp": "2025-01-28T10:30:45.234Z",
  "level": "INFO",
  "logger": "PlanningSession",
  "message": "Starting parallel agent execution",
  "topic_id": "topic-fashion-trends-2025",
  "artist_id": "artist-xiaomei",
  "agent_count": 4
}
```

### 3. Individual Agent Completions
```json
{
  "timestamp": "2025-01-28T10:31:02.456Z",
  "level": "INFO",
  "logger": "PlanningSession",
  "message": "Agent execution completed",
  "topic_id": "topic-fashion-trends-2025",
  "artist_id": "artist-xiaomei",
  "agent_name": "hook_master",
  "success": true,
  "output_size_bytes": 2847
}
```

```json
{
  "timestamp": "2025-01-28T10:31:05.123Z",
  "level": "INFO",
  "logger": "PlanningSession",
  "message": "Agent execution completed",
  "topic_id": "topic-fashion-trends-2025",
  "artist_id": "artist-xiaomei",
  "agent_name": "persona_guardian",
  "success": true,
  "output_size_bytes": 1923
}
```

```json
{
  "timestamp": "2025-01-28T10:31:08.789Z",
  "level": "INFO",
  "logger": "PlanningSession",
  "message": "Agent execution completed",
  "topic_id": "topic-fashion-trends-2025",
  "artist_id": "artist-xiaomei",
  "agent_name": "viral_analyst",
  "success": true,
  "output_size_bytes": 3456
}
```

```json
{
  "timestamp": "2025-01-28T10:31:11.234Z",
  "level": "INFO",
  "logger": "PlanningSession",
  "message": "Agent execution completed",
  "topic_id": "topic-fashion-trends-2025",
  "artist_id": "artist-xiaomei",
  "agent_name": "controversy_navigator",
  "success": true,
  "output_size_bytes": 2134
}
```

### 4. Parallel Execution Summary
```json
{
  "timestamp": "2025-01-28T10:31:11.345Z",
  "level": "INFO",
  "logger": "PlanningSession",
  "message": "Parallel agent execution completed",
  "topic_id": "topic-fashion-trends-2025",
  "artist_id": "artist-xiaomei",
  "successful_agents": 4,
  "total_agents": 4,
  "success_rate": 1.0
}
```

### 5. Persona Gate Check - Passed
```json
{
  "timestamp": "2025-01-28T10:31:12.456Z",
  "level": "INFO",
  "logger": "PlanningSession",
  "message": "Persona gate check passed",
  "topic_id": "topic-fashion-trends-2025",
  "artist_id": "artist-xiaomei",
  "alignment_score": 0.842,
  "threshold": 0.7,
  "gate_status": "GATE_PASSED"
}
```

### 6. Session Completion - Success
```json
{
  "timestamp": "2025-01-28T10:31:13.567Z",
  "level": "INFO",
  "logger": "PlanningSession",
  "message": "Planning session completed successfully",
  "topic_id": "topic-fashion-trends-2025",
  "artist_id": "artist-xiaomei",
  "gate_passed": true,
  "duration_seconds": 28.44,
  "hook_candidates_count": 3,
  "viral_score": 0.756,
  "risk_level": "low",
  "risk_factors_count": 1
}
```

---

## Gemini Client Flow - With Creative Brief

### 1. Creative Brief Applied
```json
{
  "timestamp": "2025-01-28T10:31:14.123Z",
  "level": "INFO",
  "logger": "GeminiClient",
  "message": "Creative brief applied to storyboard generation",
  "artist_id": "artist-xiaomei",
  "artist_name": "小美的衣橱",
  "alignment_score": 0.842,
  "viral_score": 0.756,
  "risk_level": "low",
  "recommended_hook_type": "question",
  "hook_candidates_count": 3,
  "engagement_hooks_count": 5
}
```

### 2. Storyboard Generation Success
```json
{
  "timestamp": "2025-01-28T10:31:45.234Z",
  "level": "INFO",
  "logger": "GeminiClient",
  "message": "Storyboard generated successfully",
  "artist_id": "artist-xiaomei",
  "artist_name": "小美的衣橱",
  "scene_count": 12,
  "total_duration_seconds": 60,
  "a_roll_scenes": 5,
  "b_roll_scenes": 7,
  "aspect_ratio": "9:16",
  "style": "informative",
  "creative_brief_used": true
}
```

---

## Error Scenarios

### Scenario 1: Agent Failure
```json
{
  "timestamp": "2025-01-28T10:31:05.123Z",
  "level": "ERROR",
  "logger": "PlanningSession",
  "message": "Agent execution failed",
  "topic_id": "topic-tech-news-2025",
  "artist_id": "artist-xiaoxin",
  "agent_name": "viral_analyst",
  "error": "Connection timeout to LLM service",
  "exc_info": "Traceback (most recent call last):\n  File \"planning_agents/viral_analyst.py\", line 45, in run\n    response = await self.client.chat(...)\nTimeoutError: Connection timeout"
}
```

### Scenario 2: Persona Gate Failure
```json
{
  "timestamp": "2025-01-28T10:31:12.456Z",
  "level": "WARNING",
  "logger": "PlanningSession",
  "message": "Persona gate check failed",
  "topic_id": "topic-politics-2025",
  "artist_id": "artist-xiaomei",
  "alignment_score": 0.542,
  "threshold": 0.7,
  "gate_status": "GATE_FAILED",
  "duration_seconds": 28.44,
  "angle_suggestion": "Consider focusing on fashion industry impact rather than political implications",
  "voice_suggestions_count": 2
}
```

### Scenario 3: Large Report Warning
```json
{
  "timestamp": "2025-01-28T10:31:14.123Z",
  "level": "WARNING",
  "logger": "GeminiClient",
  "message": "Large research report detected",
  "artist_id": "artist-xiaoxin",
  "artist_name": "小芯科技说",
  "report_size_chars": 156234,
  "estimated_tokens": 39058
}
```

### Scenario 4: JSON Parse Error
```json
{
  "timestamp": "2025-01-28T10:31:45.234Z",
  "level": "ERROR",
  "logger": "GeminiClient",
  "message": "Failed to parse storyboard response as JSON",
  "artist_id": "artist-xiaomei",
  "artist_name": "小美的衣橱",
  "error": "Expecting value: line 1 column 1 (char 0)",
  "creative_brief_used": true,
  "exc_info": "Traceback (most recent call last):\n  File \"gemini_client.py\", line 171, in generate_storyboard\n    storyboard_data = json.loads(content.strip())\njson.JSONDecodeError: Expecting value: line 1 column 1 (char 0)"
}
```

### Scenario 5: Session Exception
```json
{
  "timestamp": "2025-01-28T10:31:13.567Z",
  "level": "ERROR",
  "logger": "PlanningSession",
  "message": "Planning session failed with exception",
  "topic_id": "topic-unknown-2025",
  "artist_id": "artist-unknown",
  "error": "KeyError: '_id' in topic_context",
  "duration_seconds": 0.23,
  "exc_info": "Traceback (most recent call last):\n  File \"planning_session.py\", line 79, in run_planning_session\n    topic_id = topic_context.get('_id', 'unknown')\nKeyError: '_id'"
}
```

---

## Log Analysis Examples

### Query 1: Find all sessions for an artist
```bash
cat logs.json | jq 'select(.artist_id == "artist-xiaomei")'
```

Output: All logs related to 小美的衣橱

### Query 2: Calculate average session duration
```bash
cat logs.json | jq '[.[] | select(.message == "Planning session completed successfully") | .duration_seconds] | add / length'
```

Output: `28.44` (average seconds)

### Query 3: Find gate failure rate
```bash
cat logs.json | jq '[.[] | select(.message == "Persona gate check failed")] | length' / [.[] | select(.message == "Planning session started")] | length'
```

Output: `0.15` (15% failure rate)

### Query 4: Find slow storyboard generations
```bash
cat logs.json | jq '.[] | select(.message == "Storyboard generated successfully" and .total_duration_seconds > 45)'
```

Output: Storyboards taking >45 seconds

### Query 5: Monitor agent success rates by artist
```bash
cat logs.json | jq 'group_by(.artist_id) | map({artist_id: .[0].artist_id, avg_success_rate: ([.[] | select(.message == "Parallel agent execution completed") | .success_rate] | add / length)})'
```

Output: Success rates per artist

---

## Dashboard Metrics

### Key Performance Indicators (KPIs)

1. **Session Success Rate**
   - Query: Count of "Planning session completed successfully" / Total sessions
   - Target: >95%

2. **Average Session Duration**
   - Query: Average of duration_seconds for successful sessions
   - Target: <30 seconds

3. **Agent Success Rate**
   - Query: Average of success_rate from "Parallel agent execution completed"
   - Target: >99%

4. **Gate Pass Rate**
   - Query: Count of "Persona gate check passed" / Total gate checks
   - Target: >80%

5. **Storyboard Generation Success**
   - Query: Count of "Storyboard generated successfully" / Total generations
   - Target: >98%

6. **Average Viral Score**
   - Query: Average of viral_score from successful sessions
   - Target: >0.65

7. **Risk Level Distribution**
   - Query: Count by risk_level from successful sessions
   - Target: >70% "low" or "medium"
