"""
RPG DM Bot - Web API
FastAPI server for the web management frontend.
Provides REST endpoints for sessions, locations, NPCs, items, events, and saves.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import sys
import os
import logging

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from src.database import Database
from src.llm import LLMClient

logger = logging.getLogger('rpg.api')

# Initialize FastAPI app
app = FastAPI(
    title="RPG DM Bot Manager",
    description="Web management interface for the AI Dungeon Master bot",
    version="1.0.0"
)

# Initialize LLM client for worldbuilding (if API key available)
REQUESTY_API_KEY = os.getenv('REQUESTY_API_KEY')
LLM_MODEL = os.getenv('LLM_MODEL', 'openai/gpt-4o-mini')
llm_client: Optional[LLMClient] = None

if REQUESTY_API_KEY:
    llm_client = LLMClient(REQUESTY_API_KEY, LLM_MODEL)
    logger.info("LLM client initialized for worldbuilding")
else:
    logger.warning("REQUESTY_API_KEY not set - worldbuilding will use placeholder data")

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
    points_of_interest: List[str] = []
    current_weather: Optional[str] = None
    danger_level: int = 0
    hidden_secrets: Optional[str] = None

class LocationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    location_type: Optional[str] = None
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
    is_merchant: bool = False

class NPCUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    personality: Optional[str] = None
    npc_type: Optional[str] = None
    location: Optional[str] = None
    is_merchant: Optional[bool] = None

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
    lore: Optional[str] = None
    is_discovered: Optional[bool] = None

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
    status: Optional[str] = None
    trigger_conditions: Optional[str] = None

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
    difficulty: str = "medium"
    quest_giver_npc_id: Optional[int] = None
    dm_notes: Optional[str] = None

class QuestUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    objectives: Optional[List[str]] = None
    rewards: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    difficulty: Optional[str] = None
    dm_notes: Optional[str] = None

# ============================================================================
# STARTUP / SHUTDOWN
# ============================================================================

@app.on_event("startup")
async def startup():
    await db.init()

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

# ============================================================================
# LOCATION ENDPOINTS
# ============================================================================

@app.get("/api/locations")
async def list_locations(session_id: Optional[int] = None, guild_id: Optional[int] = None):
    """List locations"""
    locations = await db.get_locations(session_id=session_id, guild_id=guild_id)
    return {"locations": locations}

@app.get("/api/locations/{location_id}")
async def get_location(location_id: int):
    """Get a location"""
    loc = await db.get_location(location_id)
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")
    return loc

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

@app.delete("/api/locations/{location_id}")
async def delete_location(location_id: int):
    """Delete a location"""
    await db.delete_location(location_id)
    return {"message": "Location deleted"}

@app.post("/api/locations/{location_id}/connect/{target_id}")
async def connect_locations(location_id: int, target_id: int):
    """Connect two locations"""
    await db.connect_locations(location_id, target_id)
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
            npcs = [dict(row) for row in await cursor.fetchall()]
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

@app.delete("/api/npcs/{npc_id}")
async def delete_npc(npc_id: int):
    """Delete an NPC"""
    await db.delete_npc(npc_id)
    return {"message": "NPC deleted"}

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
    await db.resolve_event(event_id, outcome, notes)
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
        description=snapshot.description
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
    import aiosqlite
    async with aiosqlite.connect(db.db_path) as conn:
        conn.row_factory = aiosqlite.Row
        query = "SELECT * FROM quests WHERE 1=1"
        params = []
        
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        if guild_id:
            query += " AND guild_id = ?"
            params.append(guild_id)
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY created_at DESC"
        cursor = await conn.execute(query, params)
        quests = []
        for row in await cursor.fetchall():
            quest = dict(row)
            quest['objectives'] = json.loads(quest['objectives']) if quest.get('objectives') else []
            quest['rewards'] = json.loads(quest['rewards']) if quest.get('rewards') else {}
            quests.append(quest)
        return {"quests": quests}

@app.get("/api/quests/{quest_id}")
async def get_quest(quest_id: int):
    """Get a quest"""
    import aiosqlite
    async with aiosqlite.connect(db.db_path) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute("SELECT * FROM quests WHERE id = ?", (quest_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Quest not found")
        quest = dict(row)
        quest['objectives'] = json.loads(quest['objectives']) if quest.get('objectives') else []
        quest['rewards'] = json.loads(quest['rewards']) if quest.get('rewards') else {}
        return quest

@app.post("/api/quests")
async def create_quest(quest: QuestCreate):
    """Create a quest"""
    import aiosqlite
    now = datetime.now().isoformat()
    
    async with aiosqlite.connect(db.db_path) as conn:
        cursor = await conn.execute("""
            INSERT INTO quests (guild_id, session_id, title, description, objectives, 
                rewards, status, difficulty, quest_giver_npc_id, dm_notes, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'available', ?, ?, ?, ?, ?)
        """, (
            quest.guild_id, quest.session_id, quest.title, quest.description,
            json.dumps(quest.objectives), json.dumps(quest.rewards),
            quest.difficulty, quest.quest_giver_npc_id, quest.dm_notes,
            quest.created_by, now
        ))
        await conn.commit()
        return {"id": cursor.lastrowid, "message": "Quest created"}

@app.patch("/api/quests/{quest_id}")
async def update_quest(quest_id: int, quest: QuestUpdate):
    """Update a quest"""
    import aiosqlite
    
    async with aiosqlite.connect(db.db_path) as conn:
        updates = []
        values = []
        
        if quest.title is not None:
            updates.append("title = ?")
            values.append(quest.title)
        if quest.description is not None:
            updates.append("description = ?")
            values.append(quest.description)
        if quest.objectives is not None:
            updates.append("objectives = ?")
            values.append(json.dumps(quest.objectives))
        if quest.rewards is not None:
            updates.append("rewards = ?")
            values.append(json.dumps(quest.rewards))
        if quest.status is not None:
            updates.append("status = ?")
            values.append(quest.status)
        if quest.difficulty is not None:
            updates.append("difficulty = ?")
            values.append(quest.difficulty)
        if quest.dm_notes is not None:
            updates.append("dm_notes = ?")
            values.append(quest.dm_notes)
        
        if updates:
            values.append(quest_id)
            await conn.execute(
                f"UPDATE quests SET {', '.join(updates)} WHERE id = ?",
                values
            )
            await conn.commit()
    
    return {"message": "Quest updated"}

@app.delete("/api/quests/{quest_id}")
async def delete_quest(quest_id: int):
    """Delete a quest"""
    import aiosqlite
    async with aiosqlite.connect(db.db_path) as conn:
        await conn.execute("DELETE FROM quest_progress WHERE quest_id = ?", (quest_id,))
        await conn.execute("DELETE FROM quests WHERE id = ?", (quest_id,))
        await conn.commit()
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
async def get_npc_templates():
    """Get NPC generation templates"""
    import json
    template_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "data", "game_data", "npc_templates.json"
    )
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {"templates": {}}

# ============================================================================
# GAME DATA ENDPOINTS - Classes, Races, Skills, Items, Spells
# ============================================================================

def load_game_data(filename: str) -> Dict[str, Any]:
    """Load game data from JSON file"""
    filepath = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "data", "game_data", filename
    )
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        return {"error": str(e)}

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
async def get_classes():
    """Get all character classes"""
    data = load_game_data("classes.json")
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
async def get_races():
    """Get all races"""
    data = load_game_data("races.json")
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
async def get_skills():
    """Get all skills and skill trees"""
    data = load_game_data("skills.json")
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
async def get_items(category: Optional[str] = None):
    """Get all items, optionally filtered by category"""
    data = load_game_data("items.json")
    
    if category:
        return {"items": {category: data.get(category, [])}, "category": category}
    
    # Return items in expected format - items contains the category arrays
    # Filter out metadata keys
    item_categories = ["weapons", "armor", "consumables", "accessories", "gear", "ammunition", "materials"]
    items = {k: v for k, v in data.items() if k in item_categories}
    return {"items": items}

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
async def get_spells(school: Optional[str] = None, level: Optional[int] = None):
    """Get all spells, optionally filtered"""
    data = load_game_data("spells.json")
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

@app.get("/api/combat/active")
async def get_active_combat(session_id: int):
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

@app.post("/api/locations/{from_id}/connect/{to_id}")
async def create_location_connection(
    from_id: int, 
    to_id: int,
    direction: str = "path",
    travel_time: int = 1,
    bidirectional: bool = True,
    hidden: bool = False
):
    """Create a connection between two locations"""
    await db.connect_locations(
        from_id, to_id, 
        direction=direction,
        travel_time=travel_time,
        bidirectional=bidirectional,
        hidden=hidden
    )
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
# CAMPAIGN CREATION / WORLDBUILDING ENDPOINTS
# ============================================================================

class CampaignSettings(BaseModel):
    """Settings for generating a new campaign"""
    guild_id: int
    dm_user_id: int
    name: str
    
    # World settings
    world_theme: str = "fantasy"  # fantasy, sci-fi, horror, modern, steampunk
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
    world_setting: Dict[str, Any]
    locations: List[Dict[str, Any]]
    npcs: List[Dict[str, Any]]
    factions: List[Dict[str, Any]]
    quest_hooks: List[Dict[str, Any]]
    starting_scenario: str


@app.post("/api/campaign/finalize")
async def finalize_campaign(data: CampaignFinalize):
    """Commit the generated/edited campaign to the database.
    
    Creates the session, locations, NPCs, and quests.
    """
    import aiosqlite
    from datetime import datetime
    
    async with aiosqlite.connect(db.db_path) as conn:
        conn.row_factory = aiosqlite.Row
        
        # Create the session (set to 'active' so it's immediately playable)
        cursor = await conn.execute("""
            INSERT INTO sessions (guild_id, name, description, dm_user_id, status, created_at)
            VALUES (?, ?, ?, ?, 'active', ?)
        """, (data.guild_id, data.name, data.description or data.starting_scenario[:200], 
              data.dm_user_id, datetime.utcnow().isoformat()))
        session_id = cursor.lastrowid
        
        # Create game state
        await conn.execute("""
            INSERT INTO game_state (session_id, current_scene, dm_notes)
            VALUES (?, ?, ?)
        """, (session_id, data.starting_scenario, json.dumps(data.world_setting)))
        
        location_id_map = {}  # Map preview IDs to real IDs
        now = datetime.utcnow().isoformat()
        
        # Create locations
        for loc in data.locations:
            cursor = await conn.execute("""
                INSERT INTO locations (session_id, guild_id, name, description, location_type, 
                                       danger_level, created_by, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (session_id, data.guild_id, loc['name'], loc.get('description', ''),
                  loc.get('type', 'generic'), loc.get('danger_level', 1),
                  data.dm_user_id, now, now))
            location_id_map[loc['id']] = cursor.lastrowid
        
        npc_id_map = {}  # Map preview IDs to real IDs
        
        # Create NPCs
        for npc in data.npcs:
            # Find location name if assigned (npcs uses 'location' TEXT, not location_id)
            location_name = None
            if npc.get('location_id') and npc['location_id'] in location_id_map:
                # Get the location name from the data
                for loc in data.locations:
                    if loc['id'] == npc.get('location_id'):
                        location_name = loc['name']
                        break
            
            cursor = await conn.execute("""
                INSERT INTO npcs (session_id, guild_id, name, description, personality, 
                                  npc_type, location, is_party_member, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (session_id, data.guild_id, npc['name'], npc.get('description', ''),
                  npc.get('personality', ''), npc.get('type', 'neutral'), location_name,
                  1 if npc.get('is_party_member_candidate') else 0,
                  data.dm_user_id, now))
            npc_id_map[npc['id']] = cursor.lastrowid
        
        # Create quests
        for quest in data.quest_hooks:
            quest_giver_id = None
            if quest.get('quest_giver_id') and quest['quest_giver_id'] in npc_id_map:
                quest_giver_id = npc_id_map[quest['quest_giver_id']]
            
            await conn.execute("""
                INSERT INTO quests (session_id, guild_id, title, description, objectives, 
                                    rewards, status, difficulty, quest_giver_npc_id, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'available', ?, ?, ?, ?)
            """, (session_id, data.guild_id, quest['title'], quest.get('description', ''),
                  json.dumps(quest.get('objectives', [])), json.dumps(quest.get('rewards', {})),
                  quest.get('difficulty', 'medium'), quest_giver_id, data.dm_user_id, now))
        
        await conn.commit()
    
    return {
        "success": True,
        "session_id": session_id,
        "message": f"Campaign '{data.name}' created successfully!",
        "stats": {
            "locations_created": len(data.locations),
            "npcs_created": len(data.npcs),
            "quests_created": len(data.quest_hooks)
        }
    }


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
