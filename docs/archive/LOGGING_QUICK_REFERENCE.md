# Logging Quick Reference

## Planning Session Logging Points

### 1. Session Start
**File:** `middleware/lib/planning_session.py:84`
**Level:** INFO
**Key Fields:** topic_id, artist_id, artist_name, threshold, ir_report_size

### 2. Parallel Agent Execution Start
**File:** `middleware/lib/planning_session.py:221`
**Level:** INFO
**Key Fields:** topic_id, artist_id, agent_count

### 3. Individual Agent Completion
**File:** `middleware/lib/planning_session.py:271`
**Level:** INFO
**Key Fields:** topic_id, artist_id, agent_name, success, output_size_bytes

### 4. Agent Failure
**File:** `middleware/lib/planning_session.py:252`
**Level:** ERROR
**Key Fields:** topic_id, artist_id, agent_name, error

### 5. Parallel Execution Summary
**File:** `middleware/lib/planning_session.py:285`
**Level:** INFO
**Key Fields:** topic_id, artist_id, successful_agents, total_agents, success_rate

### 6. Persona Gate Failure
**File:** `middleware/lib/planning_session.py:117`
**Level:** WARNING
**Key Fields:** topic_id, artist_id, alignment_score, threshold, gate_status, duration_seconds

### 7. Persona Gate Success
**File:** `middleware/lib/planning_session.py:146`
**Level:** INFO
**Key Fields:** topic_id, artist_id, alignment_score, threshold, gate_status

### 8. Session Completion Success
**File:** `middleware/lib/planning_session.py:161`
**Level:** INFO
**Key Fields:** topic_id, artist_id, gate_passed, duration_seconds, hook_candidates_count, viral_score, risk_level

### 9. Session Exception
**File:** `middleware/lib/planning_session.py:186`
**Level:** ERROR
**Key Fields:** topic_id, artist_id, error, duration_seconds

---

## Gemini Client Logging Points

### 1. Large Report Warning
**File:** `middleware/lib/gemini_client.py:69`
**Level:** WARNING
**Key Fields:** artist_id, artist_name, report_size_chars, estimated_tokens
**Trigger:** Report > 100K characters

### 2. Creative Brief Applied
**File:** `middleware/lib/gemini_client.py:95`
**Level:** INFO
**Key Fields:** artist_id, artist_name, alignment_score, viral_score, risk_level, recommended_hook_type, hook_candidates_count, engagement_hooks_count

### 3. No Creative Brief
**File:** `middleware/lib/gemini_client.py:109`
**Level:** INFO
**Key Fields:** artist_id, artist_name, reason

### 4. Storyboard Generation Success
**File:** `middleware/lib/gemini_client.py:192`
**Level:** INFO
**Key Fields:** artist_id, artist_name, scene_count, total_duration_seconds, a_roll_scenes, b_roll_scenes, aspect_ratio, style, creative_brief_used

### 5. JSON Parse Error
**File:** `middleware/lib/gemini_client.py:209`
**Level:** ERROR
**Key Fields:** artist_id, artist_name, error, creative_brief_used

### 6. Generation Failure
**File:** `middleware/lib/gemini_client.py:221`
**Level:** ERROR
**Key Fields:** artist_id, artist_name, error, creative_brief_used, duration_seconds, aspect_ratio

---

## Log Analysis Commands

### Find all logs for a topic
```bash
grep '"topic_id": "YOUR_TOPIC_ID"' /path/to/logs.json
```

### Find gate failures
```bash
grep '"Persona gate check failed"' /path/to/logs.json
```

### Find slow sessions (>30 seconds)
```bash
cat /path/to/logs.json | jq 'select(.duration_seconds > 30)'
```

### Find agent failures
```bash
grep '"Agent execution failed"' /path/to/logs.json
```

### Find storyboard generation issues
```bash
grep '"Storyboard generation failed"' /path/to/logs.json
```

### Get success rate for an artist
```bash
cat /path/to/logs.json | jq 'select(.artist_id == "ARTIST_ID") | select(.message == "Parallel agent execution completed") | .success_rate'
```

---

## Monitoring Alerts

### Recommended Alert Thresholds

1. **Agent Success Rate < 75%**
   - Log: "Parallel agent execution completed"
   - Field: success_rate
   - Action: Investigate agent failures

2. **Session Duration > 60 seconds**
   - Log: "Planning session completed successfully"
   - Field: duration_seconds
   - Action: Check for performance issues

3. **Gate Failure Rate > 20%**
   - Log: "Persona gate check failed"
   - Action: Review persona alignment thresholds

4. **Storyboard Generation Failures**
   - Log: "Storyboard generation failed"
   - Action: Check Gemini/Antigravity availability

5. **Large Reports (>200K chars)**
   - Log: "Large research report detected"
   - Field: report_size_chars
   - Action: Monitor token usage

---

## Integration Checklist

- [ ] Configure JSON logging in Python logger
- [ ] Set up log aggregation (ELK, CloudWatch, etc.)
- [ ] Create dashboards for key metrics
- [ ] Set up alerts for error conditions
- [ ] Document log retention policy
- [ ] Train team on log analysis commands
- [ ] Add log queries to runbooks
