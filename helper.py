import streamlit as st
import json
import networkx as nx
import matplotlib.pyplot as plt
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from mistralai import Mistral
from collections import deque
import re

def extract_solution(text):
    # Use regex to find text between <Solution> and </Solution> tags
    match = re.search(r'<Solution>(.*?)</Solution>', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    else:
        return None


def extract_tools(data, thoughts):
    thoughts = json.loads(thoughts)
    tool_names = [item["tool_name"] for item in thoughts if "tool_name" in item]
    tools = []
    print(tool_names)
    #     print(tool_names)
    for tool in tool_names:
        #         print(tool)
        matching_tools = [tool1 for tool1 in data if tool1['tool_name'] == tool]
        print(matching_tools)
        tools.append(matching_tools[0])
    return tools

def create_graph(data):
    G = nx.DiGraph()

    # Add tools to the graph
    for tool in data:
        inp = tool['args'][0]['arg_type'] if len(tool['args']) > 0 else None
        G.add_node(tool['tool_name'], input_type=inp, output_type=tool['output']['arg_type'])

    for tool_a in data:
        for tool_b in data:
            if (len(tool_b['args']) > 0 and tool_a != tool_b):
                for i in range(len(tool_b['args'])):
                    if tool_a['output']['arg_type'] == tool_b['args'][i]['arg_type']:
                        G.add_edge(tool_a['tool_name'], tool_b['tool_name'])
                        weight = 0.1 if tool_b['args'][i].get('is_required', False) else 0.4
                        G.add_edge(tool_a['tool_name'], tool_b['tool_name'], weight=weight)
    return G

def generate_embeddings(descriptions, model, t='cosine'):
    sentences = descriptions
    embeddings = model.encode(sentences)

    if (t == 'cosine'):
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)  # Normalize the embeddings
    embedding_dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(embedding_dimension)  # Use cosine similarity
    index.add(embeddings)
    return index


def return_retrieved_tools(data, descriptions, query, model, index, k, t='cosine'):
    query_embedding = model.encode([query])
    relevance_dict = {}

    if (t == 'cosine'):
        query_embedding = query_embedding / np.linalg.norm(query_embedding, axis=1, keepdims=True)
    distances, indices = index.search(query_embedding, k)

    tools = []
    for i, idx in enumerate(indices[0]):
        tool_name = descriptions[idx].split(':')[0]
        matching_tools = [tool for tool in data if tool['tool_name'] == tool_name]
        relevance_dict[tool_name] = distances[0][i]
        tools.append(str(matching_tools[0]))

    return (distances, indices, tools, relevance_dict)


def calculate_r_values(G, tools, relevance_dict, gamma):
    r_values = relevance_dict

    for tool in tools:
        queue = deque([(tool, 0, 0)])  # Track each tool with its level (depth)

        while queue:
            current_tool, level, cur_w = queue.popleft()

            for ancestor in G.predecessors(current_tool):
                #                 print(ancestor)
                if ancestor not in r_values:
                    edge_data = G.get_edge_data(ancestor, current_tool)
                    weight = edge_data['weight']

                    t = level + 1  # Ancestor is one level higher than current tool

                    # Apply annealing factor gamma^t to the weight
                    annealed_weight = weight * (gamma ** t) + cur_w

                    if current_tool in relevance_dict:
                        r_value = relevance_dict[current_tool] * annealed_weight
                        r_values[ancestor] = r_value

                    # Add ancestor to the queue with incremented level
                    queue.append((ancestor, t, r_value))

    return r_values

