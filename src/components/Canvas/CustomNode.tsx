import React, { memo, useState } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { NodeData } from '../../types';
import { useMindMapStore } from '../../store/mindMapStore';

const CustomNode: React.FC<NodeProps<NodeData>> = ({ data, isConnectable }) => {
  const [isEditing, setIsEditing] = useState(false);
  const { updateNode } = useMindMapStore();
  const [label, setLabel] = useState(data.label);

  const handleDoubleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsEditing(true);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      setIsEditing(false);
      updateNode(data.id, { label });
    }
  };

  const handleBlur = () => {
    setIsEditing(false);
    updateNode(data.id, { label });
  };

  const nodeStyle = {
    padding: '10px 20px',
    borderRadius: '5px',
    border: '1px solid #ddd',
    backgroundColor: data.color || '#ffffff',
    fontSize: data.fontSize || '14px',
    width: data.width || 'auto',
    minWidth: '100px',
    minHeight: '40px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    position: 'relative' as const,
  };

  return (
    <div style={nodeStyle} onDoubleClick={handleDoubleClick}>
      <Handle
        type="target"
        position={Position.Top}
        isConnectable={isConnectable}
      />
      {isEditing ? (
        <input
          type="text"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={handleBlur}
          autoFocus
          style={{
            width: '100%',
            border: 'none',
            background: 'transparent',
            textAlign: 'center',
            outline: 'none',
          }}
        />
      ) : (
        <div
          style={{
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            textAlign: 'center',
          }}
        >
          {data.label}
        </div>
      )}
      {data.images?.map((image, index) => (
        <img
          key={index}
          src={image}
          alt={`Node image ${index + 1}`}
          style={{
            maxWidth: '100px',
            maxHeight: '100px',
            margin: '5px',
          }}
        />
      ))}
      <Handle
        type="source"
        position={Position.Bottom}
        isConnectable={isConnectable}
      />
    </div>
  );
};

export default memo(CustomNode); 