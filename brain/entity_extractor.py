import re
import json
from typing import List, Dict, Any, Tuple
from brain.schemas import EntityResult
from backend.services.ai_service import call_model

# Lexicon profiles for entity extraction
LEXICON: Dict[str, List[str]] = {
    "Programming Language": [
        "Python", "JavaScript", "TypeScript", "Java", "C#", "C++", "C", "Rust", "Go", "Golang",
        "Ruby", "PHP", "Swift", "Kotlin", "HTML", "CSS", "SQL", "Scala", "Shell", "Bash", "R"
    ],
    "Framework": [
        "FastAPI", "Django", "Flask", "Express", "React", "Vue", "Angular", "Svelte",
        "Spring", "ASP.NET", "Rails", "Ruby on Rails", "Next.js", "Nuxt", "Tornado",
        "Pydantic", "FastAPI", "Tailwind"
    ],
    "Database": [
        "PostgreSQL", "MySQL", "SQLite", "MongoDB", "Redis", "Elasticsearch", "DynamoDB",
        "Oracle", "Cassandra", "MariaDB", "Neo4j", "Firebase"
    ],
    "API/Service": [
        "OpenAI", "Gemini", "Claude", "Ollama", "Stripe", "Twilio", "SendGrid", "Auth0",
        "REST API", "GraphQL", "gRPC"
    ],
    "Company": [
        "Google", "Microsoft", "Apple", "Meta", "Amazon", "Netflix", "OpenAI", "Anthropic",
        "GitHub", "GitLab"
    ],
    "Product": [
        "Llama", "Qwen", "Phi", "ChatGPT", "Copilot", "iPhone", "MacBook", "Windows",
        "Linux", "Docker", "Kubernetes"
    ]
}

# Regex for github-style repos: user/repo-name (avoid catching plain text fractions like 2/3)
REPO_RE = re.compile(r'\b[a-zA-Z0-9_-]{2,}/[a-zA-Z0-9_.-]{2,}\b')

def lexicon_extract(text: str) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Scan query using predefined entity lexicons and regex rules."""
    entities_set = set()
    structured = []
    text_lower = text.lower()
    
    # 1. Lexicon scanning
    for ent_type, words in LEXICON.items():
        for word in words:
            # Match word boundaries to avoid partial matches
            pattern = rf'\b{re.escape(word)}\b'
            if re.search(pattern, text, re.IGNORECASE):
                # Find exact casing from lexicon
                entities_set.add(word)
                structured.append({"text": word, "type": ent_type})
                
    # 2. Repo pattern extraction
    repos = REPO_RE.findall(text)
    for repo in repos:
        # Ignore things that look like numbers (e.g. "1/2", "3/4")
        if not re.match(r'^\d+/\d+$', repo):
            entities_set.add(repo)
            structured.append({"text": repo, "type": "Repository"})
            
    return list(entities_set), structured

def llm_extract(text: str) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Query local Ollama to extract entities."""
    prompt = f"""
Identify important entities from the following user query.
Classify each entity into one of these types:
People, Companies, Programming Languages, Frameworks, Databases, APIs, Repositories, Products.

Respond ONLY with a JSON object in this format:
{{
  "entities": ["EntityName1", "EntityName2"],
  "structured_entities": [
    {{"text": "EntityName1", "type": "Programming Language"}},
    {{"text": "EntityName2", "type": "Database"}}
  ]
}}

User query: "{text}"
"""
    try:
        response = call_model(prompt)
        json_match = re.search(r'\{.*?\}', response, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
            entities = data.get("entities", [])
            structured = data.get("structured_entities", [])
            return entities, structured
    except Exception:
        pass
        
    return [], []

def extract_entities(text: str, skip_llm: bool = False) -> EntityResult:
    """
    Main entity extraction entrypoint.
    Runs lexicon scan first, and merges results with LLM findings if needed.
    """
    if not text or not text.strip():
        return EntityResult(entities=[], structured_entities=[])
        
    # 1. Lexicon extraction
    entities, structured = lexicon_extract(text)
    
    # 2. LLM extraction if lexicon is empty or we want to enrich
    if not skip_llm:
        llm_ents, llm_struct = llm_extract(text)
        
        # Merge results
        seen = {e.lower() for e in entities}
        for ent in llm_ents:
            if ent.lower() not in seen:
                entities.append(ent)
                seen.add(ent.lower())
                
        # Merge structured
        struct_seen = {(s["text"].lower(), s["type"].lower()) for s in structured}
        for s in llm_struct:
            key = (s.get("text", "").lower(), s.get("type", "").lower())
            if key not in struct_seen and s.get("text"):
                structured.append(s)
                struct_seen.add(key)
                
    return EntityResult(
        entities=entities,
        structured_entities=structured
    )
