/**
 * RPG DM Bot Manager - Main TypeScript Application
 * Handles navigation, API calls, and UI interactions
 */

// ============================================================================
// API CLIENT
// ============================================================================

const API_BASE = window.location.hostname === 'localhost'
    ? 'http://localhost:8000/api'
    : '/api';

interface ApiResponse<T> {
    [key: string]: T;
}

async function apiCall<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${API_BASE}${endpoint}`;
    const defaultOptions: RequestInit = {
        headers: {
            'Content-Type': 'application/json',
        },
    };

    const response = await fetch(url, { ...defaultOptions, ...options });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(error.detail || `API Error: ${response.status}`);
    }

    return response.json();
}

// API Functions
const api = {
    // Stats
    getStats: () => apiCall<{ sessions: number, characters: number, locations: number, npcs: number }>('/stats'),

    // Sessions
    getSessions: () => apiCall<{ sessions: any[] }>('/sessions'),
    getSession: (id: number) => apiCall<any>(`/sessions/${id}`),
    createSession: (data: any) => apiCall<{ id: number }>('/sessions', { method: 'POST', body: JSON.stringify(data) }),
    updateSession: (id: number, data: any) => apiCall<any>(`/sessions/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),

    // Locations
    getLocations: () => apiCall<{ locations: any[] }>('/locations'),
    getLocation: (id: number) => apiCall<any>(`/locations/${id}`),
    createLocation: (data: any) => apiCall<{ id: number }>('/locations', { method: 'POST', body: JSON.stringify(data) }),
    updateLocation: (id: number, data: any) => apiCall<any>(`/locations/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    deleteLocation: (id: number) => apiCall<any>(`/locations/${id}`, { method: 'DELETE' }),

    // NPCs
    getNPCs: () => apiCall<{ npcs: any[] }>('/npcs'),
    getNPC: (id: number) => apiCall<any>(`/npcs/${id}`),
    createNPC: (data: any) => apiCall<{ id: number }>('/npcs', { method: 'POST', body: JSON.stringify(data) }),
    updateNPC: (id: number, data: any) => apiCall<any>(`/npcs/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    deleteNPC: (id: number) => apiCall<any>(`/npcs/${id}`, { method: 'DELETE' }),

    // Story Items
    getItems: () => apiCall<{ items: any[] }>('/items'),
    getItem: (id: number) => apiCall<any>(`/items/${id}`),
    createItem: (data: any) => apiCall<{ id: number }>('/items', { method: 'POST', body: JSON.stringify(data) }),
    updateItem: (id: number, data: any) => apiCall<any>(`/items/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    deleteItem: (id: number) => apiCall<any>(`/items/${id}`, { method: 'DELETE' }),
    revealItem: (id: number) => apiCall<any>(`/items/${id}/reveal`, { method: 'POST' }),

    // Story Events
    getEvents: () => apiCall<{ events: any[] }>('/events'),
    getEvent: (id: number) => apiCall<any>(`/events/${id}`),
    createEvent: (data: any) => apiCall<{ id: number }>('/events', { method: 'POST', body: JSON.stringify(data) }),
    updateEvent: (id: number, data: any) => apiCall<any>(`/events/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    deleteEvent: (id: number) => apiCall<any>(`/events/${id}`, { method: 'DELETE' }),
    triggerEvent: (id: number) => apiCall<any>(`/events/${id}/trigger`, { method: 'POST' }),
    resolveEvent: (id: number, outcome: string) => apiCall<any>(`/events/${id}/resolve?outcome=${outcome}`, { method: 'POST' }),

    // Snapshots
    getSnapshots: (sessionId: number) => apiCall<{ snapshots: any[] }>(`/snapshots?session_id=${sessionId}`),
    createSnapshot: (data: any) => apiCall<{ id: number }>('/snapshots', { method: 'POST', body: JSON.stringify(data) }),
    loadSnapshot: (id: number) => apiCall<any>(`/snapshots/${id}/load`, { method: 'POST' }),
    deleteSnapshot: (id: number) => apiCall<any>(`/snapshots/${id}`, { method: 'DELETE' }),

    // Characters
    getCharacters: () => apiCall<{ characters: any[] }>('/characters'),
    getCharacter: (id: number) => apiCall<any>(`/characters/${id}`),
    updateCharacter: (id: number, data: any) => apiCall<any>(`/characters/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),

    // Inventory
    getInventory: (charId: number) => apiCall<{ inventory: any[] }>(`/characters/${charId}/inventory`),
    addInventoryItem: (charId: number, data: any) => apiCall<{ id: number }>(`/characters/${charId}/inventory`, { method: 'POST', body: JSON.stringify(data) }),
    updateInventoryItem: (inventoryId: number, data: any) => apiCall<any>(`/inventory/${inventoryId}`, { method: 'PATCH', body: JSON.stringify(data) }),
    equipItem: (inventoryId: number, slot?: string) => apiCall<any>(`/inventory/${inventoryId}/equip${slot ? `?slot=${slot}` : ''}`, { method: 'POST' }),
    unequipItem: (inventoryId: number) => apiCall<any>(`/inventory/${inventoryId}/unequip`, { method: 'POST' }),
    deleteInventoryItem: (inventoryId: number, quantity?: number) => apiCall<any>(`/inventory/${inventoryId}${quantity ? `?quantity=${quantity}` : ''}`, { method: 'DELETE' }),

    // Character Spells & Abilities
    getCharacterSpells: (charId: number, preparedOnly?: boolean) => 
        apiCall<{ spells: any[], spell_slots: any }>(`/characters/${charId}/spells${preparedOnly ? '?prepared_only=true' : ''}`),
    getCharacterAbilities: (charId: number) => apiCall<{ abilities: any[] }>(`/characters/${charId}/abilities`),
    getCharacterSkills: (charId: number) => apiCall<{ skills: any[], skill_points: any }>(`/characters/${charId}/skills`),
    getCharacterStatusEffects: (charId: number) => apiCall<{ status_effects: any[] }>(`/characters/${charId}/status-effects`),
    prepareSpell: (charId: number, spellId: string, prepare: boolean) => 
        apiCall<any>(`/characters/${charId}/spells/${spellId}/prepare?prepare=${prepare}`, { method: 'POST' }),
    characterRest: (charId: number, restType: string) => apiCall<any>(`/characters/${charId}/rest/${restType}`, { method: 'POST' }),

    // Combat
    getCombats: (sessionId?: number, status?: string) => {
        let url = '/combat';
        const params = new URLSearchParams();
        if (sessionId) params.append('session_id', sessionId.toString());
        if (status) params.append('status', status);
        if (params.toString()) url += '?' + params.toString();
        return apiCall<{ combats: any[] }>(url);
    },
    getCombat: (combatId: number) => apiCall<any>(`/combat/${combatId}`),
    getActiveCombat: (sessionId: number) => apiCall<{ combat: any }>(`/combat/active?session_id=${sessionId}`),

    // Location Connections
    getLocationConnections: (locationId: number) => apiCall<{ connections: any[] }>(`/locations/${locationId}/connections`),
    connectLocations: (fromId: number, toId: number, direction?: string, bidirectional?: boolean) => {
        let url = `/locations/${fromId}/connect/${toId}`;
        const params = new URLSearchParams();
        if (direction) params.append('direction', direction);
        if (bidirectional !== undefined) params.append('bidirectional', bidirectional.toString());
        if (params.toString()) url += '?' + params.toString();
        return apiCall<any>(url, { method: 'POST' });
    },

    // NPC Relationships
    getNPCRelationships: (npcId: number) => apiCall<{ relationships: any[] }>(`/npcs/${npcId}/relationships`),

    // Quests
    getQuests: () => apiCall<{ quests: any[] }>('/quests'),
    getQuest: (id: number) => apiCall<any>(`/quests/${id}`),
    createQuest: (data: any) => apiCall<{ id: number }>('/quests', { method: 'POST', body: JSON.stringify(data) }),
    updateQuest: (id: number, data: any) => apiCall<any>(`/quests/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    deleteQuest: (id: number) => apiCall<any>(`/quests/${id}`, { method: 'DELETE' }),

    // Templates
    getNPCTemplates: () => apiCall<any>('/templates/npcs'),

    // Game Data - Classes
    getClasses: () => apiCall<any>('/gamedata/classes'),
    updateClasses: (data: any) => apiCall<any>('/gamedata/classes', { method: 'PUT', body: JSON.stringify(data) }),

    // Game Data - Races
    getRaces: () => apiCall<any>('/gamedata/races'),
    updateRaces: (data: any) => apiCall<any>('/gamedata/races', { method: 'PUT', body: JSON.stringify(data) }),

    // Game Data - Skills
    getAllSkills: () => apiCall<any>('/gamedata/skills/trees'),
    getClassSkills: (className: string) => apiCall<any>(`/gamedata/skills/trees/${className}`),
    updateClassSkills: (className: string, data: any) => apiCall<any>(`/gamedata/skills/trees/${className}`, { method: 'PUT', body: JSON.stringify(data) }),

    // Game Data - Items
    getGameItems: (category?: string, rarity?: string) => {
        let url = '/gamedata/items';
        const params = new URLSearchParams();
        if (category) params.append('category', category);
        if (rarity) params.append('rarity', rarity);
        if (params.toString()) url += '?' + params.toString();
        return apiCall<any>(url);
    },
    updateGameItems: (data: any) => apiCall<any>('/gamedata/items', { method: 'PUT', body: JSON.stringify(data) }),

    // Game Data - Spells
    getGameSpells: (school?: string, level?: number) => {
        let url = '/gamedata/spells';
        const params = new URLSearchParams();
        if (school) params.append('school', school);
        if (level !== undefined) params.append('level', level.toString());
        if (params.toString()) url += '?' + params.toString();
        return apiCall<any>(url);
    },
    updateGameSpells: (data: any) => apiCall<any>('/gamedata/spells', { method: 'PUT', body: JSON.stringify(data) }),

    // Campaign Creation
    getCampaignTemplates: () => apiCall<{ templates: any[] }>('/campaign/templates'),
    generateCampaignPreview: (settings: any) => apiCall<{ preview: any, settings: any }>('/campaign/generate-preview', { method: 'POST', body: JSON.stringify(settings) }),
    finalizeCampaign: (data: any) => apiCall<{ success: boolean, session_id: number, message: string, stats: any }>('/campaign/finalize', { method: 'POST', body: JSON.stringify(data) }),
};

// ============================================================================
// NAVIGATION
// ============================================================================

function showPage(pageId: string): void {
    // Update active nav item
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.toggle('active', item.getAttribute('data-page') === pageId);
    });

    // Update active page
    document.querySelectorAll('.page').forEach(page => {
        page.classList.toggle('active', page.id === `${pageId}-page`);
    });

    // Load page data
    loadPageData(pageId);
}

async function loadPageData(pageId: string): Promise<void> {
    try {
        switch (pageId) {
            case 'dashboard':
                await loadDashboard();
                break;
            case 'sessions':
                await loadSessions();
                break;
            case 'locations':
                await loadLocations();
                break;
            case 'npcs':
                await loadNPCs();
                break;
            case 'items':
                await loadItems();
                break;
            case 'events':
                await loadEvents();
                break;
            case 'saves':
                await loadSavesPage();
                break;
            case 'characters':
                await loadCharacters();
                break;
            case 'quests':
                await loadQuests();
                break;
            case 'classes':
                await loadClasses();
                break;
            case 'races':
                await loadRaces();
                break;
            case 'skilltrees':
                await loadSkillTrees();
                break;
            case 'itemdb':
                await loadItemDb();
                break;
            case 'spellbook':
                await loadSpellbook();
                break;
            case 'campaign-creator':
                await loadCampaignCreator();
                break;
        }
    } catch (error) {
        console.error(`Error loading ${pageId}:`, error);
        showToast(`Failed to load ${pageId}`, 'error');
    }
}

// ============================================================================
// DASHBOARD
// ============================================================================

async function loadDashboard(): Promise<void> {
    try {
        const stats = await api.getStats();

        (document.getElementById('stat-sessions') as HTMLElement).textContent = String(stats.sessions);
        (document.getElementById('stat-characters') as HTMLElement).textContent = String(stats.characters);
        (document.getElementById('stat-locations') as HTMLElement).textContent = String(stats.locations);
        (document.getElementById('stat-npcs') as HTMLElement).textContent = String(stats.npcs);

        // Load recent activity
        const activity = document.getElementById('recent-activity')!;
        activity.innerHTML = `
            <div class="activity-item">
                <span class="activity-icon">✅</span>
                <span class="activity-text">API connected successfully</span>
            </div>
            <div class="activity-item">
                <span class="activity-icon">📊</span>
                <span class="activity-text">${stats.sessions} sessions, ${stats.characters} characters</span>
            </div>
        `;
    } catch (error) {
        console.error('Dashboard error:', error);
        showToast('Failed to load dashboard stats', 'error');
    }
}

// ============================================================================
// SESSIONS
// ============================================================================

async function loadSessions(): Promise<void> {
    const container = document.getElementById('sessions-list')!;
    container.innerHTML = '<div class="loading-spinner">Loading sessions...</div>';

    try {
        const data = await api.getSessions();
        const sessions = data.sessions || [];

        if (sessions.length === 0) {
            container.innerHTML = '<div class="empty-state">No sessions yet. Create one to get started!</div>';
            return;
        }

        container.innerHTML = sessions.map((session: any) => `
            <div class="entity-card" data-id="${session.id}">
                <div class="entity-header">
                    <span class="entity-title">${escapeHtml(session.name)}</span>
                    <span class="entity-badge ${session.status}">${session.status}</span>
                </div>
                <p class="entity-desc">${escapeHtml(session.description || 'No description')}</p>
                <div class="entity-meta">
                    <span>👥 ${session.max_players} max players</span>
                    <span>📅 ${formatDate(session.created_at)}</span>
                </div>
                <div class="entity-actions">
                    <button class="btn btn-small btn-secondary" onclick="viewSession(${session.id})">View</button>
                    <button class="btn btn-small btn-primary" onclick="createSavepoint(${session.id})">💾 Save</button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        container.innerHTML = '<div class="empty-state">Failed to load sessions. Is the API running?</div>';
    }
}

async function createSession(event: Event): Promise<void> {
    event.preventDefault();

    const data = {
        name: (document.getElementById('session-name') as HTMLInputElement).value,
        description: (document.getElementById('session-desc') as HTMLTextAreaElement).value,
        guild_id: parseInt((document.getElementById('session-guild') as HTMLInputElement).value),
        dm_user_id: parseInt((document.getElementById('session-dm') as HTMLInputElement).value),
        max_players: 6
    };

    try {
        await api.createSession(data);
        showToast('Session created successfully!', 'success');
        closeModal('session-modal');
        (document.getElementById('session-form') as HTMLFormElement).reset();
        loadSessions();
    } catch (error) {
        showToast('Failed to create session', 'error');
    }
}

async function viewSession(id: number): Promise<void> {
    try {
        const data = await api.getSession(id);
        const session = data.session;
        const characters = data.characters || [];
        const npcs = data.npcs || [];
        const locations = data.locations || [];
        
        // Populate the session detail modal
        const content = `
            <div class="session-detail">
                <div class="session-info">
                    <h3>📋 Session Info</h3>
                    <p><strong>Name:</strong> ${escapeHtml(session?.name || 'Unknown')}</p>
                    <p><strong>Status:</strong> <span class="entity-badge ${session?.status}">${session?.status || 'unknown'}</span></p>
                    <p><strong>Description:</strong> ${escapeHtml(session?.description || 'No description')}</p>
                    <p><strong>Max Players:</strong> ${session?.max_players || 6}</p>
                    <p><strong>Created:</strong> ${formatDate(session?.created_at)}</p>
                </div>
                
                <div class="session-section">
                    <h3>⚔️ Characters (${characters.length})</h3>
                    ${characters.length === 0 ? '<p class="empty-hint">No characters in this session</p>' : `
                        <div class="mini-card-list">
                            ${characters.map((c: any) => `
                                <div class="mini-card">
                                    <strong>${escapeHtml(c.name)}</strong>
                                    <span>Lvl ${c.level} ${escapeHtml(c.char_class || c.class || '')}</span>
                                    <span>❤️ ${c.hp}/${c.max_hp}</span>
                                </div>
                            `).join('')}
                        </div>
                    `}
                </div>
                
                <div class="session-section">
                    <h3>🗺️ Locations (${locations.length})</h3>
                    ${locations.length === 0 ? '<p class="empty-hint">No locations in this session</p>' : `
                        <div class="mini-card-list">
                            ${locations.map((l: any) => `
                                <div class="mini-card">
                                    <strong>${escapeHtml(l.name)}</strong>
                                    <span>${l.location_type}</span>
                                    <span>⚠️ ${l.danger_level}/10</span>
                                </div>
                            `).join('')}
                        </div>
                    `}
                </div>
                
                <div class="session-section">
                    <h3>👥 NPCs (${npcs.length})</h3>
                    ${npcs.length === 0 ? '<p class="empty-hint">No NPCs in this session</p>' : `
                        <div class="mini-card-list">
                            ${npcs.map((n: any) => `
                                <div class="mini-card">
                                    <strong>${escapeHtml(n.name)}</strong>
                                    <span class="entity-badge ${n.npc_type}">${n.npc_type}</span>
                                    ${n.is_merchant ? '<span>🛒</span>' : ''}
                                </div>
                            `).join('')}
                        </div>
                    `}
                </div>
            </div>
        `;
        
        document.getElementById('session-detail-content')!.innerHTML = content;
        document.getElementById('session-detail-title')!.textContent = `🎮 ${session?.name || 'Session Details'}`;
        openModal('session-detail-modal');
    } catch (error) {
        showToast('Failed to load session details', 'error');
    }
}

// ============================================================================
// LOCATIONS
// ============================================================================

async function loadLocations(): Promise<void> {
    const container = document.getElementById('locations-list')!;
    container.innerHTML = '<div class="loading-spinner">Loading locations...</div>';

    try {
        const data = await api.getLocations();
        const locations = data.locations || [];

        if (locations.length === 0) {
            container.innerHTML = '<div class="empty-state">No locations yet. Start building your world!</div>';
            return;
        }

        container.innerHTML = locations.map((loc: any) => `
            <div class="entity-card" data-id="${loc.id}">
                <div class="entity-header">
                    <span class="entity-title">${escapeHtml(loc.name)}</span>
                    <span class="entity-badge">${loc.location_type}</span>
                </div>
                <p class="entity-desc">${escapeHtml(loc.description || 'No description')}</p>
                <div class="entity-meta">
                    <span>⚠️ Danger: ${loc.danger_level}/10</span>
                    <span>🌤️ ${loc.current_weather || 'Unknown'}</span>
                </div>
                <div class="entity-actions">
                    <button class="btn btn-small btn-secondary" onclick="editLocation(${loc.id})">Edit</button>
                    <button class="btn btn-small btn-danger" onclick="deleteLocation(${loc.id})">Delete</button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        container.innerHTML = '<div class="empty-state">Failed to load locations</div>';
    }
}

async function createLocation(event: Event): Promise<void> {
    event.preventDefault();

    const data = {
        name: (document.getElementById('location-name') as HTMLInputElement).value,
        description: (document.getElementById('location-desc') as HTMLTextAreaElement).value,
        location_type: (document.getElementById('location-type') as HTMLSelectElement).value,
        danger_level: parseInt((document.getElementById('location-danger') as HTMLInputElement).value),
        current_weather: (document.getElementById('location-weather') as HTMLInputElement).value,
        hidden_secrets: (document.getElementById('location-secrets') as HTMLTextAreaElement).value,
        guild_id: 1, // Default
        created_by: 1 // Default
    };

    try {
        await api.createLocation(data);
        showToast('Location created!', 'success');
        closeModal('location-modal');
        (document.getElementById('location-form') as HTMLFormElement).reset();
        loadLocations();
    } catch (error) {
        showToast('Failed to create location', 'error');
    }
}

async function deleteLocation(id: number): Promise<void> {
    if (!confirm('Are you sure you want to delete this location?')) return;

    try {
        await api.deleteLocation(id);
        showToast('Location deleted', 'success');
        loadLocations();
    } catch (error) {
        showToast('Failed to delete location', 'error');
    }
}

// ============================================================================
// NPCs
// ============================================================================

async function loadNPCs(): Promise<void> {
    const container = document.getElementById('npcs-list')!;
    container.innerHTML = '<div class="loading-spinner">Loading NPCs...</div>';

    try {
        const data = await api.getNPCs();
        const npcs = data.npcs || [];

        if (npcs.length === 0) {
            container.innerHTML = '<div class="empty-state">No NPCs yet. Create memorable characters!</div>';
            return;
        }

        container.innerHTML = npcs.map((npc: any) => `
            <div class="entity-card" data-id="${npc.id}">
                <div class="entity-header">
                    <span class="entity-title">${escapeHtml(npc.name)}</span>
                    <span class="entity-badge ${npc.npc_type}">${npc.npc_type}</span>
                </div>
                <p class="entity-desc">${escapeHtml(npc.description || 'No description')}</p>
                <div class="entity-meta">
                    <span>📍 ${npc.location || 'Unknown'}</span>
                    ${npc.is_merchant ? '<span>🛒 Merchant</span>' : ''}
                </div>
                <div class="entity-actions">
                    <button class="btn btn-small btn-secondary" onclick="editNPC(${npc.id})">Edit</button>
                    <button class="btn btn-small btn-danger" onclick="deleteNPC(${npc.id})">Delete</button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        container.innerHTML = '<div class="empty-state">Failed to load NPCs</div>';
    }
}

async function createNPC(event: Event): Promise<void> {
    event.preventDefault();

    const data = {
        name: (document.getElementById('npc-name') as HTMLInputElement).value,
        description: (document.getElementById('npc-desc') as HTMLTextAreaElement).value,
        personality: (document.getElementById('npc-personality') as HTMLTextAreaElement).value,
        npc_type: (document.getElementById('npc-type') as HTMLSelectElement).value,
        location: (document.getElementById('npc-location') as HTMLInputElement).value,
        is_merchant: (document.getElementById('npc-merchant') as HTMLInputElement).checked,
        guild_id: 1,
        created_by: 1
    };

    try {
        await api.createNPC(data);
        showToast('NPC created!', 'success');
        closeModal('npc-modal');
        (document.getElementById('npc-form') as HTMLFormElement).reset();
        loadNPCs();
    } catch (error) {
        showToast('Failed to create NPC', 'error');
    }
}

async function deleteNPC(id: number): Promise<void> {
    if (!confirm('Are you sure you want to delete this NPC?')) return;

    try {
        await api.deleteNPC(id);
        showToast('NPC deleted', 'success');
        loadNPCs();
    } catch (error) {
        showToast('Failed to delete NPC', 'error');
    }
}

// ============================================================================
// STORY ITEMS
// ============================================================================

async function loadItems(): Promise<void> {
    const container = document.getElementById('items-list')!;
    container.innerHTML = '<div class="loading-spinner">Loading items...</div>';

    try {
        const data = await api.getItems();
        const items = data.items || [];

        if (items.length === 0) {
            container.innerHTML = '<div class="empty-state">No story items yet. Create artifacts and clues!</div>';
            return;
        }

        container.innerHTML = items.map((item: any) => `
            <div class="entity-card" data-id="${item.id}">
                <div class="entity-header">
                    <span class="entity-title">${escapeHtml(item.name)}</span>
                    <span class="entity-badge ${item.is_discovered ? 'active' : 'pending'}">${item.is_discovered ? 'Discovered' : 'Hidden'}</span>
                </div>
                <p class="entity-desc">${escapeHtml(item.description || 'No description')}</p>
                <div class="entity-meta">
                    <span>📦 ${item.item_type}</span>
                </div>
                <div class="entity-actions">
                    ${!item.is_discovered ? `<button class="btn btn-small btn-primary" onclick="revealItem(${item.id})">👁️ Reveal</button>` : ''}
                    <button class="btn btn-small btn-secondary" onclick="editItem(${item.id})">Edit</button>
                    <button class="btn btn-small btn-danger" onclick="deleteItem(${item.id})">Delete</button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        container.innerHTML = '<div class="empty-state">Failed to load items</div>';
    }
}

async function createItem(event: Event): Promise<void> {
    event.preventDefault();

    const data = {
        name: (document.getElementById('item-name') as HTMLInputElement).value,
        description: (document.getElementById('item-desc') as HTMLTextAreaElement).value,
        item_type: (document.getElementById('item-type') as HTMLSelectElement).value,
        lore: (document.getElementById('item-lore') as HTMLTextAreaElement).value,
        discovery_conditions: (document.getElementById('item-discovery') as HTMLInputElement).value,
        dm_notes: (document.getElementById('item-notes') as HTMLTextAreaElement).value,
        guild_id: 1,
        created_by: 1
    };

    try {
        await api.createItem(data);
        showToast('Story item created!', 'success');
        closeModal('item-modal');
        (document.getElementById('item-form') as HTMLFormElement).reset();
        loadItems();
    } catch (error) {
        showToast('Failed to create item', 'error');
    }
}

async function revealItem(id: number): Promise<void> {
    try {
        await api.revealItem(id);
        showToast('Item revealed to players!', 'success');
        loadItems();
    } catch (error) {
        showToast('Failed to reveal item', 'error');
    }
}

// ============================================================================
// STORY EVENTS
// ============================================================================

async function loadEvents(): Promise<void> {
    const container = document.getElementById('events-list')!;
    container.innerHTML = '<div class="loading-spinner">Loading events...</div>';

    try {
        const data = await api.getEvents();
        const events = data.events || [];

        if (events.length === 0) {
            container.innerHTML = '<div class="empty-state">No story events yet. Plan your plot twists!</div>';
            return;
        }

        container.innerHTML = events.map((ev: any) => `
            <div class="entity-card" data-id="${ev.id}">
                <div class="entity-header">
                    <span class="entity-title">${escapeHtml(ev.name)}</span>
                    <span class="entity-badge ${ev.status}">${ev.status}</span>
                </div>
                <p class="entity-desc">${escapeHtml(ev.description || 'No description')}</p>
                <div class="entity-meta">
                    <span>📋 ${ev.event_type}</span>
                </div>
                <div class="entity-actions">
                    ${ev.status === 'pending' ? `<button class="btn btn-small btn-primary" onclick="triggerEvent(${ev.id})">⚡ Trigger</button>` : ''}
                    ${ev.status === 'active' ? `<button class="btn btn-small btn-success" onclick="resolveEvent(${ev.id})">✅ Resolve</button>` : ''}
                    <button class="btn btn-small btn-secondary" onclick="editEvent(${ev.id})">Edit</button>
                    <button class="btn btn-small btn-danger" onclick="deleteEvent(${ev.id})">Delete</button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        container.innerHTML = '<div class="empty-state">Failed to load events</div>';
    }
}

async function createEvent(event: Event): Promise<void> {
    event.preventDefault();

    const data = {
        name: (document.getElementById('event-name') as HTMLInputElement).value,
        description: (document.getElementById('event-desc') as HTMLTextAreaElement).value,
        event_type: (document.getElementById('event-type') as HTMLSelectElement).value,
        trigger_conditions: (document.getElementById('event-trigger') as HTMLInputElement).value,
        dm_notes: (document.getElementById('event-notes') as HTMLTextAreaElement).value,
        guild_id: 1,
        created_by: 1
    };

    try {
        await api.createEvent(data);
        showToast('Story event created!', 'success');
        closeModal('event-modal');
        (document.getElementById('event-form') as HTMLFormElement).reset();
        loadEvents();
    } catch (error) {
        showToast('Failed to create event', 'error');
    }
}

async function triggerEvent(id: number): Promise<void> {
    try {
        await api.triggerEvent(id);
        showToast('Event triggered!', 'success');
        loadEvents();
    } catch (error) {
        showToast('Failed to trigger event', 'error');
    }
}

async function resolveEvent(id: number): Promise<void> {
    const outcome = prompt('Event outcome? (success/failure/partial)') || 'success';
    try {
        await api.resolveEvent(id, outcome);
        showToast('Event resolved!', 'success');
        loadEvents();
    } catch (error) {
        showToast('Failed to resolve event', 'error');
    }
}

// ============================================================================
// SAVE POINTS
// ============================================================================

async function loadSavesPage(): Promise<void> {
    const select = document.getElementById('save-session-select') as HTMLSelectElement;

    try {
        const data = await api.getSessions();
        const sessions = data.sessions || [];

        select.innerHTML = '<option value="">-- Select Session --</option>' +
            sessions.map((s: any) => `<option value="${s.id}">${escapeHtml(s.name)}</option>`).join('');
    } catch (error) {
        select.innerHTML = '<option value="">Failed to load sessions</option>';
    }
}

async function loadSnapshots(): Promise<void> {
    const select = document.getElementById('save-session-select') as HTMLSelectElement;
    const container = document.getElementById('saves-list')!;

    const sessionId = parseInt(select.value);
    if (!sessionId) {
        container.innerHTML = '<div class="empty-state">Select a session to view save points</div>';
        return;
    }

    container.innerHTML = '<div class="loading-spinner">Loading save points...</div>';

    try {
        const data = await api.getSnapshots(sessionId);
        const snapshots = data.snapshots || [];

        if (snapshots.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    No save points yet.
                    <button class="btn btn-primary" onclick="createSavepoint(${sessionId})" style="margin-top: 1rem;">
                        💾 Create Save Point
                    </button>
                </div>
            `;
            return;
        }

        container.innerHTML = snapshots.map((snap: any) => `
            <div class="entity-card" data-id="${snap.id}">
                <div class="entity-header">
                    <span class="entity-title">💾 ${escapeHtml(snap.name)}</span>
                    <span class="entity-badge">${snap.snapshot_type}</span>
                </div>
                <p class="entity-desc">${escapeHtml(snap.description || 'No description')}</p>
                <div class="entity-meta">
                    <span>📅 ${formatDate(snap.created_at)}</span>
                </div>
                <div class="entity-actions">
                    <button class="btn btn-small btn-primary" onclick="loadSavepoint(${snap.id})">⏪ Load</button>
                    <button class="btn btn-small btn-danger" onclick="deleteSavepoint(${snap.id})">Delete</button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        container.innerHTML = '<div class="empty-state">Failed to load save points</div>';
    }
}

async function createSavepoint(sessionId: number): Promise<void> {
    const name = prompt('Save point name:') || `Save ${new Date().toLocaleString()}`;

    try {
        await api.createSnapshot({
            session_id: sessionId,
            name: name,
            created_by: 1,
            description: 'Manual save point'
        });
        showToast('Save point created!', 'success');
        loadSnapshots();
    } catch (error) {
        showToast('Failed to create save point', 'error');
    }
}

async function loadSavepoint(id: number): Promise<void> {
    if (!confirm('Load this save point? Current progress will be overwritten.')) return;

    try {
        await api.loadSnapshot(id);
        showToast('Save point loaded!', 'success');
    } catch (error) {
        showToast('Failed to load save point', 'error');
    }
}

async function deleteSavepoint(id: number): Promise<void> {
    if (!confirm('Delete this save point?')) return;

    try {
        await api.deleteSnapshot(id);
        showToast('Save point deleted', 'success');
        loadSnapshots();
    } catch (error) {
        showToast('Failed to delete save point', 'error');
    }
}

// ============================================================================
// CHARACTERS
// ============================================================================

async function loadCharacters(): Promise<void> {
    const container = document.getElementById('characters-list')!;
    container.innerHTML = '<div class="loading-spinner">Loading characters...</div>';

    try {
        const data = await api.getCharacters();
        const characters = data.characters || [];

        if (characters.length === 0) {
            container.innerHTML = '<div class="empty-state">No characters yet. Players need to join via Discord!</div>';
            return;
        }

        container.innerHTML = characters.map((char: any) => `
            <div class="entity-card" data-id="${char.id}">
                <div class="entity-header">
                    <span class="entity-title">${escapeHtml(char.name)}</span>
                    <span class="entity-badge">Lvl ${char.level} ${escapeHtml(char.char_class || char.class || '')}</span>
                </div>
                <p class="entity-desc">${escapeHtml(char.backstory || 'No backstory')}</p>
                <div class="entity-meta">
                    <span>❤️ HP: ${char.hp}/${char.max_hp}</span>
                    <span>✨ MP: ${char.mana}/${char.max_mana}</span>
                    <span>💰 ${char.gold}g</span>
                </div>
                <div class="entity-actions">
                    <button class="btn btn-small btn-primary" onclick="showCharacterInventory(${char.id})">🎒 Inventory</button>
                    <button class="btn btn-small btn-secondary" onclick="editCharacter(${char.id})">Edit</button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        container.innerHTML = '<div class="empty-state">Failed to load characters</div>';
    }
}

async function editCharacter(id: number): Promise<void> {
    try {
        const char = await api.getCharacter(id);

        (document.getElementById('char-id') as HTMLInputElement).value = char.id;
        (document.getElementById('char-name') as HTMLInputElement).value = char.name;
        (document.getElementById('char-class') as HTMLInputElement).value = char.char_class || '';
        (document.getElementById('char-race') as HTMLInputElement).value = char.race || '';
        (document.getElementById('char-level') as HTMLInputElement).value = char.level;
        (document.getElementById('char-hp') as HTMLInputElement).value = char.hp;
        (document.getElementById('char-max-hp') as HTMLInputElement).value = char.max_hp;
        (document.getElementById('char-mana') as HTMLInputElement).value = char.mana;
        (document.getElementById('char-max-mana') as HTMLInputElement).value = char.max_mana;
        (document.getElementById('char-gold') as HTMLInputElement).value = char.gold;
        (document.getElementById('char-backstory') as HTMLTextAreaElement).value = char.backstory || '';

        openModal('character-modal');
    } catch (error) {
        showToast('Failed to load character details', 'error');
    }
}

async function updateCharacter(event: Event): Promise<void> {
    event.preventDefault();

    const id = parseInt((document.getElementById('char-id') as HTMLInputElement).value);
    const data = {
        name: (document.getElementById('char-name') as HTMLInputElement).value,
        char_class: (document.getElementById('char-class') as HTMLInputElement).value,
        race: (document.getElementById('char-race') as HTMLInputElement).value,
        level: parseInt((document.getElementById('char-level') as HTMLInputElement).value),
        hp: parseInt((document.getElementById('char-hp') as HTMLInputElement).value),
        max_hp: parseInt((document.getElementById('char-max-hp') as HTMLInputElement).value),
        mana: parseInt((document.getElementById('char-mana') as HTMLInputElement).value),
        max_mana: parseInt((document.getElementById('char-max-mana') as HTMLInputElement).value),
        gold: parseInt((document.getElementById('char-gold') as HTMLInputElement).value),
        backstory: (document.getElementById('char-backstory') as HTMLTextAreaElement).value
    };

    try {
        await api.updateCharacter(id, data);
        showToast('Character updated!', 'success');
        closeModal('character-modal');
        loadCharacters();
    } catch (error) {
        showToast('Failed to update character', 'error');
    }
}

// ============================================================================
// INVENTORY MANAGEMENT
// ============================================================================

let currentCharacterIdForInventory: number | null = null;

async function showCharacterInventory(charId: number): Promise<void> {
    currentCharacterIdForInventory = charId;
    
    try {
        const char = await api.getCharacter(charId);
        const inventoryData = await api.getInventory(charId);
        const inventory = inventoryData.inventory || [];
        
        document.getElementById('inventory-char-name')!.textContent = char.name;
        
        const container = document.getElementById('inventory-list')!;
        
        if (inventory.length === 0) {
            container.innerHTML = '<div class="empty-state">No items in inventory</div>';
        } else {
            container.innerHTML = inventory.map((item: any) => `
                <div class="inventory-item ${item.is_equipped ? 'equipped' : ''}">
                    <div class="inventory-item-info">
                        <span class="item-name">${escapeHtml(item.item_name)}</span>
                        <span class="item-type">${item.item_type}</span>
                        <span class="item-qty">x${item.quantity}</span>
                        ${item.is_equipped ? `<span class="equipped-badge">📍 ${item.slot}</span>` : ''}
                    </div>
                    <div class="inventory-item-actions">
                        ${item.is_equipped 
                            ? `<button class="btn btn-small" onclick="unequipItem(${item.id})">Unequip</button>`
                            : `<button class="btn btn-small btn-primary" onclick="equipItem(${item.id})">Equip</button>`
                        }
                        <button class="btn btn-small btn-danger" onclick="removeInventoryItem(${item.id})">Remove</button>
                    </div>
                </div>
            `).join('');
        }
        
        openModal('inventory-modal');
    } catch (error) {
        showToast('Failed to load inventory', 'error');
    }
}

async function equipItem(inventoryId: number): Promise<void> {
    try {
        await api.equipItem(inventoryId);
        showToast('Item equipped!', 'success');
        if (currentCharacterIdForInventory) {
            showCharacterInventory(currentCharacterIdForInventory);
        }
    } catch (error) {
        showToast('Failed to equip item', 'error');
    }
}

async function unequipItem(inventoryId: number): Promise<void> {
    try {
        await api.unequipItem(inventoryId);
        showToast('Item unequipped', 'success');
        if (currentCharacterIdForInventory) {
            showCharacterInventory(currentCharacterIdForInventory);
        }
    } catch (error) {
        showToast('Failed to unequip item', 'error');
    }
}

async function removeInventoryItem(inventoryId: number): Promise<void> {
    if (!confirm('Remove this item from inventory?')) return;
    
    try {
        await api.deleteInventoryItem(inventoryId);
        showToast('Item removed', 'success');
        if (currentCharacterIdForInventory) {
            showCharacterInventory(currentCharacterIdForInventory);
        }
    } catch (error) {
        showToast('Failed to remove item', 'error');
    }
}

async function addItemToInventory(event: Event): Promise<void> {
    event.preventDefault();
    
    if (!currentCharacterIdForInventory) {
        showToast('No character selected', 'error');
        return;
    }
    
    const data = {
        item_id: (document.getElementById('add-item-id') as HTMLInputElement).value || `item_${Date.now()}`,
        item_name: (document.getElementById('add-item-name') as HTMLInputElement).value,
        item_type: (document.getElementById('add-item-type') as HTMLSelectElement).value,
        quantity: parseInt((document.getElementById('add-item-quantity') as HTMLInputElement).value) || 1,
        properties: {}
    };
    
    try {
        await api.addInventoryItem(currentCharacterIdForInventory, data);
        showToast('Item added to inventory!', 'success');
        closeModal('add-item-modal');
        (document.getElementById('add-item-form') as HTMLFormElement).reset();
        showCharacterInventory(currentCharacterIdForInventory);
    } catch (error) {
        showToast('Failed to add item', 'error');
    }
}

// Item database cache for searching
let itemDbCache: any[] = [];
let itemDbLoaded = false;

async function loadItemDbCache(): Promise<void> {
    if (itemDbLoaded) return;
    
    try {
        const data = await api.getItems();
        itemDbCache = data.items || [];
        itemDbLoaded = true;
    } catch (error) {
        console.error('Failed to load item database:', error);
        itemDbCache = [];
    }
}

function searchItemDb(query: string): void {
    const results = document.getElementById('item-db-results')!;
    const typeFilter = (document.getElementById('item-db-type-filter') as HTMLSelectElement).value;
    
    if (!query && !typeFilter) {
        results.innerHTML = '<div class="empty-state">Search or browse the item database above</div>';
        return;
    }
    
    const filtered = itemDbCache.filter(item => {
        const matchesQuery = !query || 
            item.name.toLowerCase().includes(query.toLowerCase()) ||
            (item.description && item.description.toLowerCase().includes(query.toLowerCase()));
        const matchesType = !typeFilter || item.type === typeFilter;
        return matchesQuery && matchesType;
    }).slice(0, 20); // Limit to 20 results
    
    if (filtered.length === 0) {
        results.innerHTML = '<div class="empty-state">No items found</div>';
        return;
    }
    
    results.innerHTML = filtered.map(item => `
        <div class="item-db-item" onclick="addItemFromDb('${escapeHtml(item.id)}')">
            <div class="item-db-item-info">
                <span class="item-db-item-name">${escapeHtml(item.name)}</span>
                <span class="item-db-item-type">${item.type}</span>
                <span class="item-db-item-rarity ${item.rarity || 'common'}">${item.rarity || 'common'}</span>
            </div>
            <button class="btn btn-small btn-primary item-db-item-add">+ Add</button>
        </div>
    `).join('');
}

function filterItemDbByType(type: string): void {
    const query = (document.getElementById('item-db-search') as HTMLInputElement).value;
    searchItemDb(query);
}

async function addItemFromDb(itemId: string): Promise<void> {
    if (!currentCharacterIdForInventory) {
        showToast('No character selected', 'error');
        return;
    }
    
    const item = itemDbCache.find(i => i.id === itemId);
    if (!item) {
        showToast('Item not found', 'error');
        return;
    }
    
    const data = {
        item_id: item.id,
        item_name: item.name,
        item_type: item.type,
        quantity: 1,
        properties: item.stats || {}
    };
    
    try {
        await api.addInventoryItem(currentCharacterIdForInventory, data);
        showToast(`Added ${item.name} to inventory!`, 'success');
        showCharacterInventory(currentCharacterIdForInventory);
    } catch (error) {
        showToast('Failed to add item', 'error');
    }
}

async function openAddItemModal(): Promise<void> {
    // Load item database when opening the modal
    await loadItemDbCache();
    openModal('add-item-modal');
}

// ============================================================================
// QUESTS
// ============================================================================

async function loadQuests(): Promise<void> {
    const container = document.getElementById('quests-list')!;
    container.innerHTML = '<div class="loading-spinner">Loading quests...</div>';
    
    try {
        const data = await api.getQuests();
        const quests = data.quests || [];
        
        if (quests.length === 0) {
            container.innerHTML = '<div class="empty-state">No quests yet. Create epic adventures!</div>';
            return;
        }
        
        container.innerHTML = quests.map((quest: any) => `
            <div class="entity-card" data-id="${quest.id}">
                <div class="entity-header">
                    <span class="entity-title">${escapeHtml(quest.title)}</span>
                    <span class="entity-badge ${quest.status}">${quest.status}</span>
                </div>
                <p class="entity-desc">${escapeHtml(quest.description || 'No description')}</p>
                <div class="entity-meta">
                    <span>⚔️ ${quest.difficulty}</span>
                    <span>📋 ${(quest.objectives || []).length} objectives</span>
                </div>
                <div class="entity-actions">
                    <button class="btn btn-small btn-secondary" onclick="editQuest(${quest.id})">Edit</button>
                    <button class="btn btn-small btn-danger" onclick="deleteQuest(${quest.id})">Delete</button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        container.innerHTML = '<div class="empty-state">Failed to load quests</div>';
    }
}

async function createQuest(event: Event): Promise<void> {
    event.preventDefault();
    
    const objectivesText = (document.getElementById('quest-objectives') as HTMLTextAreaElement).value;
    const objectives = objectivesText.split('\n').filter(o => o.trim());
    
    const data = {
        title: (document.getElementById('quest-title') as HTMLInputElement).value,
        description: (document.getElementById('quest-desc') as HTMLTextAreaElement).value,
        difficulty: (document.getElementById('quest-difficulty') as HTMLSelectElement).value,
        objectives: objectives,
        dm_notes: (document.getElementById('quest-notes') as HTMLTextAreaElement).value,
        guild_id: 1,
        created_by: 1
    };
    
    try {
        await api.createQuest(data);
        showToast('Quest created!', 'success');
        closeModal('quest-modal');
        (document.getElementById('quest-form') as HTMLFormElement).reset();
        loadQuests();
    } catch (error) {
        showToast('Failed to create quest', 'error');
    }
}

async function editQuest(id: number): Promise<void> {
    try {
        const quest = await api.getQuest(id);
        
        (document.getElementById('edit-quest-id') as HTMLInputElement).value = quest.id;
        (document.getElementById('edit-quest-title') as HTMLInputElement).value = quest.title || '';
        (document.getElementById('edit-quest-desc') as HTMLTextAreaElement).value = quest.description || '';
        (document.getElementById('edit-quest-difficulty') as HTMLSelectElement).value = quest.difficulty || 'medium';
        (document.getElementById('edit-quest-objectives') as HTMLTextAreaElement).value = (quest.objectives || []).join('\n');
        (document.getElementById('edit-quest-notes') as HTMLTextAreaElement).value = quest.dm_notes || '';
        (document.getElementById('edit-quest-status') as HTMLSelectElement).value = quest.status || 'available';
        
        openModal('edit-quest-modal');
    } catch (error) {
        showToast('Failed to load quest', 'error');
    }
}

async function updateQuest(event: Event): Promise<void> {
    event.preventDefault();
    
    const id = parseInt((document.getElementById('edit-quest-id') as HTMLInputElement).value);
    const objectivesText = (document.getElementById('edit-quest-objectives') as HTMLTextAreaElement).value;
    const objectives = objectivesText.split('\n').filter(o => o.trim());
    
    const data = {
        title: (document.getElementById('edit-quest-title') as HTMLInputElement).value,
        description: (document.getElementById('edit-quest-desc') as HTMLTextAreaElement).value,
        difficulty: (document.getElementById('edit-quest-difficulty') as HTMLSelectElement).value,
        objectives: objectives,
        dm_notes: (document.getElementById('edit-quest-notes') as HTMLTextAreaElement).value,
        status: (document.getElementById('edit-quest-status') as HTMLSelectElement).value
    };
    
    try {
        await api.updateQuest(id, data);
        showToast('Quest updated!', 'success');
        closeModal('edit-quest-modal');
        loadQuests();
    } catch (error) {
        showToast('Failed to update quest', 'error');
    }
}

async function deleteQuest(id: number): Promise<void> {
    if (!confirm('Are you sure you want to delete this quest?')) return;
    
    try {
        await api.deleteQuest(id);
        showToast('Quest deleted', 'success');
        loadQuests();
    } catch (error) {
        showToast('Failed to delete quest', 'error');
    }
}

// ============================================================================
// MODALS
// ============================================================================

function openModal(modalId: string): void {
    document.getElementById(modalId)?.classList.add('active');
}

function closeModal(modalId: string): void {
    document.getElementById(modalId)?.classList.remove('active');
}

// ============================================================================
// TOAST NOTIFICATIONS
// ============================================================================

function showToast(message: string, type: 'success' | 'error' | 'info' = 'info'): void {
    const container = document.getElementById('toast-container')!;
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icon = type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️';
    toast.innerHTML = `<span>${icon}</span><span>${escapeHtml(message)}</span>`;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ============================================================================
// UTILITIES
// ============================================================================

function escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
}

function formatDate(dateStr: string): string {
    if (!dateStr) return 'Unknown';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
    });
}

// ============================================================================
// EDIT FUNCTIONS
// ============================================================================

async function editLocation(id: number): Promise<void> {
    try {
        const loc = await api.getLocation(id);
        
        (document.getElementById('edit-location-id') as HTMLInputElement).value = loc.id;
        (document.getElementById('edit-location-name') as HTMLInputElement).value = loc.name || '';
        (document.getElementById('edit-location-desc') as HTMLTextAreaElement).value = loc.description || '';
        (document.getElementById('edit-location-type') as HTMLSelectElement).value = loc.location_type || 'town';
        (document.getElementById('edit-location-danger') as HTMLInputElement).value = loc.danger_level || 0;
        (document.getElementById('edit-location-weather') as HTMLInputElement).value = loc.current_weather || '';
        (document.getElementById('edit-location-secrets') as HTMLTextAreaElement).value = loc.hidden_secrets || '';
        
        openModal('edit-location-modal');
    } catch (error) {
        showToast('Failed to load location', 'error');
    }
}

async function updateLocation(event: Event): Promise<void> {
    event.preventDefault();
    
    const id = parseInt((document.getElementById('edit-location-id') as HTMLInputElement).value);
    const data = {
        name: (document.getElementById('edit-location-name') as HTMLInputElement).value,
        description: (document.getElementById('edit-location-desc') as HTMLTextAreaElement).value,
        location_type: (document.getElementById('edit-location-type') as HTMLSelectElement).value,
        danger_level: parseInt((document.getElementById('edit-location-danger') as HTMLInputElement).value),
        current_weather: (document.getElementById('edit-location-weather') as HTMLInputElement).value,
        hidden_secrets: (document.getElementById('edit-location-secrets') as HTMLTextAreaElement).value
    };
    
    try {
        await api.updateLocation(id, data);
        showToast('Location updated!', 'success');
        closeModal('edit-location-modal');
        loadLocations();
    } catch (error) {
        showToast('Failed to update location', 'error');
    }
}

async function editNPC(id: number): Promise<void> {
    try {
        const npc = await api.getNPC(id);
        
        (document.getElementById('edit-npc-id') as HTMLInputElement).value = npc.id;
        (document.getElementById('edit-npc-name') as HTMLInputElement).value = npc.name || '';
        (document.getElementById('edit-npc-desc') as HTMLTextAreaElement).value = npc.description || '';
        (document.getElementById('edit-npc-personality') as HTMLTextAreaElement).value = npc.personality || '';
        (document.getElementById('edit-npc-type') as HTMLSelectElement).value = npc.npc_type || 'neutral';
        (document.getElementById('edit-npc-location') as HTMLInputElement).value = npc.location || '';
        (document.getElementById('edit-npc-merchant') as HTMLInputElement).checked = npc.is_merchant || false;
        
        openModal('edit-npc-modal');
    } catch (error) {
        showToast('Failed to load NPC', 'error');
    }
}

async function updateNPC(event: Event): Promise<void> {
    event.preventDefault();
    
    const id = parseInt((document.getElementById('edit-npc-id') as HTMLInputElement).value);
    const data = {
        name: (document.getElementById('edit-npc-name') as HTMLInputElement).value,
        description: (document.getElementById('edit-npc-desc') as HTMLTextAreaElement).value,
        personality: (document.getElementById('edit-npc-personality') as HTMLTextAreaElement).value,
        npc_type: (document.getElementById('edit-npc-type') as HTMLSelectElement).value,
        location: (document.getElementById('edit-npc-location') as HTMLInputElement).value,
        is_merchant: (document.getElementById('edit-npc-merchant') as HTMLInputElement).checked
    };
    
    try {
        await api.updateNPC(id, data);
        showToast('NPC updated!', 'success');
        closeModal('edit-npc-modal');
        loadNPCs();
    } catch (error) {
        showToast('Failed to update NPC', 'error');
    }
}

async function editItem(id: number): Promise<void> {
    try {
        const item = await api.getItem(id);
        
        (document.getElementById('edit-item-id') as HTMLInputElement).value = item.id;
        (document.getElementById('edit-item-name') as HTMLInputElement).value = item.name || '';
        (document.getElementById('edit-item-desc') as HTMLTextAreaElement).value = item.description || '';
        (document.getElementById('edit-item-type') as HTMLSelectElement).value = item.item_type || 'misc';
        (document.getElementById('edit-item-lore') as HTMLTextAreaElement).value = item.lore || '';
        (document.getElementById('edit-item-discovery') as HTMLInputElement).value = item.discovery_conditions || '';
        (document.getElementById('edit-item-notes') as HTMLTextAreaElement).value = item.dm_notes || '';
        
        openModal('edit-item-modal');
    } catch (error) {
        showToast('Failed to load item', 'error');
    }
}

async function updateItem(event: Event): Promise<void> {
    event.preventDefault();
    
    const id = parseInt((document.getElementById('edit-item-id') as HTMLInputElement).value);
    const data = {
        name: (document.getElementById('edit-item-name') as HTMLInputElement).value,
        description: (document.getElementById('edit-item-desc') as HTMLTextAreaElement).value,
        lore: (document.getElementById('edit-item-lore') as HTMLTextAreaElement).value
    };
    
    try {
        await api.updateItem(id, data);
        showToast('Item updated!', 'success');
        closeModal('edit-item-modal');
        loadItems();
    } catch (error) {
        showToast('Failed to update item', 'error');
    }
}

async function deleteItem(id: number): Promise<void> {
    if (!confirm('Are you sure you want to delete this story item?')) return;
    
    try {
        await api.deleteItem(id);
        showToast('Item deleted', 'success');
        loadItems();
    } catch (error) {
        showToast('Failed to delete item', 'error');
    }
}

async function editEvent(id: number): Promise<void> {
    try {
        const event = await api.getEvent(id);
        
        (document.getElementById('edit-event-id') as HTMLInputElement).value = event.id;
        (document.getElementById('edit-event-name') as HTMLInputElement).value = event.name || '';
        (document.getElementById('edit-event-desc') as HTMLTextAreaElement).value = event.description || '';
        (document.getElementById('edit-event-type') as HTMLSelectElement).value = event.event_type || 'side_event';
        (document.getElementById('edit-event-trigger') as HTMLInputElement).value = event.trigger_conditions || '';
        (document.getElementById('edit-event-notes') as HTMLTextAreaElement).value = event.dm_notes || '';
        (document.getElementById('edit-event-status') as HTMLSelectElement).value = event.status || 'pending';
        
        openModal('edit-event-modal');
    } catch (error) {
        showToast('Failed to load event', 'error');
    }
}

async function updateEvent(event: Event): Promise<void> {
    event.preventDefault();
    
    const id = parseInt((document.getElementById('edit-event-id') as HTMLInputElement).value);
    const data = {
        name: (document.getElementById('edit-event-name') as HTMLInputElement).value,
        description: (document.getElementById('edit-event-desc') as HTMLTextAreaElement).value,
        trigger_conditions: (document.getElementById('edit-event-trigger') as HTMLInputElement).value,
        status: (document.getElementById('edit-event-status') as HTMLSelectElement).value
    };
    
    try {
        await api.updateEvent(id, data);
        showToast('Event updated!', 'success');
        closeModal('edit-event-modal');
        loadEvents();
    } catch (error) {
        showToast('Failed to update event', 'error');
    }
}

async function deleteEvent(id: number): Promise<void> {
    if (!confirm('Are you sure you want to delete this event?')) return;
    
    try {
        await api.deleteEvent(id);
        showToast('Event deleted', 'success');
        loadEvents();
    } catch (error) {
        showToast('Failed to delete event', 'error');
    }
}

// ============================================================================
// CLASSES EDITOR
// ============================================================================

let classesData: any = null;
let currentEditingClass: string | null = null;

async function loadClasses(): Promise<void> {
    const container = document.getElementById('classes-list')!;
    container.innerHTML = '<div class="loading-spinner">Loading classes...</div>';

    try {
        const data = await api.getClasses();
        classesData = data;
        const classes = data.classes || {};

        if (Object.keys(classes).length === 0) {
            container.innerHTML = '<div class="empty-state">No classes found. Check your data files.</div>';
            return;
        }

        container.innerHTML = Object.entries(classes).map(([name, cls]: [string, any]) => {
            // Handle abilities as either object (keyed by level) or array
            const abilitiesList = Array.isArray(cls.abilities) 
                ? cls.abilities 
                : Object.values(cls.abilities || {}).flat();
            const primaryStat = cls.primary_ability || cls.primary_stat || 'Unknown';
            
            return `
            <div class="entity-card class-card" data-class="${name}">
                <div class="entity-header">
                    <span class="entity-title">${escapeHtml(cls.name || name)}</span>
                    <span class="entity-badge">${cls.hit_die || 'd8'}</span>
                </div>
                <p class="entity-desc">${escapeHtml(cls.description || 'No description')}</p>
                <div class="entity-meta">
                    <span>⚔️ ${primaryStat}</span>
                    <span>🛡️ ${(cls.saving_throws || []).join(', ') || 'None'}</span>
                </div>
                <div class="abilities-preview">
                    ${abilitiesList.slice(0, 3).map((a: any) => `<span class="ability-tag">${escapeHtml(typeof a === 'string' ? a : a.name || a)}</span>`).join('')}
                    ${abilitiesList.length > 3 ? `<span class="ability-tag">+${abilitiesList.length - 3} more</span>` : ''}
                </div>
                <div class="entity-actions">
                    <button class="btn btn-small btn-secondary" onclick="viewClass('${name}')">View</button>
                    <button class="btn btn-small btn-primary" onclick="editClass('${name}')">Edit</button>
                </div>
            </div>
        `}).join('');
    } catch (error) {
        container.innerHTML = '<div class="empty-state">Failed to load classes. Is the API running?</div>';
        console.error('Load classes error:', error);
    }
}

function viewClass(name: string): void {
    if (!classesData) return;
    const cls = classesData.classes[name];
    if (!cls) return;

    const details = document.getElementById('class-details');
    if (details) {
        // Handle abilities as either object (keyed by level) or array
        const abilities = cls.abilities || {};
        const abilitiesList = Array.isArray(abilities) 
            ? abilities 
            : Object.entries(abilities).flatMap(([level, abs]: [string, any]) => 
                (Array.isArray(abs) ? abs : [abs]).map(a => ({ name: a, level }))
            );
        const primaryStat = cls.primary_ability || cls.primary_stat || 'Unknown';
        
        details.innerHTML = `
            <div class="detail-card">
                <h3>${escapeHtml(cls.name || name)}</h3>
                <p>${escapeHtml(cls.description || 'No description')}</p>
                <div class="detail-section">
                    <h4>Base Stats</h4>
                    <ul>
                        <li><strong>Hit Die:</strong> ${cls.hit_die || 'd8'}</li>
                        <li><strong>Primary Stat:</strong> ${primaryStat}</li>
                        <li><strong>Saving Throws:</strong> ${(cls.saving_throws || []).join(', ')}</li>
                        <li><strong>Starting HP:</strong> ${cls.starting_hp || 'N/A'}</li>
                        <li><strong>HP per Level:</strong> ${cls.hp_per_level || 'N/A'}</li>
                    </ul>
                </div>
                <div class="detail-section">
                    <h4>Starting Equipment</h4>
                    <ul>
                        ${(cls.starting_equipment || []).map((e: string) => `<li>${escapeHtml(e)}</li>`).join('') || '<li>None</li>'}
                    </ul>
                </div>
                <div class="detail-section">
                    <h4>Abilities by Level</h4>
                    <div class="abilities-list">
                        ${abilitiesList.map((a: any) => `
                            <div class="ability-item">
                                <strong>${escapeHtml(typeof a === 'string' ? a : a.name)}</strong>
                                ${a.level ? `<span class="level-badge">Level ${a.level}</span>` : ''}
                            </div>
                        `).join('') || '<div class="empty-state">No abilities defined</div>'}
                    </div>
                </div>
            </div>
        `;
        details.classList.add('active');
    }
}

function editClass(name: string): void {
    currentEditingClass = name;
    if (!classesData) return;
    const cls = classesData.classes[name];
    if (!cls) return;

    const primaryStat = cls.primary_ability || cls.primary_stat || '';

    (document.getElementById('edit-class-name') as HTMLInputElement).value = cls.name || name;
    (document.getElementById('edit-class-desc') as HTMLTextAreaElement).value = cls.description || '';
    (document.getElementById('edit-class-hitdie') as HTMLSelectElement).value = cls.hit_die || 'd8';
    (document.getElementById('edit-class-primary') as HTMLInputElement).value = primaryStat;
    (document.getElementById('edit-class-saves') as HTMLInputElement).value = (cls.saving_throws || []).join(', ');
    (document.getElementById('edit-class-armor') as HTMLInputElement).value = (cls.armor_proficiencies || []).join(', ');
    (document.getElementById('edit-class-weapons') as HTMLInputElement).value = (cls.weapon_proficiencies || []).join(', ');
    
    // Abilities as JSON for now
    (document.getElementById('edit-class-abilities') as HTMLTextAreaElement).value = JSON.stringify(cls.abilities || {}, null, 2);

    openModal('edit-class-modal');
}

async function updateClass(event: Event): Promise<void> {
    event.preventDefault();
    if (!currentEditingClass || !classesData) return;

    try {
        const abilities = JSON.parse((document.getElementById('edit-class-abilities') as HTMLTextAreaElement).value || '{}');
        const primaryStatValue = (document.getElementById('edit-class-primary') as HTMLInputElement).value;
        
        classesData.classes[currentEditingClass] = {
            ...classesData.classes[currentEditingClass],
            name: (document.getElementById('edit-class-name') as HTMLInputElement).value,
            description: (document.getElementById('edit-class-desc') as HTMLTextAreaElement).value,
            hit_die: (document.getElementById('edit-class-hitdie') as HTMLSelectElement).value,
            primary_stat: primaryStatValue,
            saving_throws: (document.getElementById('edit-class-saves') as HTMLInputElement).value.split(',').map(s => s.trim()).filter(s => s),
            armor_proficiencies: (document.getElementById('edit-class-armor') as HTMLInputElement).value.split(',').map(s => s.trim()).filter(s => s),
            weapon_proficiencies: (document.getElementById('edit-class-weapons') as HTMLInputElement).value.split(',').map(s => s.trim()).filter(s => s),
            abilities: abilities
        };

        await api.updateClasses(classesData);
        showToast('Class updated!', 'success');
        closeModal('edit-class-modal');
        loadClasses();
    } catch (error) {
        showToast('Failed to update class: ' + (error as Error).message, 'error');
    }
}

// ============================================================================
// RACES EDITOR
// ============================================================================

let racesData: any = null;
let currentEditingRace: string | null = null;

async function loadRaces(): Promise<void> {
    const container = document.getElementById('races-list')!;
    container.innerHTML = '<div class="loading-spinner">Loading races...</div>';

    try {
        const data = await api.getRaces();
        racesData = data;
        const races = data.races || {};

        if (Object.keys(races).length === 0) {
            container.innerHTML = '<div class="empty-state">No races found. Check your data files.</div>';
            return;
        }

        container.innerHTML = Object.entries(races).map(([name, race]: [string, any]) => `
            <div class="entity-card race-card" data-race="${name}">
                <div class="entity-header">
                    <span class="entity-title">${escapeHtml(name)}</span>
                    <span class="entity-badge">${race.size || 'Medium'}</span>
                </div>
                <p class="entity-desc">${escapeHtml(race.description || 'No description')}</p>
                <div class="entity-meta">
                    <span>🏃 Speed: ${race.speed || 30}ft</span>
                    <span>📊 ${Object.entries(race.ability_bonuses || {}).map(([k, v]) => `${k}+${v}`).join(', ') || 'No bonuses'}</span>
                </div>
                <div class="traits-preview">
                    ${(race.traits || []).slice(0, 3).map((t: any) => `<span class="trait-tag">${escapeHtml(typeof t === 'string' ? t : t.name)}</span>`).join('')}
                    ${(race.traits || []).length > 3 ? `<span class="trait-tag">+${(race.traits || []).length - 3} more</span>` : ''}
                </div>
                <div class="entity-actions">
                    <button class="btn btn-small btn-secondary" onclick="viewRace('${name}')">View</button>
                    <button class="btn btn-small btn-primary" onclick="editRace('${name}')">Edit</button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        container.innerHTML = '<div class="empty-state">Failed to load races. Is the API running?</div>';
        console.error('Load races error:', error);
    }
}

function viewRace(name: string): void {
    if (!racesData) return;
    const race = racesData.races[name];
    if (!race) return;

    const details = document.getElementById('race-details');
    if (details) {
        details.innerHTML = `
            <div class="detail-card">
                <h3>${escapeHtml(name)}</h3>
                <p>${escapeHtml(race.description || 'No description')}</p>
                <div class="detail-section">
                    <h4>Base Stats</h4>
                    <ul>
                        <li><strong>Size:</strong> ${race.size || 'Medium'}</li>
                        <li><strong>Speed:</strong> ${race.speed || 30}ft</li>
                        <li><strong>Ability Bonuses:</strong> ${Object.entries(race.ability_bonuses || {}).map(([k, v]) => `${k}+${v}`).join(', ') || 'None'}</li>
                        <li><strong>Languages:</strong> ${(race.languages || []).join(', ')}</li>
                    </ul>
                </div>
                <div class="detail-section">
                    <h4>Traits (${(race.traits || []).length})</h4>
                    <div class="traits-list">
                        ${(race.traits || []).map((t: any) => `
                            <div class="trait-item">
                                <strong>${escapeHtml(typeof t === 'string' ? t : t.name)}</strong>
                                ${typeof t === 'object' ? `<p>${escapeHtml(t.description || '')}</p>` : ''}
                            </div>
                        `).join('')}
                    </div>
                </div>
                ${(race.subraces && Object.keys(race.subraces).length > 0) ? `
                    <div class="detail-section">
                        <h4>Subraces</h4>
                        <div class="subraces-list">
                            ${Object.entries(race.subraces || {}).map(([sname, sub]: [string, any]) => `
                                <div class="subrace-item">
                                    <strong>${escapeHtml(sname)}</strong>
                                    <p>${escapeHtml(sub.description || '')}</p>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                ` : ''}
            </div>
        `;
        details.classList.add('active');
    }
}

function editRace(name: string): void {
    currentEditingRace = name;
    if (!racesData) return;
    const race = racesData.races[name];
    if (!race) return;

    (document.getElementById('edit-race-name') as HTMLInputElement).value = name;
    (document.getElementById('edit-race-desc') as HTMLTextAreaElement).value = race.description || '';
    (document.getElementById('edit-race-size') as HTMLSelectElement).value = race.size || 'Medium';
    (document.getElementById('edit-race-speed') as HTMLInputElement).value = race.speed || '30';
    (document.getElementById('edit-race-bonuses') as HTMLInputElement).value = Object.entries(race.ability_bonuses || {}).map(([k, v]) => `${k}:${v}`).join(', ');
    (document.getElementById('edit-race-languages') as HTMLInputElement).value = (race.languages || []).join(', ');
    
    // Traits as JSON for now
    (document.getElementById('edit-race-traits') as HTMLTextAreaElement).value = JSON.stringify(race.traits || [], null, 2);

    openModal('edit-race-modal');
}

async function updateRace(event: Event): Promise<void> {
    event.preventDefault();
    if (!currentEditingRace || !racesData) return;

    try {
        const traits = JSON.parse((document.getElementById('edit-race-traits') as HTMLTextAreaElement).value || '[]');
        const bonusesStr = (document.getElementById('edit-race-bonuses') as HTMLInputElement).value;
        const ability_bonuses: {[key: string]: number} = {};
        bonusesStr.split(',').forEach(b => {
            const [key, val] = b.split(':').map(s => s.trim());
            if (key && val) ability_bonuses[key] = parseInt(val);
        });
        
        racesData.races[currentEditingRace] = {
            ...racesData.races[currentEditingRace],
            description: (document.getElementById('edit-race-desc') as HTMLTextAreaElement).value,
            size: (document.getElementById('edit-race-size') as HTMLSelectElement).value,
            speed: parseInt((document.getElementById('edit-race-speed') as HTMLInputElement).value) || 30,
            ability_bonuses: ability_bonuses,
            languages: (document.getElementById('edit-race-languages') as HTMLInputElement).value.split(',').map(s => s.trim()).filter(s => s),
            traits: traits
        };

        await api.updateRaces(racesData);
        showToast('Race updated!', 'success');
        closeModal('edit-race-modal');
        loadRaces();
    } catch (error) {
        showToast('Failed to update race: ' + (error as Error).message, 'error');
    }
}

// ============================================================================
// SKILL TREES
// ============================================================================

let skillTreesData: any = null;
let currentSkillTreeClass: string | null = null;

async function loadSkillTrees(): Promise<void> {
    const classSelect = document.getElementById('skill-tree-class-select') as HTMLSelectElement;
    const container = document.getElementById('skill-tree-container')!;

    try {
        const data = await api.getAllSkills();
        skillTreesData = data;
        const skillTrees = data.skill_trees || {};
        const classes = Object.keys(skillTrees);

        // Populate class dropdown
        classSelect.innerHTML = '<option value="">Select a class...</option>' + 
            classes.map(c => `<option value="${c}">${skillTrees[c]?.name || c}</option>`).join('');

        container.innerHTML = '<div class="empty-state">Select a class to view its skill tree.</div>';
    } catch (error) {
        container.innerHTML = '<div class="empty-state">Failed to load skill trees. Is the API running?</div>';
        console.error('Load skill trees error:', error);
    }
}

async function selectSkillTreeClass(className: string): Promise<void> {
    currentSkillTreeClass = className;
    const container = document.getElementById('skill-tree-container')!;

    if (!className) {
        container.innerHTML = '<div class="empty-state">Select a class to view its skill tree.</div>';
        return;
    }

    try {
        const data = await api.getClassSkills(className);
        const skillTree = data.skill_tree || {};
        const branches = skillTree.branches || {};

        // Store for showSkillBranch
        if (!skillTreesData) skillTreesData = { skill_trees: {} };
        skillTreesData.skill_trees[className] = skillTree;

        // Create branch navigation and display
        const branchNames = Object.keys(branches);
        
        if (branchNames.length === 0) {
            container.innerHTML = '<div class="empty-state">No skill branches found for this class.</div>';
            return;
        }
        
        container.innerHTML = `
            <div class="branch-nav" id="branch-nav">
                ${branchNames.map((branch, idx) => 
                    `<button class="branch-btn ${idx === 0 ? 'active' : ''}" onclick="showSkillBranch('${branch}')">${escapeHtml(branches[branch]?.name || branch)}</button>`
                ).join('')}
            </div>
            <div id="branch-content"></div>
        `;

        // Show first branch by default
        showSkillBranch(branchNames[0]);
    } catch (error) {
        container.innerHTML = '<div class="empty-state">Failed to load class skills.</div>';
        console.error('Load class skills error:', error);
    }
}

// Called from HTML onchange
function loadSkillTree(): void {
    const select = document.getElementById('skill-tree-class-select') as HTMLSelectElement;
    selectSkillTreeClass(select.value);
}

function showSkillBranch(branchName: string): void {
    if (!skillTreesData || !currentSkillTreeClass) return;
    
    const container = document.getElementById('branch-content')!;
    const classTree = skillTreesData.skill_trees[currentSkillTreeClass];
    if (!classTree || !classTree.branches || !classTree.branches[branchName]) return;

    const branch = classTree.branches[branchName];
    const skillIds = branch.skills || [];

    // Update active branch button
    document.querySelectorAll('.branch-btn').forEach(btn => {
        btn.classList.toggle('active', btn.textContent === (branch.name || branchName));
    });

    container.innerHTML = `
        <div class="skill-tree-container">
            <h3>${escapeHtml(branch.name || branchName)} Branch</h3>
            <p class="branch-desc">${escapeHtml(branch.description || '')}</p>
            <div class="skills-grid">
                ${skillIds.map((skillId: string, idx: number) => `
                    <div class="skill-node tier-${Math.floor(idx / 3)}" data-skill="${skillId}">
                        <div class="skill-icon">⭐</div>
                        <div class="skill-name">${escapeHtml(skillId.replace(/_/g, ' '))}</div>
                        <div class="skill-level">Tier ${Math.floor(idx / 3) + 1}</div>
                    </div>
                `).join('')}
            </div>
            <div class="branch-actions">
                <button class="btn btn-secondary" onclick="editSkillBranch('${branchName}')">✏️ Edit Branch</button>
            </div>
        </div>
    `;
}

let currentEditingBranch: string | null = null;

function editSkillBranch(branchName: string): void {
    if (!skillTreesData || !currentSkillTreeClass) return;
    
    const classTree = skillTreesData.skill_trees[currentSkillTreeClass];
    if (!classTree || !classTree.branches || !classTree.branches[branchName]) return;
    
    currentEditingBranch = branchName;
    const branch = classTree.branches[branchName];
    
    // Open a modal or inline editor
    const content = document.getElementById('branch-content')!;
    content.innerHTML = `
        <div class="skill-branch-editor">
            <h3>Editing: ${escapeHtml(branch.name || branchName)} Branch</h3>
            <form id="branch-edit-form" onsubmit="saveSkillBranch(event)">
                <div class="form-group">
                    <label for="branch-name">Branch Name</label>
                    <input type="text" id="branch-name" value="${escapeHtml(branch.name || branchName)}" required>
                </div>
                <div class="form-group">
                    <label for="branch-description">Description</label>
                    <textarea id="branch-description" rows="2">${escapeHtml(branch.description || '')}</textarea>
                </div>
                <div class="form-group">
                    <label for="branch-skills">Skills (one per line, use skill_id format)</label>
                    <textarea id="branch-skills" rows="8">${(branch.skills || []).join('\n')}</textarea>
                </div>
                <div class="form-actions">
                    <button type="button" class="btn btn-secondary" onclick="selectSkillTreeClass('${currentSkillTreeClass}')">Cancel</button>
                    <button type="submit" class="btn btn-primary">Save Changes</button>
                </div>
            </form>
        </div>
    `;
}

async function saveSkillBranch(event: Event): Promise<void> {
    event.preventDefault();
    if (!skillTreesData || !currentSkillTreeClass || !currentEditingBranch) return;
    
    const branchName = (document.getElementById('branch-name') as HTMLInputElement).value;
    const description = (document.getElementById('branch-description') as HTMLTextAreaElement).value;
    const skillsText = (document.getElementById('branch-skills') as HTMLTextAreaElement).value;
    const skills = skillsText.split('\n').map(s => s.trim()).filter(s => s);
    
    try {
        // Update the branch in the skill tree
        skillTreesData.skill_trees[currentSkillTreeClass].branches[currentEditingBranch] = {
            name: branchName,
            description: description,
            skills: skills
        };
        
        // Save to API
        await api.updateClassSkills(currentSkillTreeClass, {
            skill_tree: skillTreesData.skill_trees[currentSkillTreeClass]
        });
        
        showToast('Skill branch updated!', 'success');
        currentEditingBranch = null;
        await selectSkillTreeClass(currentSkillTreeClass);
    } catch (error) {
        showToast('Failed to save skill branch: ' + (error as Error).message, 'error');
    }
}

// ============================================================================
// ITEM DATABASE
// ============================================================================

let gameItemsData: any = null;

async function loadItemDb(): Promise<void> {
    const container = document.getElementById('itemdb-list')!;
    container.innerHTML = '<div class="loading-spinner">Loading items...</div>';

    try {
        const data = await api.getGameItems();
        gameItemsData = data;
        displayGameItems(data.items || {});
    } catch (error) {
        container.innerHTML = '<div class="empty-state">Failed to load game items. Is the API running?</div>';
        console.error('Load game items error:', error);
    }
}

function displayGameItems(items: any): void {
    const container = document.getElementById('itemdb-list')!;
    
    // Flatten items from categories
    let allItems: any[] = [];
    Object.entries(items).forEach(([category, categoryItems]: [string, any]) => {
        if (Array.isArray(categoryItems)) {
            categoryItems.forEach((item: any) => {
                allItems.push({ ...item, category });
            });
        }
    });

    if (allItems.length === 0) {
        container.innerHTML = '<div class="empty-state">No items found.</div>';
        return;
    }

    container.innerHTML = allItems.map((item: any) => `
        <div class="entity-card item-card rarity-${item.rarity || 'common'}" data-item="${item.id || item.name}">
            <div class="entity-header">
                <span class="entity-title">${escapeHtml(item.name)}</span>
                <span class="entity-badge rarity-${item.rarity || 'common'}">${item.rarity || 'common'}</span>
            </div>
            <p class="entity-desc">${escapeHtml(item.description || 'No description')}</p>
            <div class="entity-meta">
                <span>📦 ${item.category}</span>
                ${item.damage ? `<span>⚔️ ${item.damage}</span>` : ''}
                ${item.armor ? `<span>🛡️ AC ${item.armor}</span>` : ''}
                ${item.value ? `<span>💰 ${item.value}g</span>` : ''}
            </div>
            ${item.effects && item.effects.length > 0 ? `
                <div class="effects-preview">
                    ${item.effects.slice(0, 2).map((e: any) => `<span class="effect-tag">${escapeHtml(typeof e === 'string' ? e : e.type)}</span>`).join('')}
                </div>
            ` : ''}
        </div>
    `).join('');
}

function filterGameItems(): void {
    const category = (document.getElementById('item-category-select') as HTMLSelectElement).value;
    const rarity = (document.getElementById('item-rarity-select') as HTMLSelectElement).value;
    const searchTerm = (document.getElementById('item-search') as HTMLInputElement)?.value?.toLowerCase() || '';

    if (!gameItemsData) return;

    let items = gameItemsData.items || {};
    
    // If filtering by category (not "all"), only show that category
    if (category && category !== 'all') {
        items = { [category]: items[category] || [] };
    }

    // Apply rarity filter
    if (rarity && rarity !== 'all') {
        const filtered: any = {};
        Object.entries(items).forEach(([cat, catItems]: [string, any]) => {
            if (Array.isArray(catItems)) {
                const rarityFiltered = catItems.filter((item: any) => item.rarity === rarity);
                if (rarityFiltered.length > 0) {
                    filtered[cat] = rarityFiltered;
                }
            }
        });
        items = filtered;
    }

    // Apply search filter
    if (searchTerm) {
        const filtered: any = {};
        Object.entries(items).forEach(([cat, catItems]: [string, any]) => {
            if (Array.isArray(catItems)) {
                const searchFiltered = catItems.filter((item: any) => 
                    item.name?.toLowerCase().includes(searchTerm) ||
                    item.description?.toLowerCase().includes(searchTerm)
                );
                if (searchFiltered.length > 0) {
                    filtered[cat] = searchFiltered;
                }
            }
        });
        items = filtered;
    }

    displayGameItems(items);
}

// Alias functions for HTML compatibility
function loadItemCategory(): void {
    filterGameItems();
}

function filterItems(): void {
    filterGameItems();
}

// ============================================================================
// SPELLBOOK
// ============================================================================

let spellbookData: any = null;

async function loadSpellbook(): Promise<void> {
    const container = document.getElementById('spellbook-list')!;
    container.innerHTML = '<div class="loading-spinner">Loading spells...</div>';

    try {
        const data = await api.getGameSpells();
        spellbookData = data;
        // Convert spell object to array
        const spells = data.spells || {};
        const spellsArray = Object.entries(spells).map(([id, spell]: [string, any]) => ({ ...spell, id }));
        displaySpells(spellsArray);
    } catch (error) {
        container.innerHTML = '<div class="empty-state">Failed to load spells. Is the API running?</div>';
        console.error('Load spells error:', error);
    }
}

function displaySpells(spells: any[]): void {
    const container = document.getElementById('spellbook-list')!;

    if (spells.length === 0) {
        container.innerHTML = '<div class="empty-state">No spells found.</div>';
        return;
    }

    container.innerHTML = spells.map((spell: any) => `
        <div class="entity-card spell-card school-${(spell.school || 'evocation').toLowerCase()}" data-spell="${spell.id || spell.name}">
            <div class="entity-header">
                <span class="entity-title">${escapeHtml(spell.name)}</span>
                <span class="entity-badge school-${(spell.school || 'evocation').toLowerCase()}">${spell.school || 'Unknown'}</span>
            </div>
            <div class="spell-level">Level ${spell.level ?? 0} ${spell.level === 0 ? '(Cantrip)' : ''}</div>
            <p class="entity-desc">${escapeHtml(spell.description || 'No description')}</p>
            <div class="entity-meta">
                <span>⏱️ ${spell.casting_time || '1 action'}</span>
                <span>📏 ${spell.range || 'Self'}</span>
                <span>⏳ ${spell.duration || 'Instant'}</span>
            </div>
            <div class="spell-components">
                ${spell.components?.verbal ? '<span class="component">V</span>' : ''}
                ${spell.components?.somatic ? '<span class="component">S</span>' : ''}
                ${spell.components?.material ? `<span class="component" title="${escapeHtml(spell.components.material)}">M</span>` : ''}
            </div>
            ${spell.classes && spell.classes.length > 0 ? `
                <div class="spell-classes">
                    ${spell.classes.map((c: string) => `<span class="class-tag">${escapeHtml(c)}</span>`).join('')}
                </div>
            ` : ''}
        </div>
    `).join('');
}

function filterSpellbook(): void {
    const school = (document.getElementById('spell-school-select') as HTMLSelectElement)?.value || '';
    const level = (document.getElementById('spell-level-select') as HTMLSelectElement)?.value || '';
    const searchTerm = (document.getElementById('spell-search') as HTMLInputElement)?.value?.toLowerCase() || '';
    const spellClass = (document.getElementById('spell-class-select') as HTMLSelectElement)?.value || '';

    if (!spellbookData) return;

    // Convert spell object to array
    const spells = spellbookData.spells || {};
    let spellsArray = Object.entries(spells).map(([id, spell]: [string, any]) => ({ ...spell, id }));

    // Filter by school
    if (school && school !== 'all') {
        spellsArray = spellsArray.filter((s: any) => s.school?.toLowerCase() === school.toLowerCase());
    }

    // Filter by level
    if (level && level !== 'all') {
        spellsArray = spellsArray.filter((s: any) => s.level === parseInt(level));
    }

    // Filter by class
    if (spellClass && spellClass !== 'all') {
        spellsArray = spellsArray.filter((s: any) => s.classes?.includes(spellClass));
    }

    // Filter by search term
    if (searchTerm) {
        spellsArray = spellsArray.filter((s: any) => 
            s.name?.toLowerCase().includes(searchTerm) ||
            s.description?.toLowerCase().includes(searchTerm)
        );
    }

    displaySpells(spellsArray);
}

// Alias for HTML compatibility
function filterSpells(): void {
    filterSpellbook();
}

// ============================================================================
// CAMPAIGN CREATOR
// ============================================================================

interface CampaignConfig {
    name: string;
    description: string;
    guild_id: string;
    dm_user_id: string;
    genre: string;
    setting_tone: string;
    npc_count: number;
    location_count: number;
    starting_quest_count: number;
    faction_count: number;
    world_theme: string;
    world_scale: string;
    magic_level: string;
    tech_level: string;
    world_description: string;
    key_events: string;
    special_rules: string;
}

let currentCampaignStep = 1;
let generatedCampaignData: any = null;
let selectedTemplate: string = 'custom';

async function loadCampaignCreator(): Promise<void> {
    // Reset to step 1
    currentCampaignStep = 1;
    generatedCampaignData = null;
    selectedTemplate = 'custom';

    // Setup template click handlers
    setupTemplateSelection();

    // Show step 1
    goToStep(1);

    console.log('Campaign creator loaded');
}

function setupTemplateSelection(): void {
    const templateCards = document.querySelectorAll('.template-card');
    templateCards.forEach(card => {
        card.addEventListener('click', () => {
            // Remove active from all
            templateCards.forEach(c => c.classList.remove('active'));
            // Add active to clicked
            card.classList.add('active');
            selectedTemplate = card.getAttribute('data-template') || 'custom';
            // Apply template defaults
            applyTemplate(selectedTemplate);
        });
    });
}

function applyTemplate(templateId: string): void {
    const templates: Record<string, any> = {
        'classic_fantasy': {
            theme: 'fantasy',
            scale: 'regional',
            magic: 'high',
            tech: 'medieval',
            tone: 'heroic'
        },
        'dark_fantasy': {
            theme: 'fantasy',
            scale: 'regional',
            magic: 'medium',
            tech: 'medieval',
            tone: 'gritty'
        },
        'steampunk_adventure': {
            theme: 'steampunk',
            scale: 'local',
            magic: 'low',
            tech: 'industrial',
            tone: 'mystery'
        },
        'cosmic_horror': {
            theme: 'horror',
            scale: 'local',
            magic: 'low',
            tech: 'modern',
            tone: 'horror'
        },
        'space_opera': {
            theme: 'sci-fi',
            scale: 'world',
            magic: 'none',
            tech: 'futuristic',
            tone: 'heroic'
        },
        'custom': {} // No defaults for custom
    };

    const template = templates[templateId];
    if (template && Object.keys(template).length > 0) {
        setSelectValue('world-theme', template.theme);
        setSelectValue('world-scale', template.scale);
        setSelectValue('magic-level', template.magic);
        setSelectValue('tech-level', template.tech);
        setSelectValue('campaign-tone', template.tone);
    }
}

function setSelectValue(id: string, value: string): void {
    const select = document.getElementById(id) as HTMLSelectElement;
    if (select) {
        select.value = value;
    }
}

function goToStep(step: number): void {
    // Update wizard step indicators
    document.querySelectorAll('.wizard-step').forEach((el, index) => {
        el.classList.remove('active', 'completed');
        if (index + 1 < step) {
            el.classList.add('completed');
        } else if (index + 1 === step) {
            el.classList.add('active');
        }
    });

    // Show/hide step content
    document.querySelectorAll('.campaign-step').forEach((el, index) => {
        el.classList.remove('active');
        if (index + 1 === step) {
            el.classList.add('active');
        }
    });

    currentCampaignStep = step;
}

function getCampaignFormData(): CampaignConfig {
    return {
        name: (document.getElementById('campaign-name') as HTMLInputElement)?.value || 'New Campaign',
        description: (document.getElementById('world-description') as HTMLTextAreaElement)?.value || '',
        guild_id: (document.getElementById('campaign-guild-id') as HTMLInputElement)?.value || '',
        dm_user_id: (document.getElementById('campaign-dm-id') as HTMLInputElement)?.value || '',
        genre: selectedTemplate !== 'custom' ? selectedTemplate : (document.getElementById('world-theme') as HTMLSelectElement)?.value || 'fantasy',
        setting_tone: (document.getElementById('campaign-tone') as HTMLSelectElement)?.value || 'heroic',
        npc_count: parseInt((document.getElementById('num-npcs') as HTMLInputElement)?.value) || 8,
        location_count: parseInt((document.getElementById('num-locations') as HTMLInputElement)?.value) || 5,
        starting_quest_count: parseInt((document.getElementById('num-quests') as HTMLInputElement)?.value) || 3,
        faction_count: parseInt((document.getElementById('num-factions') as HTMLInputElement)?.value) || 3,
        world_theme: (document.getElementById('world-theme') as HTMLSelectElement)?.value || 'fantasy',
        world_scale: (document.getElementById('world-scale') as HTMLSelectElement)?.value || 'regional',
        magic_level: (document.getElementById('magic-level') as HTMLSelectElement)?.value || 'high',
        tech_level: (document.getElementById('tech-level') as HTMLSelectElement)?.value || 'medieval',
        world_description: (document.getElementById('world-description') as HTMLTextAreaElement)?.value || '',
        key_events: (document.getElementById('key-events') as HTMLTextAreaElement)?.value || '',
        special_rules: (document.getElementById('special-rules') as HTMLTextAreaElement)?.value || ''
    };
}

async function generateCampaignPreview(): Promise<void> {
    console.log('generateCampaignPreview called');
    const config = getCampaignFormData();
    console.log('Form config:', config);

    // Validate required fields
    if (!config.name.trim()) {
        showToast('Please enter a campaign name', 'error');
        console.log('Validation failed: missing name');
        return;
    }
    if (!config.guild_id.trim()) {
        showToast('Please enter a Discord Guild ID', 'error');
        console.log('Validation failed: missing guild_id');
        return;
    }
    if (!config.dm_user_id.trim()) {
        showToast('Please enter your Discord User ID', 'error');
        console.log('Validation failed: missing dm_user_id');
        return;
    }

    // Move to step 2 (loading state)
    goToStep(2);

    const statusElement = document.getElementById('generation-status');
    const progressBar = document.getElementById('generation-progress');

    try {
        // Animate progress while generating
        const animateProgress = async () => {
            const steps = [
                { label: 'Creating world setting...', progress: 15 },
                { label: 'Generating locations...', progress: 35 },
                { label: 'Creating NPCs...', progress: 55 },
                { label: 'Building factions...', progress: 75 },
                { label: 'Writing quest hooks...', progress: 90 },
            ];

            for (const step of steps) {
                updateGenerationStatus(statusElement, progressBar, step);
                await new Promise(resolve => setTimeout(resolve, 600));
            }
        };

        // Start progress animation
        const progressPromise = animateProgress();

        // Build settings for API
        const apiSettings = {
            guild_id: parseInt(config.guild_id) || 0,
            dm_user_id: parseInt(config.dm_user_id) || 0,
            name: config.name,
            world_theme: config.world_theme,
            world_scale: config.world_scale,
            magic_level: config.magic_level,
            technology_level: config.tech_level,
            tone: config.setting_tone,
            num_locations: config.location_count,
            num_npcs: config.npc_count,
            num_factions: config.faction_count,
            num_quest_hooks: config.starting_quest_count,
            world_description: config.world_description || null,
            key_events: config.key_events || null,
            special_rules: config.special_rules || null
        };

        // Call the API
        const result = await api.generateCampaignPreview(apiSettings);

        // Wait for progress animation to complete
        await progressPromise;

        // Final progress update
        updateGenerationStatus(statusElement, progressBar, { label: 'Finalizing...', progress: 100 });
        await new Promise(resolve => setTimeout(resolve, 300));

        // Convert API response to our format
        const preview = result.preview;
        const results = {
            config,
            apiSettings,
            world: preview.world_setting,
            locations: preview.locations || [],
            npcs: preview.npcs || [],
            factions: preview.factions || [],
            quests: preview.quest_hooks || [],
            scenario: { description: preview.starting_scenario || 'Your adventure begins...' }
        };

        // Store results and move to step 3
        generatedCampaignData = results;
        populatePreview(results);
        goToStep(3);

        showToast('Campaign preview generated!', 'success');

    } catch (error) {
        console.error('Campaign generation error:', error);
        showToast('Failed to generate campaign. Check API connection.', 'error');
        goToStep(1);
    }
}

function updateGenerationStatus(statusEl: HTMLElement | null, progressBar: HTMLElement | null, step: { label: string; progress: number }): void {
    if (statusEl) statusEl.textContent = step.label;
    if (progressBar) progressBar.style.width = `${step.progress}%`;
}

function populatePreview(data: any): void {
    // World setting
    const worldPreview = document.getElementById('preview-world');
    if (worldPreview) {
        worldPreview.innerHTML = `<p>${escapeHtml(data.world?.description || 'A world of adventure awaits...')}</p>`;
    }

    // Locations
    const locationsPreview = document.getElementById('preview-locations');
    const locationCount = document.getElementById('location-count');
    if (locationsPreview) {
        locationsPreview.innerHTML = data.locations.map((loc: any, index: number) => `
            <div class="preview-card" data-type="location" data-index="${index}">
                <div class="preview-card-header">
                    <h4>${escapeHtml(loc.name)}</h4>
                    <div class="preview-card-actions">
                        <button class="btn btn-icon" onclick="editPreviewItem('location', ${index})">✏️</button>
                        <button class="btn btn-icon btn-danger" onclick="removePreviewItem('location', ${index})">🗑️</button>
                    </div>
                </div>
                <p>${escapeHtml(loc.description || '')}</p>
                ${loc.type ? `<span class="tag">${escapeHtml(loc.type)}</span>` : ''}
            </div>
        `).join('') || '<p class="empty-state">No locations generated</p>';
    }
    if (locationCount) locationCount.textContent = String(data.locations.length);

    // NPCs
    const npcsPreview = document.getElementById('preview-npcs');
    const npcCount = document.getElementById('npc-count');
    if (npcsPreview) {
        npcsPreview.innerHTML = data.npcs.map((npc: any, index: number) => `
            <div class="preview-card" data-type="npc" data-index="${index}">
                <div class="preview-card-header">
                    <h4>${escapeHtml(npc.name)}</h4>
                    <div class="preview-card-actions">
                        <button class="btn btn-icon" onclick="editPreviewItem('npc', ${index})">✏️</button>
                        <button class="btn btn-icon btn-danger" onclick="removePreviewItem('npc', ${index})">🗑️</button>
                    </div>
                </div>
                <p class="npc-role">${escapeHtml(npc.role || npc.occupation || '')}</p>
                <p>${escapeHtml(npc.description || '')}</p>
            </div>
        `).join('') || '<p class="empty-state">No NPCs generated</p>';
    }
    if (npcCount) npcCount.textContent = String(data.npcs.length);

    // Factions
    const factionsPreview = document.getElementById('preview-factions');
    const factionCount = document.getElementById('faction-count');
    if (factionsPreview) {
        factionsPreview.innerHTML = data.factions.map((faction: any, index: number) => `
            <div class="preview-card" data-type="faction" data-index="${index}">
                <div class="preview-card-header">
                    <h4>${escapeHtml(faction.name)}</h4>
                    <div class="preview-card-actions">
                        <button class="btn btn-icon" onclick="editPreviewItem('faction', ${index})">✏️</button>
                        <button class="btn btn-icon btn-danger" onclick="removePreviewItem('faction', ${index})">🗑️</button>
                    </div>
                </div>
                <p>${escapeHtml(faction.description || '')}</p>
            </div>
        `).join('') || '<p class="empty-state">No factions generated</p>';
    }
    if (factionCount) factionCount.textContent = String(data.factions.length);

    // Quests
    const questsPreview = document.getElementById('preview-quests');
    const questCount = document.getElementById('quest-count');
    if (questsPreview) {
        questsPreview.innerHTML = data.quests.map((quest: any, index: number) => `
            <div class="preview-card" data-type="quest" data-index="${index}">
                <div class="preview-card-header">
                    <h4>${escapeHtml(quest.name || quest.title)}</h4>
                    <div class="preview-card-actions">
                        <button class="btn btn-icon" onclick="editPreviewItem('quest', ${index})">✏️</button>
                        <button class="btn btn-icon btn-danger" onclick="removePreviewItem('quest', ${index})">🗑️</button>
                    </div>
                </div>
                <p>${escapeHtml(quest.description || '')}</p>
            </div>
        `).join('') || '<p class="empty-state">No quests generated</p>';
    }
    if (questCount) questCount.textContent = String(data.quests.length);

    // Starting scenario
    const scenarioPreview = document.getElementById('preview-scenario');
    if (scenarioPreview) {
        scenarioPreview.innerHTML = `<p>${escapeHtml(data.scenario?.description || 'Your adventure begins...')}</p>`;
    }
}

function editPreviewItem(type: string, index: number): void {
    // TODO: Open edit modal for the item
    showToast(`Edit ${type} ${index + 1} - coming soon!`, 'info');
}

function removePreviewItem(type: string, index: number): void {
    if (!generatedCampaignData) return;

    const typeKey = type + 's'; // locations, npcs, factions, quests
    if (generatedCampaignData[typeKey]) {
        generatedCampaignData[typeKey].splice(index, 1);
        populatePreview(generatedCampaignData);
        showToast(`${type} removed`, 'info');
    }
}

function addItem(type: string): void {
    // TODO: Open add modal for the item type
    showToast(`Add ${type} - coming soon!`, 'info');
}

function editSection(section: string): void {
    // TODO: Open edit modal for the section
    showToast(`Edit ${section} - coming soon!`, 'info');
}

async function finalizeCampaign(): Promise<void> {
    if (!generatedCampaignData) {
        showToast('No campaign data to create', 'error');
        return;
    }

    const config = generatedCampaignData.config;
    const apiSettings = generatedCampaignData.apiSettings;

    try {
        // Build the finalization data
        const finalizeData = {
            guild_id: apiSettings.guild_id,
            dm_user_id: apiSettings.dm_user_id,
            name: config.name,
            description: config.description || generatedCampaignData.scenario?.description || '',
            world_setting: generatedCampaignData.world || {},
            locations: generatedCampaignData.locations || [],
            npcs: generatedCampaignData.npcs || [],
            factions: generatedCampaignData.factions || [],
            quest_hooks: generatedCampaignData.quests || [],
            starting_scenario: generatedCampaignData.scenario?.description || 'Your adventure begins...'
        };

        // Call the finalize endpoint
        const response = await api.finalizeCampaign(finalizeData);

        // Move to success step
        goToStep(4);

        // Update success message
        const successMessage = document.getElementById('success-message');
        if (successMessage) {
            successMessage.textContent = response.message || `"${config.name}" has been created and is ready to play!`;
        }

        // Update success stats
        const successStats = document.getElementById('success-stats');
        if (successStats) {
            const stats = response.stats || {};
            successStats.innerHTML = `
                <div class="stat-item">
                    <span class="stat-value">${stats.locations || generatedCampaignData.locations.length}</span>
                    <span class="stat-label">Locations</span>
                </div>
                <div class="stat-item">
                    <span class="stat-value">${stats.npcs || generatedCampaignData.npcs.length}</span>
                    <span class="stat-label">NPCs</span>
                </div>
                <div class="stat-item">
                    <span class="stat-value">${stats.factions || generatedCampaignData.factions.length}</span>
                    <span class="stat-label">Factions</span>
                </div>
                <div class="stat-item">
                    <span class="stat-value">${stats.quests || generatedCampaignData.quests.length}</span>
                    <span class="stat-label">Quest Hooks</span>
                </div>
            `;
        }

        showToast('Campaign created successfully!', 'success');

    } catch (error) {
        console.error('Campaign creation error:', error);
        showToast('Failed to create campaign', 'error');
    }
}

function startNewCampaign(): void {
    // Reset and start over
    generatedCampaignData = null;
    selectedTemplate = 'custom';
    
    // Clear form fields
    const inputs = document.querySelectorAll('#campaign-step-1 input, #campaign-step-1 textarea, #campaign-step-1 select');
    inputs.forEach((input: any) => {
        if (input.type === 'range') {
            input.value = input.defaultValue || '5';
        } else if (input.tagName === 'SELECT') {
            input.selectedIndex = 0;
        } else {
            input.value = '';
        }
    });

    // Remove template selection
    document.querySelectorAll('.template-card').forEach(c => c.classList.remove('active'));

    goToStep(1);
}

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    // Navigation click handlers
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', () => {
            const page = item.getAttribute('data-page');
            if (page) showPage(page);
        });
    });

    // Close modals on backdrop click
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('active');
            }
        });
    });

    // Load initial dashboard
    loadDashboard();

    console.log('🎲 RPG DM Bot Manager initialized');
});

// Export functions for HTML onclick handlers
(window as any).showPage = showPage;
(window as any).openModal = openModal;
(window as any).closeModal = closeModal;
(window as any).createSession = createSession;
(window as any).viewSession = viewSession;
(window as any).createLocation = createLocation;
(window as any).deleteLocation = deleteLocation;
(window as any).editLocation = editLocation;
(window as any).updateLocation = updateLocation;
(window as any).createNPC = createNPC;
(window as any).deleteNPC = deleteNPC;
(window as any).editNPC = editNPC;
(window as any).updateNPC = updateNPC;
(window as any).createItem = createItem;
(window as any).revealItem = revealItem;
(window as any).editItem = editItem;
(window as any).updateItem = updateItem;
(window as any).deleteItem = deleteItem;
(window as any).createEvent = createEvent;
(window as any).triggerEvent = triggerEvent;
(window as any).resolveEvent = resolveEvent;
(window as any).editEvent = editEvent;
(window as any).updateEvent = updateEvent;
(window as any).deleteEvent = deleteEvent;
(window as any).loadSnapshots = loadSnapshots;
(window as any).createSavepoint = createSavepoint;
(window as any).loadSavepoint = loadSavepoint;
(window as any).deleteSavepoint = deleteSavepoint;
(window as any).editCharacter = editCharacter;
(window as any).updateCharacter = updateCharacter;
(window as any).showCharacterInventory = showCharacterInventory;
(window as any).equipItem = equipItem;
(window as any).unequipItem = unequipItem;
(window as any).removeInventoryItem = removeInventoryItem;
(window as any).addItemToInventory = addItemToInventory;
(window as any).openAddItemModal = openAddItemModal;
(window as any).searchItemDb = searchItemDb;
(window as any).filterItemDbByType = filterItemDbByType;
(window as any).addItemFromDb = addItemFromDb;
(window as any).loadQuests = loadQuests;
(window as any).createQuest = createQuest;
(window as any).editQuest = editQuest;
(window as any).updateQuest = updateQuest;
(window as any).deleteQuest = deleteQuest;

// Classes editor
(window as any).loadClasses = loadClasses;
(window as any).viewClass = viewClass;
(window as any).editClass = editClass;
(window as any).updateClass = updateClass;

// Races editor
(window as any).loadRaces = loadRaces;
(window as any).viewRace = viewRace;
(window as any).editRace = editRace;
(window as any).updateRace = updateRace;

// Skill trees
(window as any).loadSkillTrees = loadSkillTrees;
(window as any).selectSkillTreeClass = selectSkillTreeClass;
(window as any).showSkillBranch = showSkillBranch;
(window as any).loadSkillTree = loadSkillTree;

// Game data (items)
(window as any).loadGameData = loadItemDb;
(window as any).loadItemDb = loadItemDb;
(window as any).filterGameItems = filterGameItems;
(window as any).loadItemCategory = loadItemCategory;
(window as any).filterItems = filterItems;

// Spellbook
(window as any).loadSpellbook = loadSpellbook;
(window as any).filterSpellbook = filterSpellbook;
(window as any).filterSpells = filterSpells;

// Campaign creator
(window as any).loadCampaignCreator = loadCampaignCreator;
(window as any).generateCampaignPreview = generateCampaignPreview;
(window as any).finalizeCampaign = finalizeCampaign;
(window as any).startNewCampaign = startNewCampaign;
(window as any).goToStep = goToStep;
(window as any).editPreviewItem = editPreviewItem;
(window as any).removePreviewItem = removePreviewItem;
(window as any).addItem = addItem;
(window as any).editSection = editSection;
