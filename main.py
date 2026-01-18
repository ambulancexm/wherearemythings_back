import os, json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI

from db import init_db
from tools_storage import resolve_location_path, get_or_create_item, put_item

MODEL = os.getenv("OPENAI_MODEL", "gpt-5.2")
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

app = FastAPI(title="WhereAreMyThings API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # en prod: ton domaine
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def _startup():
    init_db()

class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    session_id: str
    answer: str

SYSTEM = """Tu es un assistant pour ranger des objets et retrouver où ils sont.
Règles:
- Si l'utilisateur dit qu'il range/pose/met/déplace un objet, utilise les outils.
- Pour un rangement: 1) resolve_location_path 2) get_or_create_item 3) put_item
- Si ambigu/manquant, pose UNE question courte.
- Réponds en français, concis.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "resolve_location_path",
            "description": "Résout/crée une hiérarchie d'emplacements depuis un texte (ex: 'garage/placard jaune/haut').",
            "parameters": {
                "type": "object",
                "properties": {"path_text": {"type": "string"}},
                "required": ["path_text"],
                "additionalProperties": False
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_or_create_item",
            "description": "Trouve ou crée un objet par son nom (ex: 'visseuse').",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
                "additionalProperties": False
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "put_item",
            "description": "Enregistre qu'un objet est rangé dans un emplacement (option: quantité).",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_id": {"type": "integer"},
                    "location_id": {"type": "integer"},
                    "quantity": {"type": "integer", "default": 1},
                },
                "required": ["item_id", "location_id"],
                "additionalProperties": False
            },
        },
    },
]

DISPATCH = {
    "resolve_location_path": lambda a: resolve_location_path(a["path_text"]),
    "get_or_create_item": lambda a: get_or_create_item(a["name"]),
    "put_item": lambda a: put_item(a["item_id"], a["location_id"], a.get("quantity", 1)),
}

@app.post("/v1/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": req.message},
    ]

    # 1) première réponse (peut contenir des tool calls)
    resp = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOLS,
    )
    msg = resp.choices[0].message

    # 2) boucle tools
    while getattr(msg, "tool_calls", None):
        # on ajoute le message assistant qui contient les tool_calls
        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [tc.model_dump() for tc in msg.tool_calls],
        })

        # on exécute les tools et on renvoie les outputs
        for tc in msg.tool_calls:
            name = tc.function.name
            args = json.loads(tc.function.arguments or "{}")
            out = DISPATCH.get(name, lambda _a: {"error": f"unknown_tool:{name}"})(args)

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(out, ensure_ascii=False),
            })

        resp = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
        )
        msg = resp.choices[0].message

    return {"session_id": req.session_id, "answer": msg.content or ""}
