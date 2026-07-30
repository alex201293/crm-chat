# Chat + AI Response Flow

## Complete Message Flow (Widget → AI → WebSocket)

```
┌─────────┐    ┌───────────┐    ┌──────────────┐    ┌───────────┐    ┌────────────┐
│  Widget │    │ Widget API│    │SendMessage   │    │ AIService │    │  WebSocket │
│ (User)  │    │  Endpoint │    │  Handler     │    │           │    │  Manager   │
└────┬────┘    └─────┬─────┘    └──────┬───────┘    └─────┬─────┘    └──────┬─────┘
     │               │                  │                   │                 │
     │ POST message  │                  │                   │                 │
     │──────────────▶│                  │                   │                 │
     │               │  execute()       │                   │                 │
     │               │─────────────────▶│                   │                 │
     │               │                  │                   │                 │
     │               │                  │ 1. Create user    │                 │
     │               │                  │    message in DB  │                 │
     │               │                  │                   │                 │
     │               │                  │ 2. Update conver- │                 │
     │               │                  │    sation metadata│                 │
     │               │                  │                   │                 │
     │               │                  │ 3. Publish        │                 │
     │               │                  │    MessageReceived│                 │
     │               │                  │                   │                 │
     │               │                  │ 4. Check: is_ai_  │                 │
     │               │                  │    handling=true?  │                 │
     │               │                  │         ↓ YES     │                 │
     │               │                  │                   │                 │
     │               │                  │ 5. Get history    │                 │
     │               │                  │    (last 20 msgs) │                 │
     │               │                  │                   │                 │
     │               │                  │ 6. generate_      │                 │
     │               │                  │    response()     │                 │
     │               │                  │──────────────────▶│                 │
     │               │                  │                   │                 │
     │               │                  │                   │ Try preferred   │
     │               │                  │                   │ provider (OpenAI│
     │               │                  │                   │ /Claude/Gemini) │
     │               │                  │                   │                 │
     │               │                  │                   │ If fail →       │
     │               │                  │                   │ fallback chain  │
     │               │                  │                   │                 │
     │               │                  │  CompletionResult │                 │
     │               │                  │◀──────────────────│                 │
     │               │                  │                   │                 │
     │               │                  │ 7. Estimate       │                 │
     │               │                  │    confidence     │                 │
     │               │                  │                   │                 │
     │               │                  │ 8. should_        │                 │
     │               │                  │    escalate()?    │                 │
     │               │                  │         │         │                 │
     │               │                  │    ┌────┴────┐    │                 │
     │               │                  │    │         │    │                 │
     │               │                  │   NO        YES   │                 │
     │               │                  │    │         │    │                 │
     │               │                  │    ▼         ▼    │                 │
     │               │                  │ Save AI   Escalate│                 │
     │               │                  │ message   to human│                 │
     │               │                  │           queue   │                 │
     │               │                  │                   │                 │
     │               │  result          │                   │                 │
     │               │◀─────────────────│                   │                 │
     │               │                  │                   │                 │
     │               │                  │ 9. Broadcast      │                 │
     │               │                  │────────────────────────────────────▶│
     │               │                  │                   │                 │
     │  HTTP Response│                  │                   │    Send to room │
     │◀──────────────│                  │                   │   (agents get   │
     │ (user msg +   │                  │                   │    real-time)   │
     │  AI response) │                  │                   │                 │
     │               │                  │                   │                 │
```

## Escalation Triggers

| Trigger | Condition | Action |
|---------|-----------|--------|
| Low confidence | AI confidence < 0.5 | Transfer to pending queue |
| User request | "hablar con un agente" / "talk to human" | Immediate transfer |
| Frustration | "inaceptable" / "complaint" / "pésimo" | Transfer + high priority |
| Content filter | Provider blocks response | Transfer to human |

## AI Provider Selection

```
1. Read tenant settings → preferred provider + model
2. Try preferred provider
3. If fail → try fallback chain (OpenAI → Claude → Gemini → Mistral)
4. If all fail → RuntimeError (logged, no AI response sent)
```

## Confidence Scoring

| Factor | Score Adjustment |
|--------|-----------------|
| Short response (<5 words) | -0.3 |
| Content filter triggered | -0.5 |
| Hedging language detected | -0.3 |
| Truncated (max tokens hit) | -0.2 |
| Normal response | 1.0 (no adjustment) |

Threshold for escalation: **< 0.5**
