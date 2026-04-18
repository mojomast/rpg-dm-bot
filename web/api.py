"""
RPG DM Bot - Web API
FastAPI server for the web management frontend.
Provides REST endpoints for sessions, locations, NPCs, items, events, and saves.
"""

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import sys
import os
import logging

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from src.database import Database
from src.chat_handler import ChatActor, ChatHandler
from src.chat_web_identity import generate_web_identity_uuid, hash_ip_address, web_user_id_from_uuid
from src.llm import LLMClient
from src.prompts import Prompts
from src.tool_schemas import ToolSchemas
from src.tools import ToolExecutor
from src.content_loader import (
    DEFAULT_CONTENT_PACK_ID,
    get_content_packs_manifest,
    get_pack_data,
    get_themes_manifest,
)

logger = logging.getLogger('rpg.api')


def get_client_ip(request: Request) -> str:
    """Resolve client IP, preferring proxy-forwarded addresses."""
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return get_remote_address(request)

# Initialize FastAPI app
app = FastAPI(
    title="RPG DM Bot Manager",
    description="Web management interface for the AI Dungeon Master bot",
    version="1.0.0"
)
limiter = Limiter(key_func=get_client_ip)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Initialize LLM client for worldbuilding (if API key available)
LLM_API_KEY = os.getenv('OPENROUTER_API_KEY') or os.getenv('REQUESTY_API_KEY')
LLM_MODEL = os.getenv('LLM_MODEL', 'openai/gpt-4o-mini')
LLM_BASE_URL = os.getenv('LLM_BASE_URL', 'https://router.requesty.ai/v1')
llm_client: Optional[LLMClient] = None

if LLM_API_KEY:
    llm_client = LLMClient(LLM_API_KEY, LLM_MODEL, base_url=LLM_BASE_URL)
    logger.info("LLM client initialized for worldbuilding")
else:
    logger.warning("No LLM API key set - worldbuilding will use placeholder data")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database instance
db = Database("data/rpg.db")
prompts = Prompts()
tool_schemas = ToolSchemas()
tools = ToolExecutor(db)
chat_handler: Optional[ChatHandler] = None

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class SessionCreate(BaseModel):
    guild_id: int
    name: str
    description: Optional[str] = None
    dm_user_id: int
    max_players: int = 6

class SessionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    max_players: Optional[int] = None

class LocationCreate(BaseModel):
    guild_id: int
    name: str
    created_by: int
    session_id: Optional[int] = None
    description: Optional[str] = None
    location_type: str = "generic"
    slug: Optional[str] = None
    hierarchy_kind: str = "location"
    tags: List[str] = []
    dm_notes: Optional[str] = None
    is_hidden: bool = False
    discoverability: str = "visible"
    points_of_interest: List[str] = []
    current_weather: Optional[str] = None
    danger_level: int = 0
    hidden_secrets: Optional[str] = None

class LocationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    location_type: Optional[str] = None
    slug: Optional[str] = None
    parent_location_id: Optional[int] = None
    depth: Optional[int] = None
    canonical_path: Optional[str] = None
    hierarchy_kind: Optional[str] = None
    tags: Optional[List[str]] = None
    dm_notes: Optional[str] = None
    is_hidden: Optional[bool] = None
    discoverability: Optional[str] = None
    current_weather: Optional[str] = None
    danger_level: Optional[int] = None
    hidden_secrets: Optional[str] = None

class NPCCreate(BaseModel):
    guild_id: int
    name: str
    created_by: int
    session_id: Optional[int] = None
    description: Optional[str] = None
    personality: Optional[str] = None
    npc_type: str = "neutral"
    location: Optional[str] = None
    location_id: Optional[int] = None
    is_merchant: bool = False

class NPCUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    personality: Optional[str] = None
    npc_type: Optional[str] = None
    location: Optional[str] = None
    location_id: Optional[int] = None
    is_merchant: Optional[bool] = None
    is_revealed: Optional[bool] = None
    actor_kind: Optional[str] = None
    faction_id: Optional[int] = None
    faction_role: Optional[str] = None
    goals: Optional[List[Dict[str, Any]]] = None
    secrets: Optional[List[Dict[str, Any]]] = None
    tags: Optional[List[str]] = None


class FactionCreate(BaseModel):
    guild_id: int
    name: str
    created_by: int
    session_id: Optional[int] = None
    description: Optional[str] = None
    faction_type: str = "neutral"
    disposition: Optional[str] = None
    alignment: Optional[str] = None
    influence: int = 0
    is_hidden: bool = False
    tags: List[str] = []
    goals: List[Dict[str, Any]] = []
    resources: List[Dict[str, Any]] = []
    allies: List[Any] = []
    enemies: List[Any] = []


class FactionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    faction_type: Optional[str] = None
    disposition: Optional[str] = None
    alignment: Optional[str] = None
    influence: Optional[int] = None
    is_hidden: Optional[bool] = None
    tags: Optional[List[str]] = None
    goals: Optional[List[Dict[str, Any]]] = None
    resources: Optional[List[Dict[str, Any]]] = None
    allies: Optional[List[Any]] = None
    enemies: Optional[List[Any]] = None


class FactionMemberCreate(BaseModel):
    actor_id: int
    actor_type: str = "npc"
    role: Optional[str] = None
    rank: Optional[str] = None
    notes: Optional[str] = None


class FactionMemberUpdate(BaseModel):
    actor_type: Optional[str] = None
    role: Optional[str] = None
    rank: Optional[str] = None
    notes: Optional[str] = None


class CharacterFactionReputationUpdate(BaseModel):
    reputation_change: int = 0
    reputation: Optional[int] = None
    tier: Optional[str] = None
    notes: Optional[str] = None


class StorylineCreate(BaseModel):
    guild_id: int
    title: str
    created_by: int
    session_id: Optional[int] = None
    description: Optional[str] = None
    status: str = "draft"
    act_label: Optional[str] = None
    sort_order: int = 0


class StorylineUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    act_label: Optional[str] = None
    sort_order: Optional[int] = None


class StorylineNodeCreate(BaseModel):
    title: str
    description: Optional[str] = None
    node_type: str = "scene"
    node_key: Optional[str] = None
    is_start: bool = False
    is_end: bool = False
    reveal_order: int = 0
    data_json: Dict[str, Any] = {}


class StorylineEdgeCreate(BaseModel):
    from_node_id: int
    to_node_id: int
    edge_type: str = "progression"
    conditions_json: Dict[str, Any] = {}


class StorylineAdvanceRequest(BaseModel):
    node_id: int
    character_id: Optional[int] = None
    branch_choice: Optional[str] = None
    variables: Dict[str, Any] = {}


class PlotPointCreate(BaseModel):
    title: str
    session_id: Optional[int] = None
    storyline_id: Optional[int] = None
    description: Optional[str] = None
    reveal_threshold: int = 1
    metadata_json: Dict[str, Any] = {}


class LocationConnectionCreate(BaseModel):
    from_location_id: int
    to_location_id: int
    direction: str = "path"
    travel_time: int = 1
    requirements: Optional[str] = None
    hidden: bool = False
    bidirectional: bool = True


class LocationConnectionUpdate(BaseModel):
    from_location_id: Optional[int] = None
    to_location_id: Optional[int] = None
    direction: Optional[str] = None
    travel_time: Optional[int] = None
    requirements: Optional[str] = None
    hidden: Optional[bool] = None
    bidirectional: Optional[bool] = None


class CombatMonsterSpawn(BaseModel):
    template_id: str
    count: int = 1

class StoryItemCreate(BaseModel):
    guild_id: int
    name: str
    created_by: int
    session_id: Optional[int] = None
    description: Optional[str] = None
    item_type: str = "misc"
    lore: Optional[str] = None
    discovery_conditions: Optional[str] = None
    dm_notes: Optional[str] = None

class StoryItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    item_type: Optional[str] = None
    lore: Optional[str] = None
    discovery_conditions: Optional[str] = None
    dm_notes: Optional[str] = None
    location_id: Optional[int] = None
    is_discovered: Optional[bool] = None
    discovered: Optional[bool] = None

class StoryEventCreate(BaseModel):
    guild_id: int
    name: str
    created_by: int
    session_id: Optional[int] = None
    description: Optional[str] = None
    event_type: str = "side_event"
    trigger_conditions: Optional[str] = None
    dm_notes: Optional[str] = None

class StoryEventUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    event_type: Optional[str] = None
    status: Optional[str] = None
    trigger_conditions: Optional[str] = None
    dm_notes: Optional[str] = None
    location_id: Optional[int] = None
    resolution_outcome: Optional[str] = None

class SnapshotCreate(BaseModel):
    session_id: int
    name: str
    created_by: int
    description: Optional[str] = None

class CharacterUpdate(BaseModel):
    name: Optional[str] = None
    char_class: Optional[str] = None
    race: Optional[str] = None
    level: Optional[int] = None
    backstory: Optional[str] = None
    hp: Optional[int] = None
    max_hp: Optional[int] = None
    mana: Optional[int] = None
    max_mana: Optional[int] = None
    gold: Optional[int] = None


class BrowserCharacterCreate(BaseModel):
    session_id: int
    name: str
    race: str
    char_class: str
    backstory: Optional[str] = None

class InventoryItemAdd(BaseModel):
    item_id: str
    item_name: str
    item_type: str
    quantity: int = 1
    properties: Dict[str, Any] = {}
    is_equipped: bool = False
    slot: Optional[str] = None

class InventoryItemUpdate(BaseModel):
    quantity: Optional[int] = None
    is_equipped: Optional[bool] = None
    slot: Optional[str] = None

class QuestCreate(BaseModel):
    guild_id: int
    title: str
    created_by: int
    session_id: Optional[int] = None
    description: Optional[str] = None
    objectives: List[str] = []
    rewards: Dict[str, Any] = {}
    status: str = "available"
    difficulty: str = "medium"
    quest_giver_npc_id: Optional[int] = None
    dm_notes: Optional[str] = None
    dm_plan: Optional[str] = None
    storyline_id: Optional[int] = None
    primary_location_id: Optional[int] = None
    quest_type: str = "main"
    availability_rules_json: Dict[str, Any] = {}
    branching_rules_json: Dict[str, Any] = {}
    failure_rules_json: Dict[str, Any] = {}

class QuestUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    objectives: Optional[List[str]] = None
    rewards: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    difficulty: Optional[str] = None
    quest_giver_npc_id: Optional[int] = None
    dm_notes: Optional[str] = None
    dm_plan: Optional[str] = None
    storyline_id: Optional[int] = None
    primary_location_id: Optional[int] = None
    quest_type: Optional[str] = None
    availability_rules_json: Optional[Dict[str, Any]] = None
    branching_rules_json: Optional[Dict[str, Any]] = None
    failure_rules_json: Optional[Dict[str, Any]] = None


class ChatHistoryMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    session_id: Optional[int] = None
    message: str
    character_id: Optional[int] = None
    dm_mode: bool = False
    chat_history: List[ChatHistoryMessage] = []


class ChatResponse(BaseModel):
    response: str
    mechanics_text: str
    tool_results: List[Dict[str, Any]]
    updated_state: Dict[str, Any]
    options: List[str]
    session_id: int


class ChatIdentityResponse(BaseModel):
    user_id: str


class ChatBootstrapResponse(BaseModel):
    session: Dict[str, Any]
    participants: List[Dict[str, Any]]
    available_characters: List[Dict[str, Any]]
    game_state: Dict[str, Any]
    recent_messages: List[Dict[str, str]]
    browser_dm: bool = False
    active_combat: Optional[Dict[str, Any]] = None
    location: Optional[Dict[str, Any]] = None
    connections: List[Dict[str, Any]] = []


class SessionSceneUpdate(BaseModel):
    scene: str


class SessionNarrateRequest(BaseModel):
    text: str
    title: str = "DM Narration"


class SessionMovePartyRequest(BaseModel):
    location_id: Optional[int] = None
    location_name: Optional[str] = None
    travel_description: Optional[str] = None


class SessionZeroGenerateRequest(BaseModel):
    session_id: int
    prompt: Optional[str] = None


class PlotPointUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    reveal_threshold: Optional[int] = None
    metadata_json: Optional[Dict[str, Any]] = None


async def _require_active_browser_session(session_id: Optional[int]) -> Dict[str, Any]:
    """Validate that browser chat is targeting a playable active session."""
    if session_id is None:
        raise HTTPException(status_code=400, detail="session_id is required")

    session = await db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=400, detail="Invalid session_id")
    if session.get('status') != 'active':
        raise HTTPException(status_code=400, detail="Browser chat only supports active sessions")
    return session


async def _require_browser_actor(
    session_id: int,
    x_web_identity: Optional[str],
    character_id: Optional[int],
    *,
    require_character: bool,
) -> tuple[str, int, List[Dict[str, Any]], List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Validate browser identity ownership against the selected session participant."""
    if not x_web_identity or not await db.web_identity_exists(x_web_identity):
        raise HTTPException(status_code=401, detail="Invalid web chat identity")

    web_user_id = web_user_id_from_uuid(x_web_identity)
    participants = await db.get_session_participants(session_id)
    owned_participants = [participant for participant in participants if participant.get('user_id') == web_user_id]
    owned_character_ids = {
        participant.get('character_id') for participant in owned_participants if participant.get('character_id')
    }

    if require_character and character_id is None:
        raise HTTPException(status_code=400, detail="character_id is required")

    character = None
    if character_id is not None:
        character = await db.get_character(character_id)
        if not character or character.get('session_id') != session_id:
            raise HTTPException(status_code=400, detail="Character does not belong to the selected session")
        if character_id not in owned_character_ids:
            raise HTTPException(status_code=403, detail="Browser identity does not control that character")

    return x_web_identity, web_user_id, participants, owned_participants, character


async def _browser_dm_allowed(session: Dict[str, Any], web_user_id: int) -> bool:
    """Allow browser DM mode when the browser identity matches the session DM."""
    return session.get('dm_user_id') == web_user_id


def _normalize_preview_connections(locations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize preview location connections into unique DB-ready edges."""
    connections: List[Dict[str, Any]] = []
    seen_edges = set()

    for location in locations:
        source_id = location.get('id')
        for raw_connection in location.get('connections', []) or []:
            if isinstance(raw_connection, str):
                target_id = raw_connection
                direction = 'path'
                travel_time = 1
                hidden = False
                bidirectional = True
            else:
                target_id = raw_connection.get('target_id') or raw_connection.get('to_location_id') or raw_connection.get('id')
                direction = raw_connection.get('direction') or raw_connection.get('type') or 'path'
                travel_time = raw_connection.get('travel_time') or 1
                hidden = bool(raw_connection.get('hidden', False))
                bidirectional = raw_connection.get('bidirectional', True)

            if not source_id or not target_id or source_id == target_id:
                continue

            edge_key = (source_id, target_id, direction)
            if edge_key in seen_edges:
                continue

            seen_edges.add(edge_key)
            connections.append({
                'from_preview_id': source_id,
                'to_preview_id': target_id,
                'direction': direction,
                'travel_time': travel_time,
                'hidden': hidden,
                'bidirectional': bidirectional,
            })

    return connections

# ============================================================================
# STARTUP / SHUTDOWN
# ============================================================================

@app.on_event("startup")
async def startup():
    await db.init()
    global chat_handler
    if llm_client:
        chat_handler = ChatHandler(db, llm_client, prompts, tool_schemas, tools)


def get_chat_handler() -> ChatHandler:
    if not chat_handler:
        raise HTTPException(status_code=503, detail="Chat is unavailable until an LLM API key is configured")
    return chat_handler

# ============================================================================
# DASHBOARD ENDPOINTS
# ============================================================================

@app.get("/api/dashboard")
async def get_dashboard():
    """Get dashboard overview data"""
    async with db.db_path as conn:
        pass  # Just to verify connection
    return {
        "status": "online",
        "message": "RPG DM Bot Manager API"
    }

@app.get("/api/stats")
async def get_stats(guild_id: Optional[int] = None):
    """Get overall statistics"""
    import aiosqlite
    async with aiosqlite.connect(db.db_path) as conn:
        conn.row_factory = aiosqlite.Row
        
        # Count sessions
        cursor = await conn.execute("SELECT COUNT(*) as count FROM sessions")
        sessions = (await cursor.fetchone())['count']
        
        # Count characters
        cursor = await conn.execute("SELECT COUNT(*) as count FROM characters")
        characters = (await cursor.fetchone())['count']
        
        # Count locations
        cursor = await conn.execute("SELECT COUNT(*) as count FROM locations")
        locations = (await cursor.fetchone())['count']
        
        # Count NPCs
        cursor = await conn.execute("SELECT COUNT(*) as count FROM npcs")
        npcs = (await cursor.fetchone())['count']
        
        return {
            "sessions": sessions,
            "characters": characters,
            "locations": locations,
            "npcs": npcs
        }

# ============================================================================
# SESSION ENDPOINTS
# ============================================================================

@app.get("/api/sessions")
async def list_sessions(guild_id: Optional[int] = None, status: Optional[str] = None):
    """List all sessions"""
    if guild_id:
        sessions = await db.get_sessions(guild_id, status)
    else:
        import aiosqlite
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            query = "SELECT * FROM sessions"
            if status:
                query += f" WHERE status = '{status}'"
            query += " ORDER BY created_at DESC"
            cursor = await conn.execute(query)
            sessions = [dict(row) for row in await cursor.fetchall()]
    return {"sessions": sessions}

@app.get("/api/sessions/{session_id}")
async def get_session(session_id: int):
    """Get full session state"""
    state = await db.get_full_session_state(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    return state

@app.post("/api/sessions")
async def create_session(session: SessionCreate):
    """Create a new session"""
    session_id = await db.create_session(
        guild_id=session.guild_id,
        name=session.name,
        description=session.description,
        dm_user_id=session.dm_user_id,
        max_players=session.max_players
    )
    return {"id": session_id, "message": "Session created"}

@app.patch("/api/sessions/{session_id}")
async def update_session(session_id: int, session: SessionUpdate):
    """Update a session"""
    updates = {k: v for k, v in session.dict().items() if v is not None}
    if updates:
        await db.update_session(session_id, **updates)
    return {"message": "Session updated"}


@app.post("/api/sessions/{session_id}/scene")
async def set_session_scene(session_id: int, payload: SessionSceneUpdate):
    """Persist the current scene text for a session."""
    session = await db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await db.save_game_state(
        session_id,
        current_scene=payload.scene,
        active_content_pack_id=session.get('content_pack_id'),
    )
    return {"message": "Scene updated"}


@app.post("/api/sessions/{session_id}/move-party")
async def move_session_party(session_id: int, payload: SessionMovePartyRequest):
    """Move the active party to a location using canonical travel rules."""
    session = await db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    location = None
    if payload.location_id is not None:
        location = await db.get_location(payload.location_id)
    elif payload.location_name:
        location = await db.get_location_by_name(session_id, payload.location_name)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    result = await tools._move_party_to_location(
        {'guild_id': session['guild_id'], 'session_id': session_id},
        {
            'location_id': location['id'],
            'travel_description': payload.travel_description or '',
        },
    )
    return json.loads(result)


@app.post("/api/sessions/{session_id}/narrate")
async def narrate_session(session_id: int, payload: SessionNarrateRequest):
    """Generate DM narration text for the session's current scene context."""
    session = await db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    handler = get_chat_handler()
    actor = ChatActor(
        user_id=session['dm_user_id'],
        display_name=f"DM {session['dm_user_id']}",
        character_name=None,
        character_id=None,
    )
    synthetic_channel_id = web_user_id_from_uuid(f"api-session-narration:{session_id}")
    result = await handler.process_single_message(
        guild_id=session['guild_id'],
        channel_id=synthetic_channel_id,
        actor=actor,
        user_message=f"[DM DIRECTIVE] Narrate this for the players in polished DM prose: {payload.text}",
        history=[],
        session_id=session_id,
    )
    return {
        'title': payload.title,
        'text': result['response'],
        'mechanics_text': result['mechanics_text'],
        'tool_results': result['tool_results'],
    }


@app.post("/api/sessions/{session_id}/session-zero")
async def generate_session_zero(session_id: int, payload: SessionZeroGenerateRequest):
    """Generate and persist a lightweight session-zero kickoff package."""
    session = await db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    participants = await db.get_session_participants(session_id)
    party_lines: List[str] = []
    for participant in participants:
        character_id = participant.get('character_id')
        if not character_id:
            continue
        character = await db.get_character(character_id)
        if character:
            party_lines.append(f"- {character['name']}: {character.get('backstory') or 'No backstory provided.'}")

    game_state = await db.get_game_state(session_id) or {}
    location = await db.get_location(game_state['current_location_id']) if game_state.get('current_location_id') else None
    prompt = payload.prompt or (
        f"Create a session zero opener for the campaign '{session['name']}'.\n"
        f"Setting: {session.get('setting') or session.get('world_theme')}.\n"
        f"Starting location: {(location or {}).get('name') or game_state.get('current_location') or 'Unknown'}.\n"
        f"Party:\n" + ("\n".join(party_lines) if party_lines else "- No party members yet.") +
        "\nReturn sections titled Opening Scene, Quest Hooks, NPC Introductions, and DM Notes."
    )

    if not llm_client:
        generated = {
            'opening_scene': f"The party gathers at {(location or {}).get('name') or 'the starting point'}, where the first threads of the campaign begin to tighten.",
            'quest_hooks': [
                'A local problem demands immediate attention.',
                'A mysterious faction is watching the party.',
            ],
            'npc_introductions': ['A local guide', 'A worried patron', 'A suspicious rival'],
            'dm_notes': 'Refine this opening once an LLM key is configured.',
        }
    else:
        generated_text = await llm_client.generate_response(prompt)
        generated = {
            'opening_scene': generated_text,
            'quest_hooks': [],
            'npc_introductions': [],
            'dm_notes': generated_text,
        }

    existing_notes = game_state.get('dm_notes') if isinstance(game_state.get('dm_notes'), dict) else {}
    existing_notes['session_zero'] = generated
    await db.save_game_state(
        session_id,
        dm_notes=existing_notes,
        active_content_pack_id=session.get('content_pack_id'),
    )
    return generated


@app.post("/api/chat/identity", response_model=ChatIdentityResponse)
async def create_chat_identity(http_request: Request):
    """Issue a server-generated browser chat identity."""
    identity = generate_web_identity_uuid()
    await db.create_web_identity(identity, hash_ip_address(get_client_ip(http_request)))
    return ChatIdentityResponse(user_id=identity)


@app.post("/api/chat", response_model=ChatResponse)
@limiter.limit("10/minute")
async def chat_with_dm(
    http_request: Request,
    request: ChatRequest,
    x_web_identity: Optional[str] = Header(None, alias="X-Web-Identity"),
):
    """Send a message to the AI DM and get a response."""
    handler = get_chat_handler()
    session = await _require_active_browser_session(request.session_id)
    x_web_identity, web_user_id, _, _, character = await _require_browser_actor(
        session['id'],
        x_web_identity,
        request.character_id,
        require_character=not request.dm_mode,
    )
    if request.dm_mode and not await _browser_dm_allowed(session, web_user_id):
        raise HTTPException(status_code=403, detail="Browser identity is not the session DM")

    synthetic_channel_id = web_user_id_from_uuid(f"web-session:{session['id']}:user:{x_web_identity}")

    actor_name = character['name'] if character else (f"DM {session['dm_user_id']}" if request.dm_mode else f"Web Player {x_web_identity[:8]}")
    actor = ChatActor(
        user_id=web_user_id,
        display_name=actor_name,
        character_name=character['name'] if character else None,
        character_id=character['id'] if character else None,
    )

    persisted_history = await db.get_recent_messages_by_session(web_user_id, request.session_id, limit=20)
    history = [
        {
            "role": message["role"],
            "content": message["content"],
        }
        for message in persisted_history
    ]

    result = await handler.process_single_message(
        guild_id=session['guild_id'],
        channel_id=synthetic_channel_id,
        actor=actor,
        user_message=(f"[DM DIRECTIVE] {request.message}" if request.dm_mode else request.message),
        history=history,
        session_id=request.session_id,
    )

    await db.save_message(
        web_user_id,
        session['guild_id'],
        synthetic_channel_id,
        'user',
        result['user_message']['content'],
        session_id=request.session_id,
    )
    await db.save_message(
        web_user_id,
        session['guild_id'],
        synthetic_channel_id,
        'assistant',
        result['assistant_message']['content'],
        session_id=request.session_id,
    )

    updated_state = await db.get_full_session_state(request.session_id)
    return ChatResponse(
        response=result['response'],
        mechanics_text=result['mechanics_text'],
        tool_results=result['tool_results'],
        updated_state=updated_state or {},
        options=handler.extract_response_options(result['response']),
        session_id=request.session_id,
    )


@app.get("/api/chat/bootstrap", response_model=ChatBootstrapResponse)
async def get_chat_bootstrap(
    session_id: Optional[int] = None,
    character_id: Optional[int] = None,
    x_web_identity: Optional[str] = Header(None, alias="X-Web-Identity"),
):
    """Return browser-chat bootstrap state for a playable session."""
    session = await _require_active_browser_session(session_id)
    _, web_user_id, participants, owned_participants, _ = await _require_browser_actor(
        session['id'],
        x_web_identity,
        character_id,
        require_character=False,
    )

    full_state = await db.get_full_session_state(session['id'])
    participants = full_state.get('participants', participants) if full_state else participants
    available_characters = [p for p in owned_participants if p.get('character_id')]

    recent = await db.get_recent_messages_by_session(web_user_id, session['id'], limit=20)
    recent_messages = [{"role": msg["role"], "content": msg["content"]} for msg in recent]

    game_state = await db.get_game_state(session['id']) or {}
    if not game_state.get('active_content_pack_id'):
        game_state['active_content_pack_id'] = session.get('content_pack_id')
    location = None
    connections: List[Dict[str, Any]] = []
    if game_state.get('current_location_id'):
        location = await db.get_location(game_state['current_location_id'])
        connections = await db.get_nearby_locations(game_state['current_location_id'])

    active_combat = await db.get_active_combat_by_session(session['id'])

    return ChatBootstrapResponse(
        session=session,
        participants=participants,
        available_characters=available_characters,
        game_state=game_state,
        recent_messages=recent_messages,
        browser_dm=await _browser_dm_allowed(session, web_user_id),
        active_combat=active_combat,
        location=location,
        connections=connections,
    )

# ============================================================================
# LOCATION ENDPOINTS
# ============================================================================

@app.get("/api/locations")
async def list_locations(session_id: Optional[int] = None, guild_id: Optional[int] = None):
    """List locations"""
    locations = await db.get_locations(session_id=session_id, guild_id=guild_id)
    return {"locations": locations}


@app.get("/api/sessions/{session_id}/location-tree")
async def get_session_location_tree(session_id: int):
    """Return the hierarchical location tree for a session."""
    session = await db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"locations": await db.get_location_tree(session_id)}

@app.get("/api/locations/{location_id}")
async def get_location(location_id: int):
    """Get a location"""
    loc = await db.get_location(location_id)
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")
    return loc

@app.get("/api/locations/{location_id}/adjacent")
async def get_adjacent_locations(location_id: int):
    """Get visible adjacent locations for a specific location."""
    loc = await db.get_location(location_id)
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")
    return {"locations": await db.get_nearby_locations(location_id)}

@app.post("/api/locations")
async def create_location(location: LocationCreate):
    """Create a location"""
    loc_id = await db.create_location(**location.dict())
    return {"id": loc_id, "message": "Location created"}

@app.patch("/api/locations/{location_id}")
async def update_location(location_id: int, location: LocationUpdate):
    """Update a location"""
    updates = {k: v for k, v in location.dict().items() if v is not None}
    if updates:
        await db.update_location(location_id, **updates)
    return {"message": "Location updated"}


@app.post("/api/locations/{location_id}/reveal")
async def reveal_location(location_id: int):
    """Reveal a location to players."""
    location = await db.get_location(location_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    await db.reveal_location(location_id)
    return {"message": "Location revealed"}

@app.delete("/api/locations/{location_id}")
async def delete_location(location_id: int):
    """Delete a location"""
    await db.delete_location(location_id)
    return {"message": "Location deleted"}

@app.post("/api/locations/{location_id}/connect/{target_id}")
async def connect_locations(location_id: int, target_id: int, direction: str = "path", travel_time: int = 1, hidden: bool = False):
    """Connect two locations"""
    await db.connect_locations(location_id, target_id, direction=direction, travel_time=travel_time, hidden=hidden)
    return {"message": "Locations connected"}

# ============================================================================
# NPC ENDPOINTS
# ============================================================================

@app.get("/api/npcs")
async def list_npcs(session_id: Optional[int] = None, guild_id: Optional[int] = None):
    """List NPCs"""
    if session_id:
        npcs = await db.get_npcs_by_session(session_id)
    elif guild_id:
        npcs = await db.get_npcs_by_guild(guild_id)
    else:
        import aiosqlite
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("SELECT * FROM npcs ORDER BY created_at DESC")
            rows = await cursor.fetchall()
            npcs = [db._normalize_npc_record(dict(row)) for row in rows]
    return {"npcs": npcs}

@app.get("/api/npcs/{npc_id}")
async def get_npc(npc_id: int):
    """Get an NPC"""
    npc = await db.get_npc(npc_id)
    if not npc:
        raise HTTPException(status_code=404, detail="NPC not found")
    return npc

@app.post("/api/npcs")
async def create_npc(npc: NPCCreate):
    """Create an NPC"""
    npc_id = await db.create_npc(**npc.dict())
    return {"id": npc_id, "message": "NPC created"}

@app.patch("/api/npcs/{npc_id}")
async def update_npc(npc_id: int, npc: NPCUpdate):
    """Update an NPC"""
    updates = {k: v for k, v in npc.dict().items() if v is not None}
    if updates:
        await db.update_npc(npc_id, **updates)
    return {"message": "NPC updated"}


@app.post("/api/npcs/{npc_id}/reveal")
async def reveal_npc(npc_id: int):
    """Reveal an NPC to players."""
    npc = await db.get_npc(npc_id)
    if not npc:
        raise HTTPException(status_code=404, detail="NPC not found")
    await db.reveal_npc(npc_id)
    return {"message": "NPC revealed"}

@app.delete("/api/npcs/{npc_id}")
async def delete_npc(npc_id: int):
    """Delete an NPC"""
    await db.delete_npc(npc_id)
    return {"message": "NPC deleted"}


# ============================================================================
# FACTION ENDPOINTS
# ============================================================================

@app.get("/api/factions")
async def list_factions(session_id: Optional[int] = None, guild_id: Optional[int] = None):
    """List factions."""
    factions = await db.get_factions(session_id=session_id, guild_id=guild_id)
    return {"factions": factions}


@app.post("/api/factions")
async def create_faction(faction: FactionCreate):
    """Create a faction."""
    payload = faction.dict()
    disposition = payload.pop('disposition', None)
    is_hidden = payload.pop('is_hidden', False)
    tags = payload.pop('tags', [])
    faction_id = await db.create_faction(**payload)
    updates = {}
    if disposition is not None:
        updates['disposition'] = disposition
    if is_hidden is not None:
        updates['is_hidden'] = int(bool(is_hidden))
    if tags is not None:
        updates['tags'] = tags
    if updates:
        await db.update_faction(faction_id, **updates)
    return {"id": faction_id, "message": "Faction created"}


@app.patch("/api/factions/{faction_id}")
async def update_faction(faction_id: int, faction: FactionUpdate):
    """Update a faction."""
    updates = {k: v for k, v in faction.dict().items() if v is not None}
    if updates:
        await db.update_faction(faction_id, **updates)
    return {"message": "Faction updated"}


@app.delete("/api/factions/{faction_id}")
async def delete_faction(faction_id: int):
    """Delete a faction."""
    await db.delete_faction(faction_id)
    return {"message": "Faction deleted"}


@app.get("/api/factions/{faction_id}/members")
async def get_faction_members(faction_id: int):
    """List faction members."""
    members = await db.get_faction_members(faction_id)
    return {"members": members}


@app.post("/api/factions/{faction_id}/members")
async def add_faction_member(faction_id: int, member: FactionMemberCreate):
    """Add a faction member."""
    membership_id = await db.add_faction_member(faction_id=faction_id, **member.dict())
    return {"id": membership_id, "message": "Faction member added"}


@app.patch("/api/faction-memberships/{membership_id}")
async def update_faction_member(membership_id: int, member: FactionMemberUpdate):
    """Update a faction member."""
    updates = {k: v for k, v in member.dict().items() if v is not None}
    if updates:
        updated = await db.update_faction_member(membership_id, **updates)
        if not updated:
            raise HTTPException(status_code=404, detail="Faction membership not found")
    return {"message": "Faction member updated"}


@app.delete("/api/faction-memberships/{membership_id}")
async def delete_faction_member(membership_id: int):
    """Delete a faction member."""
    deleted = await db.delete_faction_member(membership_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Faction membership not found")
    return {"message": "Faction member deleted"}


@app.get("/api/characters/{char_id}/factions")
async def get_character_factions(char_id: int):
    """Get character faction reputation entries."""
    factions = await db.get_character_faction_reputation(char_id)
    return {"factions": factions}


@app.patch("/api/characters/{char_id}/factions/{faction_id}")
async def update_character_faction_reputation(char_id: int, faction_id: int, payload: CharacterFactionReputationUpdate):
    """Update character faction reputation."""
    if payload.reputation is not None or payload.tier is not None:
        current = await db.get_character_faction_reputation(char_id, faction_id)
        if not isinstance(current, dict):
            current = {'reputation': 0, 'tier': 'neutral', 'notes': None}
        record = await db.upsert_character_faction_reputation(
            character_id=char_id,
            faction_id=faction_id,
            reputation=payload.reputation if payload.reputation is not None else current.get('reputation', 0),
            tier=payload.tier or current.get('tier', 'neutral'),
            notes=payload.notes,
        )
        return {"reputation": record, "message": "Faction reputation updated"}

    reputation = await db.update_character_faction_reputation(
        character_id=char_id,
        faction_id=faction_id,
        reputation_change=payload.reputation_change,
        notes=payload.notes,
    )
    return {"reputation": reputation, "message": "Faction reputation updated"}


@app.delete("/api/characters/{char_id}/factions/{faction_id}")
async def delete_character_faction_reputation(char_id: int, faction_id: int):
    """Delete a character faction reputation entry."""
    deleted = await db.delete_character_faction_reputation(char_id, faction_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Faction reputation not found")
    return {"message": "Faction reputation deleted"}

# ============================================================================
# STORY ITEM ENDPOINTS
# ============================================================================

@app.get("/api/items")
async def list_story_items(session_id: Optional[int] = None):
    """List story items"""
    items = await db.get_story_items(session_id=session_id)
    return {"items": items}

@app.get("/api/items/{item_id}")
async def get_story_item(item_id: int):
    """Get a story item"""
    item = await db.get_story_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.post("/api/items")
async def create_story_item(item: StoryItemCreate):
    """Create a story item"""
    item_id = await db.create_story_item(**item.dict())
    return {"id": item_id, "message": "Story item created"}

@app.patch("/api/items/{item_id}")
async def update_story_item(item_id: int, item: StoryItemUpdate):
    """Update a story item"""
    updates = {k: v for k, v in item.dict().items() if v is not None}
    if updates:
        await db.update_story_item(item_id, **updates)
    return {"message": "Story item updated"}

@app.post("/api/items/{item_id}/reveal")
async def reveal_story_item(item_id: int):
    """Reveal a story item"""
    await db.reveal_story_item(item_id)
    return {"message": "Item revealed"}

# ============================================================================
# STORY EVENT ENDPOINTS
# ============================================================================

@app.get("/api/events")
async def list_story_events(session_id: Optional[int] = None, status: Optional[str] = None):
    """List story events"""
    events = await db.get_story_events(session_id=session_id, status=status)
    return {"events": events}

@app.get("/api/events/{event_id}")
async def get_story_event(event_id: int):
    """Get a story event"""
    event = await db.get_story_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event

@app.post("/api/events")
async def create_story_event(event: StoryEventCreate):
    """Create a story event"""
    event_id = await db.create_story_event(**event.dict())
    return {"id": event_id, "message": "Story event created"}

@app.patch("/api/events/{event_id}")
async def update_story_event(event_id: int, event: StoryEventUpdate):
    """Update a story event"""
    updates = {k: v for k, v in event.dict().items() if v is not None}
    if updates:
        await db.update_story_event(event_id, **updates)
    return {"message": "Story event updated"}

@app.post("/api/events/{event_id}/trigger")
async def trigger_story_event(event_id: int):
    """Trigger an event"""
    await db.trigger_event(event_id)
    return {"message": "Event triggered"}

@app.post("/api/events/{event_id}/resolve")
async def resolve_story_event(event_id: int, outcome: str = "success", notes: str = None):
    """Resolve an event"""
    updates = {"resolution_outcome": outcome}
    if notes:
        updates["dm_notes"] = notes
    await db.update_story_event(event_id, **updates)
    await db.resolve_event(event_id, outcome)
    return {"message": "Event resolved"}

# ============================================================================
# SNAPSHOT (SAVE/LOAD) ENDPOINTS
# ============================================================================

@app.get("/api/snapshots")
async def list_snapshots(session_id: int):
    """List snapshots for a session"""
    snapshots = await db.get_session_snapshots(session_id)
    return {"snapshots": snapshots}

@app.get("/api/snapshots/{snapshot_id}")
async def get_snapshot(snapshot_id: int):
    """Get a snapshot"""
    snapshot = await db.get_session_snapshot(snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return snapshot

@app.post("/api/snapshots")
async def create_snapshot(snapshot: SnapshotCreate):
    """Create a save point"""
    snapshot_id = await db.save_session_snapshot(
        session_id=snapshot.session_id,
        name=snapshot.name,
        created_by=snapshot.created_by,
        description=snapshot.description,
        snapshot_type='manual'
    )
    return {"id": snapshot_id, "message": "Save point created"}

@app.post("/api/snapshots/{snapshot_id}/load")
async def load_snapshot(snapshot_id: int):
    """Load a save point"""
    result = await db.load_session_snapshot(snapshot_id)
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error'))
    return result

@app.delete("/api/snapshots/{snapshot_id}")
async def delete_snapshot(snapshot_id: int):
    """Delete a snapshot"""
    success = await db.delete_session_snapshot(snapshot_id)
    if not success:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return {"message": "Snapshot deleted"}

# ============================================================================
# CHARACTER ENDPOINTS
# ============================================================================

@app.get("/api/characters")
async def list_characters(session_id: Optional[int] = None, guild_id: Optional[int] = None):
    """List characters"""
    if session_id:
        characters = await db.get_session_characters(session_id)
    else:
        import aiosqlite
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            query = "SELECT * FROM characters"
            if guild_id:
                query += f" WHERE guild_id = {guild_id}"
            query += " ORDER BY created_at DESC"
            cursor = await conn.execute(query)
            characters = [dict(row) for row in await cursor.fetchall()]
    return {"characters": characters}

@app.get("/api/characters/{char_id}")
async def get_character(char_id: int):
    """Get a character"""
    char = await db.get_character(char_id)
    if not char:
        raise HTTPException(status_code=404, detail="Character not found")
    return char

@app.patch("/api/characters/{char_id}")
async def update_character(char_id: int, character: CharacterUpdate):
    """Update a character"""
    updates = {k: v for k, v in character.dict().items() if v is not None}
    if updates:
        await db.update_character(char_id, **updates)
    return {"message": "Character updated"}


@app.post("/api/characters/browser")
async def create_browser_character(
    character: BrowserCharacterCreate,
    x_web_identity: Optional[str] = Header(None, alias="X-Web-Identity"),
):
    """Create and attach a browser-playable character to a session."""
    if not x_web_identity or not await db.web_identity_exists(x_web_identity):
        raise HTTPException(status_code=401, detail="Invalid web chat identity")

    session = await _require_active_browser_session(character.session_id)

    web_user_id = web_user_id_from_uuid(x_web_identity)
    existing_participants = await db.get_session_participants(character.session_id)
    existing_character_id = next(
        (
            participant.get('character_id')
            for participant in existing_participants
            if participant.get('user_id') == web_user_id and participant.get('character_id')
        ),
        None,
    )
    if existing_character_id:
        raise HTTPException(status_code=400, detail="Browser player already has a character in this session")

    char_id = await db.create_character(
        user_id=web_user_id,
        guild_id=session['guild_id'],
        name=character.name,
        race=character.race,
        char_class=character.char_class,
        stats={
            'strength': 12,
            'dexterity': 12,
            'constitution': 12,
            'intelligence': 12,
            'wisdom': 12,
            'charisma': 12,
        },
        backstory=character.backstory,
        session_id=character.session_id,
    )
    await db.join_session(character.session_id, web_user_id, character_id=char_id)

    game_state = await db.get_game_state(character.session_id)
    if game_state and game_state.get('current_location_id'):
        await db.update_character(char_id, current_location_id=game_state['current_location_id'])

    created = await db.get_character(char_id)
    return {"character": created}

# ============================================================================
# INVENTORY ENDPOINTS
# ============================================================================

@app.get("/api/characters/{char_id}/inventory")
async def get_character_inventory(char_id: int):
    """Get character's inventory"""
    inventory = await db.get_inventory(char_id)
    return {"inventory": inventory}

@app.post("/api/characters/{char_id}/inventory")
async def add_inventory_item(char_id: int, item: InventoryItemAdd):
    """Add an item to character's inventory"""
    item_id = await db.add_item(
        character_id=char_id,
        item_id=item.item_id,
        item_name=item.item_name,
        item_type=item.item_type,
        quantity=item.quantity,
        properties=item.properties,
        is_equipped=item.is_equipped,
        slot=item.slot
    )
    return {"id": item_id, "message": "Item added to inventory"}

@app.patch("/api/inventory/{inventory_id}")
async def update_inventory_item(inventory_id: int, item: InventoryItemUpdate):
    """Update an inventory item (quantity, equip status)"""
    import aiosqlite
    
    async with aiosqlite.connect(db.db_path) as conn:
        updates = []
        values = []
        
        if item.quantity is not None:
            updates.append("quantity = ?")
            values.append(item.quantity)
        if item.is_equipped is not None:
            updates.append("is_equipped = ?")
            values.append(1 if item.is_equipped else 0)
        if item.slot is not None:
            updates.append("slot = ?")
            values.append(item.slot)
        
        if updates:
            values.append(inventory_id)
            await conn.execute(
                f"UPDATE inventory SET {', '.join(updates)} WHERE id = ?",
                values
            )
            await conn.commit()
    
    return {"message": "Inventory item updated"}

@app.post("/api/inventory/{inventory_id}/equip")
async def equip_inventory_item(inventory_id: int, slot: str = Query(None)):
    """Equip an inventory item"""
    import aiosqlite
    
    async with aiosqlite.connect(db.db_path) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute("SELECT * FROM inventory WHERE id = ?", (inventory_id,))
        item = await cursor.fetchone()
        
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        
        item = dict(item)
        equip_slot = slot or db._get_default_slot(item['item_type'])
        
        # Unequip any item in the same slot
        await conn.execute(
            "UPDATE inventory SET is_equipped = 0, slot = NULL WHERE character_id = ? AND slot = ?",
            (item['character_id'], equip_slot)
        )
        
        # Equip the item
        await conn.execute(
            "UPDATE inventory SET is_equipped = 1, slot = ? WHERE id = ?",
            (equip_slot, inventory_id)
        )
        await conn.commit()
    
    return {"message": f"Item equipped to {equip_slot}"}

@app.post("/api/inventory/{inventory_id}/unequip")
async def unequip_inventory_item(inventory_id: int):
    """Unequip an inventory item"""
    await db.unequip_item(inventory_id)
    return {"message": "Item unequipped"}

@app.delete("/api/inventory/{inventory_id}")
async def delete_inventory_item(inventory_id: int, quantity: int = Query(1)):
    """Remove item(s) from inventory"""
    success = await db.remove_item(inventory_id, quantity)
    if not success:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Item removed from inventory"}

# ============================================================================
# QUEST ENDPOINTS
# ============================================================================

@app.get("/api/quests")
async def list_quests(session_id: Optional[int] = None, guild_id: Optional[int] = None, status: Optional[str] = None):
    """List quests"""
    quests = await db.get_quests(session_id=session_id, guild_id=guild_id, status=status)
    return {"quests": quests}

@app.get("/api/quests/{quest_id}")
async def get_quest(quest_id: int):
    """Get a quest"""
    quest = await db.get_quest(quest_id)
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")
    return quest

@app.post("/api/quests")
async def create_quest(quest: QuestCreate):
    """Create a quest"""
    quest_id = await db.create_quest(**quest.dict())
    if quest.status != 'available':
        await db.update_quest(quest_id, status=quest.status)
    return {"id": quest_id, "message": "Quest created"}

@app.patch("/api/quests/{quest_id}")
async def update_quest(quest_id: int, quest: QuestUpdate):
    """Update a quest"""
    updates = {k: v for k, v in quest.dict().items() if v is not None}
    if updates:
        await db.update_quest(quest_id, **updates)
    return {"message": "Quest updated"}

@app.delete("/api/quests/{quest_id}")
async def delete_quest(quest_id: int):
    """Delete a quest"""
    await db.delete_quest(quest_id)
    return {"message": "Quest deleted"}

# ============================================================================
# STORY ITEM DELETE ENDPOINT
# ============================================================================

@app.delete("/api/items/{item_id}")
async def delete_story_item(item_id: int):
    """Delete a story item"""
    import aiosqlite
    async with aiosqlite.connect(db.db_path) as conn:
        await conn.execute("DELETE FROM story_items WHERE id = ?", (item_id,))
        await conn.commit()
    return {"message": "Story item deleted"}

# ============================================================================
# STORY EVENT DELETE ENDPOINT
# ============================================================================

@app.delete("/api/events/{event_id}")
async def delete_story_event(event_id: int):
    """Delete a story event"""
    import aiosqlite
    async with aiosqlite.connect(db.db_path) as conn:
        await conn.execute("DELETE FROM story_events WHERE id = ?", (event_id,))
        await conn.commit()
    return {"message": "Story event deleted"}

# ============================================================================
# NPC TEMPLATES ENDPOINT
# ============================================================================

@app.get("/api/templates/npcs")
async def get_npc_templates(content_pack_id: str = DEFAULT_CONTENT_PACK_ID):
    """Get NPC generation templates"""
    try:
        return get_pack_data(content_pack_id, "npc_templates.json")
    except Exception:
        return {"templates": {}}


@app.get("/api/templates/enemies")
async def get_enemy_templates(content_pack_id: str = DEFAULT_CONTENT_PACK_ID):
    """Get monster templates for combat spawning."""
    try:
        templates = []
        try:
            templates = await db.get_monster_templates(content_pack_id=content_pack_id)
        except Exception:
            templates = []
        if templates:
            normalized = []
            for template in templates:
                row = dict(template)
                row.setdefault('ac', row.get('armor_class'))
                row.setdefault('hp', row.get('max_hp'))
                normalized.append(row)
            return {"templates": normalized}
        data = get_pack_data(content_pack_id, "enemies.json")
        templates = []
        for template_id, template in data.get('enemies', {}).items():
            row = dict(template)
            row.setdefault('id', template_id)
            templates.append(row)
        return {"templates": sorted(templates, key=lambda item: item.get('name') or item.get('id') or '')}
    except Exception:
        return {"templates": []}


@app.get("/api/monsters")
async def list_monsters(content_pack_id: str = DEFAULT_CONTENT_PACK_ID, session_id: Optional[int] = None):
    """List relational monster templates."""
    monsters = await db.get_monster_templates(content_pack_id=content_pack_id, session_id=session_id)
    return {"monsters": monsters}


@app.get("/api/monsters/{template_id}")
async def get_monster(template_id: str, content_pack_id: str = DEFAULT_CONTENT_PACK_ID, session_id: Optional[int] = None):
    """Get one monster template."""
    monster = await db.get_monster_template(template_id=template_id, content_pack_id=content_pack_id, session_id=session_id)
    if not monster:
        raise HTTPException(status_code=404, detail="Monster template not found")
    return monster

# ============================================================================
# GAME DATA ENDPOINTS - Classes, Races, Skills, Items, Spells
# ============================================================================

def load_game_data(filename: str, content_pack_id: str = DEFAULT_CONTENT_PACK_ID, use_content_pack: bool = True) -> Dict[str, Any]:
    """Load game data from JSON file"""
    try:
        if use_content_pack and "/" not in filename:
            return get_pack_data(content_pack_id, filename)

        filepath = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "data", "game_data", filename
        )
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/content-packs")
async def get_content_packs():
    """List available content packs."""
    return get_content_packs_manifest()


@app.get("/api/themes")
async def get_themes():
    """List available world themes."""
    return get_themes_manifest()

def save_game_data(filename: str, data: Dict[str, Any]) -> bool:
    """Save game data to JSON file"""
    filepath = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "data", "game_data", filename
    )
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except:
        return False

# --- CLASSES ---

@app.get("/api/gamedata/classes")
async def get_classes(content_pack_id: str = DEFAULT_CONTENT_PACK_ID):
    """Get all character classes"""
    data = load_game_data("classes.json", content_pack_id=content_pack_id)
    return {"classes": data.get("classes", {})}

@app.get("/api/gamedata/classes/{class_id}")
async def get_class(class_id: str):
    """Get a specific class"""
    data = load_game_data("classes.json")
    classes = data.get("classes", {})
    if class_id not in classes:
        raise HTTPException(status_code=404, detail="Class not found")
    return {"class": classes[class_id], "id": class_id}

class ClassUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    hit_die: Optional[str] = None
    primary_ability: Optional[str] = None
    saving_throws: Optional[List[str]] = None
    armor_proficiencies: Optional[List[str]] = None
    weapon_proficiencies: Optional[List[str]] = None
    starting_equipment: Optional[List[str]] = None
    abilities: Optional[Dict[str, Any]] = None
    spell_slots: Optional[Dict[str, List[int]]] = None

@app.patch("/api/gamedata/classes/{class_id}")
async def update_class(class_id: str, update: ClassUpdate):
    """Update a class"""
    data = load_game_data("classes.json")
    classes = data.get("classes", {})
    
    if class_id not in classes:
        raise HTTPException(status_code=404, detail="Class not found")
    
    # Apply updates
    for key, value in update.dict().items():
        if value is not None:
            classes[class_id][key] = value
    
    data["classes"] = classes
    if save_game_data("classes.json", data):
        return {"message": "Class updated", "class": classes[class_id]}
    raise HTTPException(status_code=500, detail="Failed to save")

class ClassCreate(BaseModel):
    id: str
    name: str
    description: str = ""
    hit_die: str = "d8"
    primary_ability: str = "strength"
    saving_throws: List[str] = []
    armor_proficiencies: List[str] = []
    weapon_proficiencies: List[str] = []
    starting_equipment: List[str] = []
    abilities: Dict[str, Any] = {}
    spell_slots: Optional[Dict[str, List[int]]] = None

@app.post("/api/gamedata/classes")
async def create_class(new_class: ClassCreate):
    """Create a new class"""
    data = load_game_data("classes.json")
    classes = data.get("classes", {})
    
    if new_class.id in classes:
        raise HTTPException(status_code=400, detail="Class ID already exists")
    
    class_data = new_class.dict()
    class_id = class_data.pop("id")
    classes[class_id] = class_data
    
    data["classes"] = classes
    if save_game_data("classes.json", data):
        return {"message": "Class created", "id": class_id}
    raise HTTPException(status_code=500, detail="Failed to save")

@app.delete("/api/gamedata/classes/{class_id}")
async def delete_class(class_id: str):
    """Delete a class"""
    data = load_game_data("classes.json")
    classes = data.get("classes", {})
    
    if class_id not in classes:
        raise HTTPException(status_code=404, detail="Class not found")
    
    del classes[class_id]
    data["classes"] = classes
    
    if save_game_data("classes.json", data):
        return {"message": "Class deleted"}
    raise HTTPException(status_code=500, detail="Failed to save")

@app.put("/api/gamedata/classes")
async def update_all_classes(classes_data: Dict[str, Any]):
    """Update all classes at once (for bulk editing)"""
    # The frontend sends the entire classes data structure
    data = {"classes": classes_data.get("classes", classes_data)}
    if save_game_data("classes.json", data):
        return {"message": "Classes updated"}
    raise HTTPException(status_code=500, detail="Failed to save")

# --- RACES ---

@app.get("/api/gamedata/races")
async def get_races(content_pack_id: str = DEFAULT_CONTENT_PACK_ID):
    """Get all races"""
    data = load_game_data("races.json", content_pack_id=content_pack_id)
    return {"races": data.get("races", {})}

@app.get("/api/gamedata/races/{race_id}")
async def get_race(race_id: str):
    """Get a specific race"""
    data = load_game_data("races.json")
    races = data.get("races", {})
    if race_id not in races:
        raise HTTPException(status_code=404, detail="Race not found")
    return {"race": races[race_id], "id": race_id}

class RaceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    stat_bonuses: Optional[Dict[str, int]] = None
    size: Optional[str] = None
    speed: Optional[int] = None
    languages: Optional[List[str]] = None
    traits: Optional[List[Dict[str, Any]]] = None
    subraces: Optional[Dict[str, Any]] = None

@app.patch("/api/gamedata/races/{race_id}")
async def update_race(race_id: str, update: RaceUpdate):
    """Update a race"""
    data = load_game_data("races.json")
    races = data.get("races", {})
    
    if race_id not in races:
        raise HTTPException(status_code=404, detail="Race not found")
    
    for key, value in update.dict().items():
        if value is not None:
            races[race_id][key] = value
    
    data["races"] = races
    if save_game_data("races.json", data):
        return {"message": "Race updated", "race": races[race_id]}
    raise HTTPException(status_code=500, detail="Failed to save")

class RaceCreate(BaseModel):
    id: str
    name: str
    description: str = ""
    stat_bonuses: Dict[str, int] = {}
    size: str = "medium"
    speed: int = 30
    languages: List[str] = ["common"]
    traits: List[Dict[str, Any]] = []
    subraces: Optional[Dict[str, Any]] = None

@app.post("/api/gamedata/races")
async def create_race(new_race: RaceCreate):
    """Create a new race"""
    data = load_game_data("races.json")
    races = data.get("races", {})
    
    if new_race.id in races:
        raise HTTPException(status_code=400, detail="Race ID already exists")
    
    race_data = new_race.dict()
    race_id = race_data.pop("id")
    races[race_id] = race_data
    
    data["races"] = races
    if save_game_data("races.json", data):
        return {"message": "Race created", "id": race_id}
    raise HTTPException(status_code=500, detail="Failed to save")

@app.delete("/api/gamedata/races/{race_id}")
async def delete_race(race_id: str):
    """Delete a race"""
    data = load_game_data("races.json")
    races = data.get("races", {})
    
    if race_id not in races:
        raise HTTPException(status_code=404, detail="Race not found")
    
    del races[race_id]
    data["races"] = races
    
    if save_game_data("races.json", data):
        return {"message": "Race deleted"}
    raise HTTPException(status_code=500, detail="Failed to save")

@app.put("/api/gamedata/races")
async def update_all_races(races_data: Dict[str, Any]):
    """Update all races at once (for bulk editing)"""
    data = {"races": races_data.get("races", races_data)}
    if save_game_data("races.json", data):
        return {"message": "Races updated"}
    raise HTTPException(status_code=500, detail="Failed to save")

# --- SKILLS ---

@app.get("/api/gamedata/skills")
async def get_skills(content_pack_id: str = DEFAULT_CONTENT_PACK_ID):
    """Get all skills and skill trees"""
    data = load_game_data("skills.json", content_pack_id=content_pack_id)
    return data

@app.get("/api/gamedata/skills/trees")
async def get_skill_trees():
    """Get skill trees by class"""
    data = load_game_data("skills.json")
    return {"skill_trees": data.get("skill_trees", {})}

@app.get("/api/gamedata/skills/trees/{class_id}")
async def get_class_skill_tree(class_id: str):
    """Get skill tree for a specific class"""
    data = load_game_data("skills.json")
    trees = data.get("skill_trees", {})
    if class_id not in trees:
        raise HTTPException(status_code=404, detail="Skill tree not found for class")
    return {"skill_tree": trees[class_id], "class": class_id}

@app.get("/api/gamedata/skills/{skill_id}")
async def get_skill(skill_id: str):
    """Get a specific skill"""
    data = load_game_data("skills.json")
    skills = data.get("skills", {})
    if skill_id not in skills:
        raise HTTPException(status_code=404, detail="Skill not found")
    return {"skill": skills[skill_id], "id": skill_id}

class SkillUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    tier: Optional[int] = None
    skill_point_cost: Optional[int] = None
    is_passive: Optional[bool] = None
    cooldown: Optional[int] = None
    uses_per_rest: Optional[int] = None
    recharge: Optional[str] = None
    effects: Optional[List[Dict[str, Any]]] = None
    prerequisites: Optional[List[str]] = None

@app.patch("/api/gamedata/skills/{skill_id}")
async def update_skill(skill_id: str, update: SkillUpdate):
    """Update a skill"""
    data = load_game_data("skills.json")
    skills = data.get("skills", {})
    
    if skill_id not in skills:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    for key, value in update.dict().items():
        if value is not None:
            skills[skill_id][key] = value
    
    data["skills"] = skills
    if save_game_data("skills.json", data):
        return {"message": "Skill updated", "skill": skills[skill_id]}
    raise HTTPException(status_code=500, detail="Failed to save")

@app.put("/api/gamedata/skills/trees/{class_id}")
async def update_class_skill_tree(class_id: str, tree_data: Dict[str, Any]):
    """Update skill tree for a specific class"""
    data = load_game_data("skills.json")
    trees = data.get("skill_trees", {})
    
    # Update the skill tree for this class
    trees[class_id] = tree_data.get("skill_tree", tree_data)
    data["skill_trees"] = trees
    
    if save_game_data("skills.json", data):
        return {"message": f"Skill tree for {class_id} updated"}
    raise HTTPException(status_code=500, detail="Failed to save")

@app.put("/api/gamedata/skills")
async def update_all_skills(skills_data: Dict[str, Any]):
    """Update all skills and skill trees at once"""
    if save_game_data("skills.json", skills_data):
        return {"message": "Skills data updated"}
    raise HTTPException(status_code=500, detail="Failed to save")

@app.get("/api/gamedata/status-effects")
async def get_status_effects():
    """Get all status effects"""
    data = load_game_data("skills.json")
    return {"status_effects": data.get("status_effects", {})}

# --- ITEMS ---

@app.get("/api/gamedata/items")
async def get_items(category: Optional[str] = None, content_pack_id: str = DEFAULT_CONTENT_PACK_ID):
    """Get all items, optionally filtered by category"""
    data = load_game_data("items.json", content_pack_id=content_pack_id)
    
    if category:
        return {"items": {category: data.get(category, [])}, "category": category}
    
    # Return items in expected format - items contains the category arrays
    # Filter out metadata keys
    item_categories = ["weapons", "armor", "consumables", "accessories", "gear", "ammunition", "materials"]
    items = {k: v for k, v in data.items() if k in item_categories}
    return {"items": items}


@app.put("/api/gamedata/items")
async def update_all_items(items_data: Dict[str, Any]):
    """Bulk update item data while preserving metadata keys when omitted."""
    existing = load_game_data("items.json")
    existing.update(items_data.get("items", items_data))
    if save_game_data("items.json", existing):
        return {"message": "Items updated"}
    raise HTTPException(status_code=500, detail="Failed to save")

@app.get("/api/gamedata/items/categories")
async def get_item_categories():
    """Get item categories and metadata"""
    data = load_game_data("items.json")
    return {
        "categories": data.get("item_categories", []),
        "rarity_tiers": data.get("rarity_tiers", {}),
        "equipment_slots": data.get("equipment_slots", {})
    }

@app.get("/api/gamedata/items/{category}/{item_id}")
async def get_item(category: str, item_id: str):
    """Get a specific item"""
    data = load_game_data("items.json")
    items = data.get(category, [])
    
    for item in items:
        if item.get("id") == item_id:
            return {"item": item, "category": category}
    
    raise HTTPException(status_code=404, detail="Item not found")

class ItemCreate(BaseModel):
    id: str
    name: str
    type: str
    subtype: Optional[str] = None
    description: str = ""
    rarity: str = "common"
    price: int = 0
    weight: float = 0
    properties: List[str] = []
    # Weapon fields
    damage: Optional[str] = None
    damage_type: Optional[str] = None
    # Armor fields
    ac_base: Optional[int] = None
    ac_bonus: Optional[int] = None
    # Consumable fields
    effect: Optional[Dict[str, Any]] = None

@app.post("/api/gamedata/items/{category}")
async def create_item(category: str, item: ItemCreate):
    """Create a new item in a category"""
    data = load_game_data("items.json")
    
    if category not in data:
        data[category] = []
    
    # Check if ID exists
    for existing in data[category]:
        if existing.get("id") == item.id:
            raise HTTPException(status_code=400, detail="Item ID already exists")
    
    item_data = {k: v for k, v in item.dict().items() if v is not None}
    data[category].append(item_data)
    
    if save_game_data("items.json", data):
        return {"message": "Item created", "id": item.id}
    raise HTTPException(status_code=500, detail="Failed to save")

@app.delete("/api/gamedata/items/{category}/{item_id}")
async def delete_item(category: str, item_id: str):
    """Delete an item"""
    data = load_game_data("items.json")
    items = data.get(category, [])
    
    for i, item in enumerate(items):
        if item.get("id") == item_id:
            del items[i]
            data[category] = items
            if save_game_data("items.json", data):
                return {"message": "Item deleted"}
            raise HTTPException(status_code=500, detail="Failed to save")
    
    raise HTTPException(status_code=404, detail="Item not found")

# --- SPELLS ---

@app.get("/api/gamedata/spells")
async def get_spells(school: Optional[str] = None, level: Optional[int] = None, content_pack_id: str = DEFAULT_CONTENT_PACK_ID):
    """Get all spells, optionally filtered"""
    data = load_game_data("spells.json", content_pack_id=content_pack_id)
    spells = data.get("spells", {})
    
    if school or level is not None:
        filtered = {}
        for spell_id, spell in spells.items():
            if school and spell.get("school", "").lower() != school.lower():
                continue
            if level is not None and spell.get("level") != level:
                continue
            filtered[spell_id] = spell
        return {"spells": filtered}
    
    return {"spells": spells}


@app.put("/api/gamedata/spells")
async def update_all_spells(spells_data: Dict[str, Any]):
    """Bulk update spell data while preserving class lists when omitted."""
    existing = load_game_data("spells.json")
    if "spells" in spells_data:
        existing["spells"] = spells_data["spells"]
    else:
        existing.update(spells_data)
    if save_game_data("spells.json", existing):
        return {"message": "Spells updated"}
    raise HTTPException(status_code=500, detail="Failed to save")

@app.get("/api/gamedata/spells/class-lists")
async def get_class_spell_lists():
    """Get spell lists by class"""
    data = load_game_data("spells.json")
    return {"class_spell_lists": data.get("class_spell_lists", {})}

@app.get("/api/gamedata/spells/{spell_id}")
async def get_spell(spell_id: str):
    """Get a specific spell"""
    data = load_game_data("spells.json")
    spells = data.get("spells", {})
    if spell_id not in spells:
        raise HTTPException(status_code=404, detail="Spell not found")
    return {"spell": spells[spell_id], "id": spell_id}

class SpellUpdate(BaseModel):
    name: Optional[str] = None
    level: Optional[int] = None
    school: Optional[str] = None
    casting_time: Optional[str] = None
    range: Optional[str] = None
    components: Optional[List[str]] = None
    duration: Optional[str] = None
    description: Optional[str] = None
    damage: Optional[str] = None
    damage_type: Optional[str] = None
    healing: Optional[str] = None
    effect: Optional[str] = None
    upcast: Optional[str] = None
    classes: Optional[List[str]] = None

@app.patch("/api/gamedata/spells/{spell_id}")
async def update_spell(spell_id: str, update: SpellUpdate):
    """Update a spell"""
    data = load_game_data("spells.json")
    spells = data.get("spells", {})
    
    if spell_id not in spells:
        raise HTTPException(status_code=404, detail="Spell not found")
    
    for key, value in update.dict().items():
        if value is not None:
            spells[spell_id][key] = value
    
    data["spells"] = spells
    if save_game_data("spells.json", data):
        return {"message": "Spell updated", "spell": spells[spell_id]}
    raise HTTPException(status_code=500, detail="Failed to save")

# ============================================================================
# COMBAT ENDPOINTS
# ============================================================================

@app.get("/api/combat")
async def list_combats(session_id: Optional[int] = None, status: Optional[str] = None):
    """List combat encounters"""
    import aiosqlite
    async with aiosqlite.connect(db.db_path) as conn:
        conn.row_factory = aiosqlite.Row
        query = "SELECT * FROM combat_encounters WHERE 1=1"
        params = []
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC"
        cursor = await conn.execute(query, params)
        combats = [dict(row) for row in await cursor.fetchall()]
    return {"combats": combats}

@app.get("/api/combat/active")
async def get_active_combat(session_id: int = Query(...)):
    """Get active combat for a session"""
    import aiosqlite
    async with aiosqlite.connect(db.db_path) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute(
            "SELECT * FROM combat_encounters WHERE session_id = ? AND status = 'active' ORDER BY created_at DESC LIMIT 1",
            (session_id,)
        )
        combat = await cursor.fetchone()
        if not combat:
            return {"combat": None}
        combat = dict(combat)
        
        cursor = await conn.execute("SELECT * FROM combat_participants WHERE encounter_id = ?", (combat['id'],))
        combat['participants'] = [dict(row) for row in await cursor.fetchall()]
    return {"combat": combat}

@app.get("/api/combat/{combat_id}")
async def get_combat(combat_id: int):
    """Get combat encounter with participants"""
    import aiosqlite
    async with aiosqlite.connect(db.db_path) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute("SELECT * FROM combat_encounters WHERE id = ?", (combat_id,))
        combat = await cursor.fetchone()
        if not combat:
            raise HTTPException(status_code=404, detail="Combat not found")
        combat = dict(combat)
        
        # Get participants
        cursor = await conn.execute("SELECT * FROM combat_participants WHERE encounter_id = ?", (combat_id,))
        participants = [dict(row) for row in await cursor.fetchall()]
        combat['participants'] = participants
    return combat


@app.post("/api/combat/{combat_id}/spawn-template")
async def spawn_combat_template_enemy(combat_id: int, spawn: CombatMonsterSpawn):
    """Spawn one or more monster-template combatants into an encounter."""
    combat = await get_combat(combat_id)
    if not combat:
        raise HTTPException(status_code=404, detail="Combat not found")

    session = await db.get_session(combat['session_id']) if combat.get('session_id') else None
    context = {
        'session_id': combat.get('session_id'),
        'guild_id': combat.get('guild_id'),
    }
    if session:
        context['content_pack_id'] = session.get('content_pack_id')

    try:
        created_ids = await tools.spawn_enemy_template_combatants(
            combat['id'],
            spawn.template_id,
            count=spawn.count,
            context=context,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"combatant_ids": created_ids, "message": "Monster spawned"}

# ============================================================================
# CHARACTER SPELLS & ABILITIES ENDPOINTS
# ============================================================================

@app.get("/api/characters/{char_id}/spells")
async def get_character_spells(char_id: int, prepared_only: bool = False):
    """Get character's known spells"""
    spells = await db.get_character_spells(char_id, prepared_only)
    slots = await db.get_spell_slots(char_id)
    return {"spells": spells, "spell_slots": slots}

@app.get("/api/characters/{char_id}/abilities")
async def get_character_abilities(char_id: int):
    """Get character's class abilities"""
    abilities = await db.get_character_abilities(char_id)
    return {"abilities": abilities}

@app.get("/api/characters/{char_id}/skills")
async def get_character_skills(char_id: int):
    """Get character's unlocked skills"""
    skills = await db.get_character_skills(char_id)
    skill_points = await db.get_skill_points(char_id)
    return {"skills": skills, "skill_points": skill_points}

@app.get("/api/characters/{char_id}/status-effects")
async def get_character_status_effects(char_id: int):
    """Get character's active status effects"""
    effects = await db.get_status_effects(char_id)
    return {"status_effects": effects}

@app.post("/api/characters/{char_id}/spells/{spell_id}/prepare")
async def prepare_spell(char_id: int, spell_id: str, prepare: bool = True):
    """Prepare or unprepare a spell"""
    await db.set_spell_prepared(char_id, spell_id, prepare)
    return {"message": f"Spell {'prepared' if prepare else 'unprepared'}"}

@app.post("/api/characters/{char_id}/rest/{rest_type}")
async def character_rest(char_id: int, rest_type: str):
    """Have character take a rest"""
    if rest_type == "long":
        result = await db.long_rest(char_id)
    else:
        result = await db.short_rest(char_id)
    return result

# ============================================================================
# LOCATION CONNECTIONS ENDPOINTS
# ============================================================================

@app.get("/api/locations/{location_id}/connections")
async def get_location_connections(location_id: int):
    """Get all connections from/to a location"""
    connections = await db.get_nearby_locations(location_id)
    return {"connections": connections}


@app.get("/api/location-connections")
async def list_location_connections(location_id: Optional[int] = None, session_id: Optional[int] = None):
    """List canonical location connection records."""
    connections = await db.list_location_connections(location_id=location_id, session_id=session_id)
    return {"connections": connections}


@app.post("/api/location-connections")
async def create_location_connection_resource(connection: LocationConnectionCreate):
    """Create a canonical location connection."""
    try:
        connection_id = await db.create_location_connection(**connection.dict())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"id": connection_id, "message": "Location connection created"}


@app.patch("/api/location-connections/{connection_id}")
async def update_location_connection_resource(connection_id: int, connection: LocationConnectionUpdate):
    """Update a canonical location connection."""
    updates = {k: v for k, v in connection.dict().items() if v is not None}
    if not updates:
        return {"message": "Location connection updated"}
    try:
        updated = await db.update_location_connection(connection_id, **updates)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not updated:
        raise HTTPException(status_code=404, detail="Location connection not found")
    return {"message": "Location connection updated"}


@app.delete("/api/location-connections/{connection_id}")
async def delete_location_connection_resource(connection_id: int):
    """Delete a canonical location connection."""
    deleted = await db.delete_location_connection(connection_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Location connection not found")
    return {"message": "Location connection deleted"}


# Preserve module-level names used by direct tests while keeping
# distinct internal handler names from the legacy compatibility wrapper.
create_location_connection = create_location_connection_resource
update_location_connection = update_location_connection_resource
delete_location_connection = delete_location_connection_resource

@app.post("/api/locations/{from_id}/connect/{to_id}")
async def create_location_connection_legacy(
    from_id: int, 
    to_id: int,
    direction: str = "path",
    travel_time: int = 1,
    hidden: bool = False
):
    """Create a connection between two locations"""
    try:
        await db.create_location_connection(
            from_location_id=from_id,
            to_location_id=to_id,
            direction=direction,
            travel_time=travel_time,
            hidden=hidden,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"message": "Locations connected"}

# ============================================================================
# NPC RELATIONSHIPS ENDPOINT
# ============================================================================

@app.get("/api/npcs/{npc_id}/relationships")
async def get_npc_relationships(npc_id: int):
    """Get all relationships for an NPC"""
    import aiosqlite
    async with aiosqlite.connect(db.db_path) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute("""
            SELECT nr.*, c.name as character_name
            FROM npc_relationships nr
            JOIN characters c ON nr.character_id = c.id
            WHERE nr.npc_id = ?
        """, (npc_id,))
        relationships = [dict(row) for row in await cursor.fetchall()]
    return {"relationships": relationships}


# ============================================================================
# STORYLINE / PLOT ENDPOINTS
# ============================================================================

@app.get("/api/storylines")
async def list_storylines(session_id: Optional[int] = None, guild_id: Optional[int] = None):
    """List storylines."""
    storylines = await db.get_storylines(session_id=session_id, guild_id=guild_id)
    return {"storylines": storylines}


@app.post("/api/storylines")
async def create_storyline(storyline: StorylineCreate):
    """Create a storyline."""
    storyline_id = await db.create_storyline(**storyline.dict())
    return {"id": storyline_id, "message": "Storyline created"}


@app.patch("/api/storylines/{storyline_id}")
async def update_storyline(storyline_id: int, storyline: StorylineUpdate):
    """Update a storyline."""
    updates = {k: v for k, v in storyline.dict().items() if v is not None}
    if updates:
        updated = await db.update_storyline(storyline_id, **updates)
        if not updated:
            raise HTTPException(status_code=404, detail="Storyline not found")
    return {"message": "Storyline updated"}


@app.get("/api/storylines/{storyline_id}")
async def get_storyline(storyline_id: int):
    """Get a storyline with nodes and edges."""
    state = await db.get_storyline_state(storyline_id)
    if not state:
        raise HTTPException(status_code=404, detail="Storyline not found")
    return state


@app.delete("/api/storylines/{storyline_id}")
async def delete_storyline(storyline_id: int):
    """Delete a storyline."""
    deleted = await db.delete_storyline(storyline_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Storyline not found")
    return {"message": "Storyline deleted"}


@app.get("/api/storylines/{storyline_id}/quests")
async def get_storyline_quests(storyline_id: int):
    """List quests attached to a storyline."""
    storyline = await db.get_storyline(storyline_id)
    if not storyline:
        raise HTTPException(status_code=404, detail="Storyline not found")
    quests = await db.get_storyline_quests(storyline_id)
    return {"quests": quests}


@app.post("/api/storylines/{storyline_id}/nodes")
async def create_storyline_node(storyline_id: int, node: StorylineNodeCreate):
    """Create a storyline node."""
    node_id = await db.create_storyline_node(storyline_id=storyline_id, **node.dict())
    return {"id": node_id, "message": "Storyline node created"}


@app.post("/api/storylines/{storyline_id}/edges")
async def create_storyline_edge(storyline_id: int, edge: StorylineEdgeCreate):
    """Create a storyline edge."""
    edge_id = await db.create_storyline_edge(storyline_id=storyline_id, **edge.dict())
    return {"id": edge_id, "message": "Storyline edge created"}


@app.post("/api/storylines/{storyline_id}/advance")
async def advance_storyline(storyline_id: int, payload: StorylineAdvanceRequest):
    """Advance storyline progress to a specific node."""
    result = await db.advance_storyline_node(
        storyline_id=storyline_id,
        to_node_id=payload.node_id,
        character_id=payload.character_id,
        branch_choice=payload.branch_choice,
        variables=payload.variables,
    )
    if result.get('error'):
        raise HTTPException(status_code=400, detail=result['error'])
    return result


@app.get("/api/sessions/{session_id}/storyline-state")
async def get_session_storyline_state(session_id: int):
    """Get storyline state for a session."""
    storylines = await db.get_storylines(session_id=session_id)
    return {
        "storylines": [await db.get_storyline_state(storyline['id']) for storyline in storylines]
    }


@app.get("/api/campaign/overview")
async def get_campaign_overview(session_id: int):
    """Get a session campaign overview for studio/admin surfaces."""
    overview = await db.get_campaign_overview(session_id)
    if not overview:
        raise HTTPException(status_code=404, detail="Session not found")
    return overview


@app.get("/api/plot-points")
async def list_plot_points(session_id: Optional[int] = None, storyline_id: Optional[int] = None):
    """List plot points."""
    plot_points = await db.get_plot_points(session_id=session_id, storyline_id=storyline_id)
    return {"plot_points": plot_points}


@app.post("/api/plot-points")
async def create_plot_point(plot_point: PlotPointCreate):
    """Create a plot point."""
    plot_point_id = await db.create_plot_point(**plot_point.dict())
    return {"id": plot_point_id, "message": "Plot point created"}


@app.patch("/api/plot-points/{plot_point_id}")
async def update_plot_point(plot_point_id: int, plot_point: PlotPointUpdate):
    """Update a plot point."""
    updates = {k: v for k, v in plot_point.dict().items() if v is not None}
    if updates:
        updated = await db.update_plot_point(plot_point_id, **updates)
        if not updated:
            raise HTTPException(status_code=404, detail="Plot point not found")
    return {"message": "Plot point updated"}


@app.delete("/api/plot-points/{plot_point_id}")
async def delete_plot_point(plot_point_id: int):
    """Delete a plot point."""
    deleted = await db.delete_plot_point(plot_point_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Plot point not found")
    return {"message": "Plot point deleted"}


@app.post("/api/plot-clues/{clue_id}/discover")
async def discover_plot_clue(clue_id: int, character_id: Optional[int] = Query(None)):
    """Mark a plot clue as discovered."""
    result = await db.discover_clue(clue_id, discovered_by=character_id)
    if result.get('error'):
        raise HTTPException(status_code=404, detail=result['error'])
    return result


# ============================================================================
# CAMPAIGN CREATION / WORLDBUILDING ENDPOINTS
# ============================================================================

class CampaignSettings(BaseModel):
    """Settings for generating a new campaign"""
    guild_id: int
    dm_user_id: int
    name: str
    
    # World settings
    world_theme: str = "fantasy"  # fantasy, sci-fi, horror, modern, steampunk
    content_pack_id: Optional[str] = None
    world_scale: str = "regional"  # local, regional, continental, world
    magic_level: str = "high"  # none, low, medium, high
    technology_level: str = "medieval"  # primitive, medieval, renaissance, industrial, modern, futuristic
    tone: str = "heroic"  # gritty, heroic, comedic, horror, mystery
    
    # Generation options
    num_locations: int = 5
    num_npcs: int = 8
    num_factions: int = 3
    num_quest_hooks: int = 3
    
    # Custom prompts (optional)
    world_description: Optional[str] = None
    key_events: Optional[str] = None
    special_rules: Optional[str] = None


class WorldPreview(BaseModel):
    """Preview data for a generated world"""
    session_id: int
    world_setting: Dict[str, Any]
    locations: List[Dict[str, Any]]
    npcs: List[Dict[str, Any]]
    factions: List[Dict[str, Any]]
    quest_hooks: List[Dict[str, Any]]
    starting_scenario: str


@app.post("/api/campaign/generate-preview")
async def generate_campaign_preview(settings: CampaignSettings):
    """Generate a campaign preview using AI worldbuilding.
    
    This creates the world data in memory so users can review and tweak
    before finalizing. Uses LLM to generate rich, interconnected content.
    """
    import random
    
    # Convert settings to dict for LLM
    settings_dict = {
        'name': settings.name,
        'world_theme': settings.world_theme,
        'world_scale': settings.world_scale,
        'magic_level': settings.magic_level,
        'technology_level': settings.technology_level,
        'tone': settings.tone,
        'num_locations': settings.num_locations,
        'num_npcs': settings.num_npcs,
        'num_factions': settings.num_factions,
        'num_quest_hooks': settings.num_quest_hooks,
        'world_description': settings.world_description,
        'key_events': settings.key_events,
        'special_rules': settings.special_rules
    }
    
    # Try AI generation if LLM client is available
    if llm_client:
        try:
            logger.info(f"Generating AI campaign preview for '{settings.name}'...")
            generated = await llm_client.generate_campaign_world(settings_dict)
            
            # Build response from generated content
            world_setting = generated.get('world_setting', {})
            # Ensure required fields
            world_setting['theme'] = settings.world_theme
            world_setting['magic_level'] = settings.magic_level
            world_setting['technology_level'] = settings.technology_level
            world_setting['tone'] = settings.tone
            
            return {
                "preview": {
                    "world_setting": world_setting,
                    "locations": generated.get('locations', []),
                    "npcs": generated.get('npcs', []),
                    "factions": generated.get('factions', []),
                    "quest_hooks": generated.get('quest_hooks', []),
                    "starting_scenario": generated.get('starting_scenario', 'Your adventure begins...')
                },
                "settings": settings.dict()
            }
        except Exception as e:
            logger.error(f"AI generation failed, falling back to placeholders: {e}")
            # Fall through to placeholder generation
    
    # Fallback: Generate placeholder data if no LLM or if generation failed
    logger.info("Using placeholder campaign data (no LLM available)")
    
    world_setting = {
        "name": f"{settings.name} World",
        "theme": settings.world_theme,
        "magic_level": settings.magic_level,
        "technology_level": settings.technology_level,
        "tone": settings.tone,
        "description": f"A {settings.tone} {settings.world_theme} world where {settings.magic_level} magic exists alongside {settings.technology_level} technology.",
        "history": "A world shaped by ancient conflicts and emerging powers.",
        "current_state": "A time of change and opportunity for adventurers."
    }
    
    # Generate location templates
    location_types = ["city", "town", "dungeon", "wilderness", "landmark"]
    locations = []
    for i in range(settings.num_locations):
        loc_type = location_types[i % len(location_types)]
        locations.append({
            "id": f"loc_{i}",
            "name": f"Location {i + 1}",
            "type": loc_type,
            "description": f"A {loc_type} waiting to be explored.",
            "danger_level": random.randint(1, 5),
            "points_of_interest": [],
            "connections": []
        })
    
    # Generate NPC templates
    npc_types = ["merchant", "quest_giver", "ally", "neutral", "antagonist"]
    npcs = []
    for i in range(settings.num_npcs):
        npc_type = npc_types[i % len(npc_types)]
        npcs.append({
            "id": f"npc_{i}",
            "name": f"NPC {i + 1}",
            "type": npc_type,
            "description": f"A {npc_type} character.",
            "personality": "To be determined",
            "goals": "Unknown",
            "is_party_member_candidate": npc_type == "ally"
        })
    
    # Generate faction templates
    factions = []
    for i in range(settings.num_factions):
        factions.append({
            "id": f"faction_{i}",
            "name": f"Faction {i + 1}",
            "type": ["guild", "kingdom", "cult", "merchant_group"][i % 4],
            "alignment": ["good", "neutral", "evil"][i % 3],
            "description": "A powerful group with their own agenda.",
            "goals": "Expand influence",
            "key_npcs": []
        })
    
    # Generate quest hooks
    quest_hooks = []
    quest_types = ["main", "side", "character"]
    for i in range(settings.num_quest_hooks):
        quest_hooks.append({
            "id": f"quest_{i}",
            "title": f"Quest Hook {i + 1}",
            "name": f"Quest Hook {i + 1}",
            "type": quest_types[i % len(quest_types)],
            "description": "An adventure awaits...",
            "difficulty": ["easy", "medium", "hard"][i % 3],
            "rewards": {"gold": (i + 1) * 100, "xp": (i + 1) * 50}
        })
    
    # Generate starting scenario
    starting_scenario = f"""Welcome to {world_setting['name']}!

The party gathers at the crossroads of fate. In this {settings.tone} {settings.world_theme} world, 
adventure calls to those brave enough to answer.

Your journey begins in {locations[0]['name'] if locations else 'a mysterious place'}..."""
    
    return {
        "preview": {
            "world_setting": world_setting,
            "locations": locations,
            "npcs": npcs,
            "factions": factions,
            "quest_hooks": quest_hooks,
            "starting_scenario": starting_scenario
        },
        "settings": settings.dict()
    }


class CampaignFinalize(BaseModel):
    """Finalized campaign data to commit to database"""
    guild_id: int
    dm_user_id: int
    name: str
    description: Optional[str] = None
    content_pack_id: Optional[str] = None
    world_setting: Dict[str, Any]
    locations: List[Dict[str, Any]]
    npcs: List[Dict[str, Any]]
    factions: List[Dict[str, Any]]
    quest_hooks: List[Dict[str, Any]]
    starting_scenario: str
    generation_settings: Dict[str, Any] = {}


@app.post("/api/campaign/finalize")
async def finalize_campaign(data: CampaignFinalize):
    """Commit the generated/edited campaign to the database.
    
    Creates the session, locations, NPCs, and quests.
    """
    return await db.create_campaign_from_preview(**data.dict())


@app.get("/api/campaign/templates")
async def get_campaign_templates():
    """Get predefined campaign templates for quick setup"""
    return {
        "templates": [
            {
                "id": "classic_fantasy",
                "name": "Classic Fantasy",
                "description": "A traditional sword & sorcery adventure",
                "settings": {
                    "world_theme": "fantasy",
                    "world_scale": "regional",
                    "magic_level": "high",
                    "technology_level": "medieval",
                    "tone": "heroic"
                }
            },
            {
                "id": "dark_fantasy",
                "name": "Dark Fantasy",
                "description": "A gritty world where survival is everything",
                "settings": {
                    "world_theme": "fantasy",
                    "world_scale": "regional",
                    "magic_level": "low",
                    "technology_level": "medieval",
                    "tone": "gritty"
                }
            },
            {
                "id": "steampunk_adventure",
                "name": "Steampunk Adventure",
                "description": "Steam-powered machines and Victorian intrigue",
                "settings": {
                    "world_theme": "steampunk",
                    "world_scale": "continental",
                    "magic_level": "low",
                    "technology_level": "industrial",
                    "tone": "mystery"
                }
            },
            {
                "id": "cosmic_horror",
                "name": "Cosmic Horror",
                "description": "Uncover forbidden knowledge at great cost",
                "settings": {
                    "world_theme": "horror",
                    "world_scale": "local",
                    "magic_level": "medium",
                    "technology_level": "renaissance",
                    "tone": "horror"
                }
            },
            {
                "id": "space_opera",
                "name": "Space Opera",
                "description": "Epic adventures across the galaxy",
                "settings": {
                    "world_theme": "sci-fi",
                    "world_scale": "world",
                    "magic_level": "none",
                    "technology_level": "futuristic",
                    "tone": "heroic"
                }
            }
        ]
    }


# ============================================================================
# STATIC FILES (Frontend)
# ============================================================================


# Mount static files for frontend
frontend_path = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.get("/")
async def serve_frontend():
    """Serve frontend"""
    index_path = os.path.join(os.path.dirname(__file__), "frontend", "dist", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Frontend not built. Run 'npm run build' in web/frontend/"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
