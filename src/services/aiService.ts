import axios from 'axios';
import { AIResponse, NodeData } from '../types';

const OLLAMA_API_URL = 'http://localhost:11434/api';

export class AIService {
  private static instance: AIService;
  private constructor() {}

  static getInstance(): AIService {
    if (!AIService.instance) {
      AIService.instance = new AIService();
    }
    return AIService.instance;
  }

  async generateSubtopics(topic: string): Promise<string[]> {
    try {
      const response = await axios.post(`${OLLAMA_API_URL}/generate`, {
        model: 'llama2',
        prompt: `Generate 7 relevant subtopics for the mind map topic: "${topic}". 
                Return only the subtopics as a comma-separated list.`,
        stream: false,
      });

      const subtopics = response.data.response
        .split(',')
        .map((topic: string) => topic.trim())
        .filter((topic: string) => topic.length > 0);

      return subtopics;
    } catch (error) {
      console.error('Error generating subtopics:', error);
      return [];
    }
  }

  async suggestConnections(nodes: NodeData[]): Promise<Array<{ source: string; target: string; strength: number }>> {
    try {
      const nodeLabels = nodes.map(node => node.label).join(', ');
      const response = await axios.post(`${OLLAMA_API_URL}/generate`, {
        model: 'llama2',
        prompt: `Analyze these concepts and suggest logical connections between them: ${nodeLabels}. 
                Return the connections in format: concept1->concept2,strength(1-10)`,
        stream: false,
      });

      const connections = response.data.response
        .split('\n')
        .map((line: string) => {
          const [concepts, strength] = line.split(',');
          const [source, target] = concepts.split('->');
          return {
            source: nodes.find(n => n.label === source.trim())?.id || '',
            target: nodes.find(n => n.label === target.trim())?.id || '',
            strength: parseInt(strength, 10) || 5,
          };
        })
        .filter((conn: any) => conn.source && conn.target);

      return connections;
    } catch (error) {
      console.error('Error suggesting connections:', error);
      return [];
    }
  }

  async identifyKnowledgeGaps(nodes: NodeData[]): Promise<string[]> {
    try {
      const nodeLabels = nodes.map(node => node.label).join(', ');
      const response = await axios.post(`${OLLAMA_API_URL}/generate`, {
        model: 'llama2',
        prompt: `Given these concepts in a mind map: ${nodeLabels}, 
                identify potential missing important concepts or knowledge gaps. 
                Return as a comma-separated list.`,
        stream: false,
      });

      const gaps = response.data.response
        .split(',')
        .map((gap: string) => gap.trim())
        .filter((gap: string) => gap.length > 0);

      return gaps;
    } catch (error) {
      console.error('Error identifying knowledge gaps:', error);
      return [];
    }
  }

  async suggestClusters(nodes: NodeData[]): Promise<Array<{ name: string; nodeIds: string[] }>> {
    try {
      const nodeLabels = nodes.map(node => `${node.id}:${node.label}`).join(', ');
      const response = await axios.post(`${OLLAMA_API_URL}/generate`, {
        model: 'llama2',
        prompt: `Given these nodes in a mind map: ${nodeLabels}, 
                suggest logical clusters/groups. Return in format: 
                clusterName:nodeId1,nodeId2,nodeId3`,
        stream: false,
      });

      const clusters = response.data.response
        .split('\n')
        .map((line: string) => {
          const [name, nodeList] = line.split(':');
          return {
            name: name.trim(),
            nodeIds: nodeList.split(',').map((id: string) => id.trim()),
          };
        })
        .filter((cluster: any) => cluster.name && cluster.nodeIds.length > 0);

      return clusters;
    } catch (error) {
      console.error('Error suggesting clusters:', error);
      return [];
    }
  }
} 