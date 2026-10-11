import React from 'react';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  ZoomIn as ZoomInIcon,
  ZoomOut as ZoomOutIcon,
  Undo as UndoIcon,
  Redo as RedoIcon,
  Save as SaveIcon,
  FolderOpen as OpenIcon,
  Lightbulb as AIIcon,
  ColorLens as ColorIcon,
  Image as ImageIcon,
  DarkMode as ThemeIcon,
} from '@mui/icons-material';
import { SpeedDial, SpeedDialAction, SpeedDialIcon } from '@mui/material';
import { useMindMapStore } from '../../store/mindMapStore';
import { AIService } from '../../services/aiService';

const actions = [
  { icon: <AddIcon />, name: 'Add Node', action: 'add' },
  { icon: <DeleteIcon />, name: 'Delete', action: 'delete' },
  { icon: <ZoomInIcon />, name: 'Zoom In', action: 'zoomIn' },
  { icon: <ZoomOutIcon />, name: 'Zoom Out', action: 'zoomOut' },
  { icon: <UndoIcon />, name: 'Undo', action: 'undo' },
  { icon: <RedoIcon />, name: 'Redo', action: 'redo' },
  { icon: <SaveIcon />, name: 'Save', action: 'save' },
  { icon: <OpenIcon />, name: 'Open', action: 'open' },
  { icon: <AIIcon />, name: 'AI Suggestions', action: 'ai' },
  { icon: <ColorIcon />, name: 'Change Color', action: 'color' },
  { icon: <ImageIcon />, name: 'Add Image', action: 'image' },
  { icon: <ThemeIcon />, name: 'Toggle Theme', action: 'theme' },
];

export const Toolbar: React.FC = () => {
  const {
    currentMap,
    userSettings,
    updateSettings,
    undo,
    redo,
    addNode,
    deleteNode,
    selectedNodes,
  } = useMindMapStore();

  const aiService = AIService.getInstance();

  const handleAction = async (action: string) => {
    switch (action) {
      case 'undo':
        undo();
        break;
      case 'redo':
        redo();
        break;
      case 'delete':
        selectedNodes.forEach((nodeId) => deleteNode(nodeId));
        break;
      case 'theme':
        updateSettings({
          theme: userSettings.theme === 'light' ? 'dark' : 'light',
        });
        break;
      case 'ai':
        if (currentMap && currentMap.nodes.length > 0) {
          const suggestions = await aiService.generateSubtopics(
            currentMap.nodes[0].label
          );
          suggestions.forEach((suggestion) => {
            addNode({
              type: 'subtopic',
              label: suggestion,
              position: { x: Math.random() * 500, y: Math.random() * 500 },
            });
          });
        }
        break;
      // Add more actions as needed
    }
  };

  return (
    <SpeedDial
      ariaLabel="Mind Map Toolbar"
      sx={{ position: 'absolute', bottom: 16, right: 16 }}
      icon={<SpeedDialIcon />}
    >
      {actions.map((action) => (
        <SpeedDialAction
          key={action.name}
          icon={action.icon}
          tooltipTitle={action.name}
          onClick={() => handleAction(action.action)}
        />
      ))}
    </SpeedDial>
  );
}; 