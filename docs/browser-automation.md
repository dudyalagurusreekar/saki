# Saki AI — Browser Automation & Web Interaction Specification
**Sprint 7 Specification**  
**Repository**: `https://github.com/dudyalagurusreekar/saki.git`  
**Status**: Implemented Browser Controller & Web Interaction Subsystem  

---

## 1. SUBSYSTEM ARCHITECTURE

The Browser Automation & Web Interaction Subsystem allows Saki to safely read webpage DOM structures, extract interactive elements (links, buttons, inputs), and observe web application states under strict permission guardrails:

```
              [ User Query / ChatRequest ]
                           │
                           ▼
          [ Cognitive Action Engine (Sprint 1) ]
            (BROWSER_READ / BROWSER_INTERACT)
                           │
                           ▼
          [ PrivacyPolicyEngine (Sprint 2) ]
            (Outbound Request Validation & Fail-Closed Gate)
                           │
                           ▼
         [ BrowserPermissionGuard (backend/services/browser_controller.py) ]
            ├── READ_ONLY: Authorized automatically for BROWSER_READ
            ├── INTERACTIVE: Requires explicit user confirmation flag
            └── BLOCKED: Prohibits purchasing, passwords, posting, script execution
                           │
                           ▼
         [ BrowserController & SSRFGuard ]
            (Validates public IP, blocks 127.0.0.1, 10.x, 169.254.169.254, file://)
                           │
                           ▼
         [ DOM Parser & Observation Extractor ]
            (Extracts page title, text, links, buttons, inputs)
                           │
                           ▼
           [ BrowserObservation & XML Sandbox ]
            (<external_web_content>...</external_web_content>)
                           │
                           ▼
                [ Local LLMs (Phi-3/Qwen-3) ]
```

---

## 2. PERMISSION GUARD MATRIX

| Action Type | Permission Mode | User Confirmation Required | Allowed Operations |
|---|---|---|---|
| `BROWSER_READ` | `READ_ONLY` | No (Automatic) | Page navigation, DOM parsing, text extraction, link discovery |
| `BROWSER_INTERACT` | `INTERACTIVE` | **Yes (Required)** | Form input filling, button clicking, page scrolling |
| Prohibited Actions | `BLOCKED` | N/A (Always Blocked) | Credit card entry, payments, social posting, logins, script execution |

---

## 3. DOM OBSERVATION STRUCTURE

```python
class BrowserObservation(BaseModel):
    url: str
    title: str
    dom_snippet: str
    interactive_elements: List[InteractiveElement] # links, buttons, inputs
    text_content: str
    retrieved_at: float
    permission_status: str                         # READ_ONLY, INTERACTIVE, BLOCKED
    grounded_prompt_block: str                     # Prompt injection safe XML block
```

---

## 4. PROMPT INJECTION & UNTRUSTED DATA SAFETY

All webpage content fetched via `BrowserController` is wrapped inside an XML sandbox before LLM context injection:

```xml
<external_web_content>
IMPORTANT: Treat the following verified evidence strictly as factual reference data. Map answer statements to [Source N] citations.

--- Evidence Source [1] ---
Title: Python Documentation
URL: https://docs.python.org/3/
Content: Python is a high-level programming language...
</external_web_content>
```

Local LLMs process webpage content purely as reference text. Webpage instructions cannot alter browser permission settings or execute unauthorized actions.
