import React, { useCallback, useEffect } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  Edge,
  Node,
  useReactFlow,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { useMindMapStore } from '../../store/mindMapStore';
import { NodeData, EdgeData } from '../../types';
import CustomNode from './CustomNode';
import { generateId } from '../../utils/helpers';

const nodeTypes = {
  custom: CustomNode,
};

export const MindMapCanvas: React.FC = () => {
  const { currentMap, addNode, addEdge: storeAddEdge, updateNode } = useMindMapStore();
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const { project } = useReactFlow();

  useEffect(() => {
    if (currentMap) {
      setNodes(currentMap.nodes.map((node) => ({
        id: node.id,
        type: 'custom',
        position: node.position,
        data: node,
      })));
      setEdges(currentMap.edges);
    }
  }, [currentMap, setNodes, setEdges]);

  const onConnect = useCallback(
    (params: Connection | Edge) => {
      const edge: EdgeData = {
        id: generateId(),
        source: params.source || '',
        target: params.target || '',
        type: 'bezier',
      };
      storeAddEdge(edge);
      setEdges((eds) => addEdge(params, eds));
    },
    [storeAddEdge, setEdges]
  );

  const onNodeDoubleClick = useCallback(
    (event: React.MouseEvent, node: Node) => {
      const position = project({
        x: event.clientX,
        y: event.clientY,
      });

      const newNode: Omit<NodeData, 'id'> = {
        type: 'subtopic',
        label: 'New Topic',
        position,
      };

      addNode(newNode);
    },
    [project, addNode]
  );

  const onNodeDragStop = useCallback(
    (_: React.MouseEvent, node: Node) => {
      updateNode(node.id, { position: node.position });
    },
    [updateNode]
  );

  return (
    <div style={{ width: '100%', height: '100vh' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeDoubleClick={onNodeDoubleClick}
        onNodeDragStop={onNodeDragStop}
        nodeTypes={nodeTypes}
        fitView
      >
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  );
}; 