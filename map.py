from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
import uuid
import requests
import json
from datetime import datetime

app = Flask(__name__)
CORS(app)

# In-memory storage for mind maps
mind_maps = {}

class AIService:
    @staticmethod
    def generate_subtopics(topic: str) -> list[str]:
        try:
            prompt = f"""
            You are a helpful assistant that generates relevant subtopics for mind maps.
            Given the main topic "{topic}", please generate 5-7 relevant subtopics.
            Return only a JSON array of strings, nothing else.
            
            Example for "Project Management":
            ["Planning", "Execution", "Monitoring", "Team Coordination", "Risk Assessment"]
            """
            
            response = requests.post(
                'http://localhost:11434/api/generate',
                json={
                    "model": "qwen2.5:latest",
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3}
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                try:
                    subtopics = json.loads(result['response'].strip())
                    if isinstance(subtopics, list):
                        return subtopics
                except json.JSONDecodeError:
                    lines = [line.strip() for line in result['response'].split('\n') if line.strip()]
                    return lines[:7]
                
            return ["Research", "Development", "Implementation", "Testing", "Evaluation"]
            
        except Exception as e:
            print(f"AI generation failed: {e}")
            return ["Concept 1", "Concept 2", "Concept 3", "Concept 4", "Concept 5"]

    @staticmethod
    def suggest_connections(nodes: list[dict]) -> list[dict]:
        try:
            node_list = "\n".join([f"- {node['text']} (ID: {node['id']})" for node in nodes])
            prompt = f"""
            Given these mind map nodes:
            {node_list}
            
            Suggest 2-3 logical connections between these nodes.
            Return only a JSON array of objects with 'from', 'to', and 'reason' properties.
            """
            
            response = requests.post(
                'http://localhost:11434/api/generate',
                json={
                    "model": "qwen2.5:latest",
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3}
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                try:
                    connections = json.loads(result['response'].strip())
                    if isinstance(connections, list):
                        return connections[:3]
                except json.JSONDecodeError:
                    pass
                    
            if len(nodes) >= 2:
                return [{
                    "from": nodes[0]['id'],
                    "to": nodes[1]['id'],
                    "reason": "These concepts are related"
                }]
            return []
            
        except Exception as e:
            print(f"AI connection suggestion failed: {e}")
            return []

# API Endpoints
@app.route('/api/mindmaps', methods=['GET', 'POST'])
def handle_mindmaps():
    if request.method == 'POST':
        data = request.json
        map_id = str(uuid.uuid4())
        mind_maps[map_id] = {
            **data,
            'id': map_id,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        return jsonify(mind_maps[map_id]), 201
    return jsonify(list(mind_maps.values()))

@app.route('/api/mindmaps/<map_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_mindmap(map_id):
    if map_id not in mind_maps:
        return jsonify({"error": "Mind map not found"}), 404
        
    if request.method == 'GET':
        return jsonify(mind_maps[map_id])
    elif request.method == 'PUT':
        data = request.json
        mind_maps[map_id] = {
            **data,
            'id': map_id,
            'updated_at': datetime.now().isoformat()
        }
        return jsonify(mind_maps[map_id])
    elif request.method == 'DELETE':
        del mind_maps[map_id]
        return jsonify({"success": True})

@app.route('/api/ai/generate-subtopics', methods=['POST'])
def generate_subtopics():
    data = request.json
    subtopics = AIService.generate_subtopics(data.get('topic', ''))
    return jsonify({"subtopics": subtopics})

@app.route('/api/ai/suggest-connections', methods=['POST'])
def suggest_connections():
    data = request.json
    connections = AIService.suggest_connections(data.get('nodes', []))
    return jsonify({"connections": connections})

@app.route('/api/templates', methods=['GET'])
def get_templates():
    templates = [
        {
            'name': 'SWOT Analysis',
            'structure': {'center': 'SWOT Analysis', 'branches': ['Strengths', 'Weaknesses', 'Opportunities', 'Threats']}
        },
        {
            'name': 'Project Planning',
            'structure': {'center': 'Project Plan', 'branches': ['Scope', 'Timeline', 'Resources', 'Risks', 'Deliverables']}
        }
    ]
    return jsonify(templates)

# Main route
@app.route('/')
def index():
    return render_template('map.html')

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)