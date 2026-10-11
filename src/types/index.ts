export interface NodeData {
  id: string;
  type: 'central' | 'subtopic' | 'detail';
  label: string;
  color?: string;
  fontSize?: number;
  width?: number;
  height?: number;
  images?: string[];
  richText?: string;
  position: { x: number; y: number };
}

export interface EdgeData {
  id: string;
  source: string;
  target: string;
  type?: 'bezier' | 'straight' | 'smoothstep';
  style?: {
    stroke?: string;
    strokeWidth?: number;
  };
}

export interface MindMap {
  id: string;
  name: string;
  createdAt: string;
  updatedAt: string;
  nodes: NodeData[];
  edges: EdgeData[];
  version: number;
  theme: 'light' | 'dark';
}

export interface AIResponse {
  suggestions: string[];
  connections: Array<{
    source: string;
    target: string;
    strength: number;
  }>;
  clusters: Array<{
    name: string;
    nodeIds: string[];
  }>;
}

export interface UserSettings {
  theme: 'light' | 'dark';
  autoSave: boolean;
  snapToGrid: boolean;
  gridSize: number;
  defaultNodeColor: string;
  defaultEdgeType: 'bezier' | 'straight' | 'smoothstep';
}

export type ToolbarAction = 
  | 'addNode'
  | 'connect'
  | 'delete'
  | 'undo'
  | 'redo'
  | 'zoomIn'
  | 'zoomOut'
  | 'fit'
  | 'group'
  | 'ungroup';

export interface HistoryEntry {
  timestamp: number;
  action: string;
  data: Partial<MindMap>;
} 