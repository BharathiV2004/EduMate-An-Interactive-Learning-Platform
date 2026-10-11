document.addEventListener('DOMContentLoaded', () => {
    // Initialize Lucide icons
    lucide.createIcons();
    
    // State management
    const state = {
        mindMap: {
            id: generateId(),
            name: 'New Mind Map',
            nodes: [],
            connections: [],
            centerNode: ''
        },
        selectedTool: 'select',
        zoom: 1,
        pan: { x: 0, y: 0 },
        draggedNode: null,
        dragOffset: { x: 0, y: 0 },
        isDarkMode: false,
        isToolbarOpen: true,
        isAiLoading: false,
        searchTerm: '',
        selectedNodeId: null,
        history: [],
        historyIndex: -1
    };

    // DOM elements
    const elements = {
        canvas: document.getElementById('canvas'),
        nodesContainer: document.getElementById('nodes-container'),
        connectionsLayer: document.getElementById('connections'),
        toggleSidebar: document.getElementById('toggle-sidebar'),
        sidebar: document.getElementById('sidebar'),
        toggleDarkmode: document.getElementById('toggle-darkmode'),
        mindmapName: document.getElementById('mindmap-name'),
        searchNodes: document.getElementById('search-nodes'),
        toolButtons: document.querySelectorAll('[data-tool]'),
        centralTopic: document.getElementById('central-topic'),
        createCentral: document.getElementById('create-central'),
        showTemplates: document.getElementById('show-templates'),
        templatesContainer: document.getElementById('templates-container'),
        aiSuggest: document.getElementById('ai-suggest'),
        aiText: document.getElementById('ai-text'),
        aiLoading: document.getElementById('ai-loading'),
        aiStatus: document.getElementById('ai-status'),
        zoomIn: document.getElementById('zoom-in'),
        zoomOut: document.getElementById('zoom-out'),
        zoomInBtn: document.getElementById('zoom-in-btn'),
        zoomOutBtn: document.getElementById('zoom-out-btn'),
        zoomLevel: document.getElementById('zoom-level'),
        deleteSelected: document.getElementById('delete-selected'),
        nodeProperties: document.getElementById('node-properties'),
        colorPalette: document.querySelectorAll('.color-palette button'),
        nodeSize: document.getElementById('node-size'),
        emptyState: document.getElementById('empty-state'),
        nodeCount: document.getElementById('node-count'),
        selectedCount: document.getElementById('selected-count'),
        minimapView: document.getElementById('minimap-view')
    };

    // Initialize event listeners
    function initEventListeners() {
        // Toolbar toggle
        elements.toggleSidebar.addEventListener('click', toggleSidebar);
        
        // Dark mode toggle
        elements.toggleDarkmode.addEventListener('click', toggleDarkMode);
        
        // Mind map name update
        elements.mindmapName.addEventListener('change', updateMindMapName);
        
        // Search nodes
        elements.searchNodes.addEventListener('input', handleSearch);
        
        // Tool selection
        elements.toolButtons.forEach(btn => {
            btn.addEventListener('click', () => selectTool(btn.dataset.tool));
        });
        
        // Create central node
        elements.createCentral.addEventListener('click', handleCreateCentral);
        elements.centralTopic.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && elements.centralTopic.value) {
                handleCreateCentral();
            }
        });
        
        // Templates
        elements.showTemplates.addEventListener('click', toggleTemplates);
        
        // AI suggestions
        elements.aiSuggest.addEventListener('click', handleAiSuggest);
        
        // Zoom controls
        elements.zoomIn.addEventListener('click', () => updateZoom(1.2));
        elements.zoomOut.addEventListener('click', () => updateZoom(1/1.2));
        elements.zoomInBtn.addEventListener('click', () => updateZoom(1.2));
        elements.zoomOutBtn.addEventListener('click', () => updateZoom(1/1.2));
        
        // Delete selected
        elements.deleteSelected.addEventListener('click', deleteSelectedNodes);
        
        // Node properties
        elements.colorPalette.forEach(btn => {
            btn.addEventListener('click', () => updateNodeColor(btn.dataset.color));
        });
        elements.nodeSize.addEventListener('change', updateNodeSize);
        
        // Canvas events
        elements.canvas.addEventListener('click', handleCanvasClick);
        elements.canvas.addEventListener('mousemove', handleMouseMove);
        elements.canvas.addEventListener('mouseup', handleMouseUp);
        
        // Keyboard shortcuts
        document.addEventListener('keydown', handleKeyDown);
        
        // Load templates
        loadTemplates();
    }

    // Helper functions
    function generateId() {
        return Math.random().toString(36).substr(2, 9);
    }

    function getNodePosition(angle, radius, centerX, centerY) {
        return {
            x: centerX + radius * Math.cos(angle),
            y: centerY + radius * Math.sin(angle)
        };
    }

    function distance(p1, p2) {
        return Math.sqrt(Math.pow(p2.x - p1.x, 2) + Math.pow(p2.y - p1.y, 2));
    }

    function saveToHistory() {
        const newHistory = state.history.slice(0, state.historyIndex + 1);
        newHistory.push(JSON.parse(JSON.stringify(state.mindMap)));
        state.history = newHistory;
        state.historyIndex = newHistory.length - 1;
    }

    // UI update functions
    function renderNodes() {
        elements.nodesContainer.innerHTML = '';
        
        const filteredNodes = state.searchTerm 
            ? state.mindMap.nodes.filter(node => 
                node.text.toLowerCase().includes(state.searchTerm.toLowerCase()))
            : state.mindMap.nodes;
        
        filteredNodes.forEach(node => {
            const nodeEl = document.createElement('div');
            nodeEl.className = `node ${node.size} ${node.isSelected ? 'selected' : ''}`;
            nodeEl.style.left = `${node.x}px`;
            nodeEl.style.top = `${node.y}px`;
            nodeEl.style.backgroundColor = node.color;
            nodeEl.innerHTML = `<div class="node-text">${node.text}</div>`;
            nodeEl.dataset.id = node.id;
            
            nodeEl.addEventListener('click', (e) => handleNodeClick(e, node.id));
            nodeEl.addEventListener('dblclick', () => handleNodeDoubleClick(node.id));
            nodeEl.addEventListener('mousedown', (e) => handleMouseDown(e, node.id));
            
            elements.nodesContainer.appendChild(nodeEl);
        });
        
        updateNodeCount();
        updateSelectedCount();
        updateMinimap();
    }

    function renderConnections() {
        elements.connectionsLayer.innerHTML = '';
        
        state.mindMap.connections.forEach(conn => {
            const fromNode = state.mindMap.nodes.find(n => n.id === conn.fromId);
            const toNode = state.mindMap.nodes.find(n => n.id === conn.toId);
            
            if (!fromNode || !toNode) return;
            
            const dx = toNode.x - fromNode.x;
            const dy = toNode.y - fromNode.y;
            const controlOffset = Math.min(Math.abs(dx), Math.abs(dy)) * 0.5;
            
            const path = `M ${fromNode.x} ${fromNode.y} 
                         C ${fromNode.x + controlOffset} ${fromNode.y}, 
                           ${toNode.x - controlOffset} ${toNode.y}, 
                           ${toNode.x} ${toNode.y}`;
            
            const pathEl = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            pathEl.setAttribute('d', path);
            pathEl.setAttribute('stroke', state.isDarkMode ? '#64748b' : '#94a3b8');
            pathEl.setAttribute('stroke-width', '2');
            pathEl.setAttribute('fill', 'none');
            pathEl.setAttribute('opacity', '0.8');
            
            elements.connectionsLayer.appendChild(pathEl);
        });
    }

    function updateNodeCount() {
        elements.nodeCount.textContent = state.mindMap.nodes.length;
        if (state.mindMap.nodes.length === 0) {
            elements.emptyState.classList.remove('hidden');
        } else {
            elements.emptyState.classList.add('hidden');
        }
    }

    function updateSelectedCount() {
        const selectedCount = state.mindMap.nodes.filter(n => n.isSelected).length;
        elements.selectedCount.textContent = selectedCount;
        elements.deleteSelected.disabled = selectedCount === 0;
        
        // Show/hide node properties panel
        if (selectedCount === 1) {
            const selectedNode = state.mindMap.nodes.find(n => n.isSelected);
            if (selectedNode) {
                elements.nodeProperties.classList.remove('hidden');
                elements.nodeSize.value = selectedNode.size;
            }
        } else {
            elements.nodeProperties.classList.add('hidden');
        }
    }

    function updateMinimap() {
        elements.minimapView.innerHTML = '';
        
        state.mindMap.nodes.forEach(node => {
            const nodeDot = document.createElement('div');
            nodeDot.className = 'minimap-node';
            nodeDot.style.left = `${(node.x / elements.canvas.offsetWidth) * 100}%`;
            nodeDot.style.top = `${(node.y / elements.canvas.offsetHeight) * 100}%`;
            nodeDot.style.backgroundColor = node.color;
            elements.minimapView.appendChild(nodeDot);
        });
    }

    function updateZoom(factor) {
        state.zoom = Math.max(0.3, Math.min(3, state.zoom * factor));
        elements.canvas.style.transform = `scale(${state.zoom}) translate(${state.pan.x}px, ${state.pan.y}px)`;
        elements.zoomLevel.textContent = `${Math.round(state.zoom * 100)}%`;
    }

    // Event handlers
    function toggleSidebar() {
        state.isToolbarOpen = !state.isToolbarOpen;
        if (state.isToolbarOpen) {
            elements.sidebar.style.transform = 'translateX(0)';
        } else {
            elements.sidebar.style.transform = 'translateX(-100%)';
        }
    }

    function toggleDarkMode() {
        state.isDarkMode = !state.isDarkMode;
        document.body.classList.toggle('dark-mode', state.isDarkMode);
        
        // Update icon
        const icon = elements.toggleDarkmode.querySelector('i');
        if (state.isDarkMode) {
            icon.setAttribute('data-lucide', 'sun');
        } else {
            icon.setAttribute('data-lucide', 'moon');
        }
        lucide.createIcons();
        
        // Re-render connections to update colors
        renderConnections();
    }

    function updateMindMapName() {
        state.mindMap.name = elements.mindmapName.value;
    }

    function handleSearch(e) {
        state.searchTerm = e.target.value;
        renderNodes();
    }

    function selectTool(tool) {
        state.selectedTool = tool;
        elements.toolButtons.forEach(btn => {
            if (btn.dataset.tool === tool) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
    }
        function handleCreateCentral() {
        const topic = elements.centralTopic.value.trim();
        if (!topic) return;

        const centerX = elements.canvas.offsetWidth / 2;
        const centerY = elements.canvas.offsetHeight / 2;

        const centralNode = {
            id: generateId(),
            x: centerX,
            y: centerY,
            text: topic,
            color: '#3b82f6',
            size: 'large',
            isSelected: false,
            level: 0
        };

        state.mindMap = {
            ...state.mindMap,
            centerNode: centralNode.id,
            nodes: [centralNode],
            connections: []
        };

        saveToHistory();
        renderNodes();
        renderConnections();
        elements.centralTopic.value = '';

        // Generate AI suggestions
        generateSubtopics(topic);
    }

    async function generateSubtopics(topic) {
        try {
            state.isAiLoading = true;
            elements.aiStatus.classList.remove('hidden');
            
            const response = await fetch('/api/ai/generate-subtopics', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ topic })
            });
            
            const data = await response.json();
            const subtopics = data.subtopics;
            
            const centerNode = state.mindMap.nodes.find(n => n.id === state.mindMap.centerNode);
            if (!centerNode) return;

            const angleStep = (2 * Math.PI) / subtopics.length;
            const radius = 150;
            
            const newNodes = subtopics.map((text, index) => {
                const angle = index * angleStep;
                const pos = getNodePosition(angle, radius, centerNode.x, centerNode.y);
                
                return {
                    id: generateId(),
                    x: pos.x,
                    y: pos.y,
                    text,
                    color: '#10b981',
                    size: 'medium',
                    isSelected: false,
                    parentId: centerNode.id,
                    level: 1
                };
            });

            const newConnections = newNodes.map(node => ({
                id: generateId(),
                fromId: centerNode.id,
                toId: node.id
            }));

            state.mindMap.nodes = [...state.mindMap.nodes, ...newNodes];
            state.mindMap.connections = [...state.mindMap.connections, ...newConnections];
            
            saveToHistory();
            renderNodes();
            renderConnections();
        } catch (error) {
            console.error('AI suggestion failed:', error);
        } finally {
            state.isAiLoading = false;
            elements.aiStatus.classList.add('hidden');
        }
    }

    function handleNodeClick(e, nodeId) {
        e.stopPropagation();
        
        if (state.selectedTool === 'select') {
            const isCtrlPressed = e.ctrlKey || e.metaKey;
            
            state.mindMap.nodes = state.mindMap.nodes.map(node => ({
                ...node,
                isSelected: node.id === nodeId 
                    ? !node.isSelected 
                    : (isCtrlPressed ? node.isSelected : false)
            }));
            
            renderNodes();
        }
    }

    function handleNodeDoubleClick(nodeId) {
        const node = state.mindMap.nodes.find(n => n.id === nodeId);
        if (!node) return;

        const newText = prompt('Edit node text:', node.text);
        if (newText && newText !== node.text) {
            node.text = newText;
            saveToHistory();
            renderNodes();
        }
    }

    function handleMouseDown(e, nodeId) {
        e.preventDefault();
        state.draggedNode = nodeId;
        
        const rect = elements.canvas.getBoundingClientRect();
        const node = state.mindMap.nodes.find(n => n.id === nodeId);
        
        if (node) {
            state.dragOffset = {
                x: (e.clientX - rect.left) - node.x,
                y: (e.clientY - rect.top) - node.y
            };
        }
    }

    function handleMouseMove(e) {
        if (!state.draggedNode) return;

        const rect = elements.canvas.getBoundingClientRect();
        const node = state.mindMap.nodes.find(n => n.id === state.draggedNode);
        
        if (node) {
            node.x = (e.clientX - rect.left) - state.dragOffset.x;
            node.y = (e.clientY - rect.top) - state.dragOffset.y;
            renderNodes();
            renderConnections();
        }
    }

    function handleMouseUp() {
        if (state.draggedNode) {
            state.draggedNode = null;
            saveToHistory();
        }
    }

    function handleCanvasClick(e) {
        if (state.selectedTool === 'add') {
            const rect = elements.canvas.getBoundingClientRect();
            const x = (e.clientX - rect.left) / state.zoom - state.pan.x;
            const y = (e.clientY - rect.top) / state.zoom - state.pan.y;
            
            addNode(x, y);
        } else {
            // Deselect all nodes
            state.mindMap.nodes = state.mindMap.nodes.map(n => ({ ...n, isSelected: false }));
            renderNodes();
        }
    }

    function addNode(x, y, parentId) {
        const newNode = {
            id: generateId(),
            x,
            y,
            text: 'New Node',
            color: parentId ? '#6366f1' : '#3b82f6',
            size: 'medium',
            isSelected: true,
            parentId,
            level: parentId ? (state.mindMap.nodes.find(n => n.id === parentId)?.level || 0) + 1 : 0
        };

        state.mindMap.nodes = state.mindMap.nodes.map(n => ({ ...n, isSelected: false }));
        state.mindMap.nodes.push(newNode);

        if (parentId) {
            state.mindMap.connections.push({
                id: generateId(),
                fromId: parentId,
                toId: newNode.id
            });
        }

        saveToHistory();
        renderNodes();
        renderConnections();
    }

    function handleKeyDown(e) {
        if (e.ctrlKey || e.metaKey) {
            switch (e.key.toLowerCase()) {
                case 'z':
                    e.preventDefault();
                    if (state.historyIndex > 0) {
                        state.historyIndex--;
                        state.mindMap = JSON.parse(JSON.stringify(state.history[state.historyIndex]));
                        renderNodes();
                        renderConnections();
                    }
                    break;
                case 'y':
                    e.preventDefault();
                    if (state.historyIndex < state.history.length - 1) {
                        state.historyIndex++;
                        state.mindMap = JSON.parse(JSON.stringify(state.history[state.historyIndex]));
                        renderNodes();
                        renderConnections();
                    }
                    break;
                case 's':
                    e.preventDefault();
                    saveMindMap();
                    break;
            }
        } else if (e.key === 'Delete') {
            deleteSelectedNodes();
        }
    }

    function deleteSelectedNodes() {
        const selectedIds = state.mindMap.nodes.filter(n => n.isSelected).map(n => n.id);
        if (selectedIds.length === 0) return;

        state.mindMap.nodes = state.mindMap.nodes.filter(n => !selectedIds.includes(n.id));
        state.mindMap.connections = state.mindMap.connections.filter(c => 
            !selectedIds.includes(c.fromId) && !selectedIds.includes(c.toId)
        );

        saveToHistory();
        renderNodes();
        renderConnections();
    }

    function updateNodeColor(color) {
        const selectedNode = state.mindMap.nodes.find(n => n.isSelected);
        if (selectedNode) {
            selectedNode.color = color;
            saveToHistory();
            renderNodes();
        }
    }

    function updateNodeSize(e) {
        const size = e.target.value;
        const selectedNode = state.mindMap.nodes.find(n => n.isSelected);
        if (selectedNode) {
            selectedNode.size = size;
            saveToHistory();
            renderNodes();
        }
    }

    async function loadTemplates() {
        try {
            const response = await fetch('/api/templates');
            const templates = await response.json();
            
            elements.templatesContainer.innerHTML = templates
                .map(t => `
                    <div class="template-item" data-name="${t.name}">
                        ${t.name}
                    </div>
                `).join('');
            
            elements.templatesContainer.querySelectorAll('.template-item').forEach(item => {
                item.addEventListener('click', () => {
                    const template = templates.find(t => t.name === item.dataset.name);
                    if (template) {
                        elements.centralTopic.value = template.structure.center;
                        handleCreateCentral();
                        elements.templatesContainer.classList.add('hidden');
                    }
                });
            });
        } catch (error) {
            console.error('Failed to load templates:', error);
        }
    }

    function toggleTemplates() {
        elements.templatesContainer.classList.toggle('hidden');
    }

    async function saveMindMap() {
        try {
            const response = await fetch('/api/mindmaps', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(state.mindMap)
            });
            
            if (response.ok) {
                alert('Mind map saved successfully!');
            }
        } catch (error) {
            console.error('Failed to save mind map:', error);
        }
    }

    // Initialize the application
    initEventListeners();
    renderNodes();
    renderConnections();
});