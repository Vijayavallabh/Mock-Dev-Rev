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
        match = json.loads(match.group(1))
        return match
    else:
        return None


def extract_tools(data, thoughts):
    tool_names = [item["tool_name"] for item in thoughts if "tool_name" in item]
    tools = []
    #     print(tool_names)
    for tool in tool_names:
        #         print(tool)
        matching_tools = [tool1 for tool1 in data if tool1['tool_name'] == tool]
        try:
            tools.append(matching_tools[0])
        except:
            tools = []
            break
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


def load_tool_descriptions(file_path):
     """Load the tool descriptions from the JSON file."""
     import json


     with open('/content/tool_up.json', 'r') as file:
         data = json.load(file)
     return {tool['tool_name']: tool for tool in data}

def validate_tool_input(tool_name, arguments, tool_descriptions):
     """
#     Validate the input arguments against the tool's expected argument types dynamically.

#     :param tool_name: The name of the tool to validate against.
#     :param arguments: A list of arguments provided for the tool.
#     :param tool_descriptions: Dictionary of tool descriptions.
#     :return: True if valid, False and error message if invalid.
#     """
     if tool_name not in tool_descriptions:
         return False, f"Tool '{tool_name}' not found."

     tool_info = tool_descriptions[tool_name]
     expected_arguments = {arg['arg_name']: arg['arg_type'] for arg in tool_info['args']}

     for arg in arguments:
         arg_name = arg['arg_name']
         arg_value = arg['arg_value']
         expected_type = expected_arguments[arg_name]

         if arg_name not in expected_arguments:
             return False, f"Argument '{arg_name}' is not recognized for tool '{tool_name}'."
         if type(arg_value) not in type_mapping:
            return False, f"Argument '{expected_type}' is not a valid datatype'"


         # Check if the argument's type matches the expected type
         if not isinstance(arg_value, type_mapping[expected_type]):
             return False, f"Argument '{arg_name}' should be of type '{expected_type}'."



     return True, "Validation successful."

def validate_tool_output(tool_output, previous_tool,next_tool_name, tool_descriptions):
    """
    Validate if the output of one tool matches the expected input type of the next tool.
    If the types don't match, attempt conversion.
    """
    if next_tool_name not in tool_descriptions:
        return False, f"Next tool '{next_tool_name}' not found."

    next_tool_info = tool_descriptions[next_tool_name]
    expected_input_type = next_tool_info['input_type']

    # Debug: Print the types for comparison
    print(f"Validating output for next tool '{next_tool_name}'")
    print(f"Tool output: {tool_output} (type: {type(tool_output)})")
    print(f"Expected input type: {expected_input_type}")

    # Check if the tool output matches the next tool's expected input type
    if isinstance(tool_output, type_mapping[expected_input_type]):
        print("Output matches expected type.")
        return tool_output, "Output is valid for the next tool."

    # Attempt to convert the output to the expected input type
    converted_output, success = convert_type(tool_output,previous_tool,next_tool_name, expected_input_type)

    # Debug: Print the conversion result
    print(f"Converted output: {converted_output} (success: {success})")

    if success:
        return converted_output, True

    return tool_output, False

def mmr(query_embedding, document_embeddings, k=5, lambda_param=0.5):
    """
    MMR implementation for diverse document retrieval.
    query_embedding: embedding of the query.
    document_embeddings: embeddings of all documents.
    k: number of documents to retrieve.
    lambda_param: trade-off between relevance and diversity (0 to 1).
    """

    query_similarities = cosine_similarity(query_embedding, document_embeddings)[0]

    doc_similarities = cosine_similarity(document_embeddings)

    selected_indices = []
    unselected_indices = list(range(len(document_embeddings)))

    best_doc_index = np.argmax(query_similarities)
    selected_indices.append(best_doc_index)
    unselected_indices.remove(best_doc_index)

    for _ in range(k - 1):
        mmr_values = []
        for i in unselected_indices:
            relevance = query_similarities[i]
            diversity = max([doc_similarities[i][j] for j in selected_indices])
            mmr_score = lambda_param * relevance - (1 - lambda_param) * diversity
            mmr_values.append(mmr_score)

        best_doc_index = unselected_indices[np.argmax(mmr_values)]
        selected_indices.append(best_doc_index)
        unselected_indices.remove(best_doc_index)

    return selected_indices


def augment_descriptions(data, client):
    descriptions = []
    for i in range(len(data)):
        chat_response = client.chat.complete(
            model=model,
            messages=[{
                "role": "system",
                "content": """
                    You are an AI assistant designed to understand and explain the functionality of API tools. 
                    Your task is to analyze the given tool, break down its arguments, and generate a clear, concise, and informative description."""
            },
                {
                    "role": "assistant",
                    "content": """Your task is to provide a detailed description of the provided tool's functionality. 
                    Carefully explain each argument it accepts, how the tool works, and what kind of output it generates. 
                    Summarize its purpose in a way that highlights its use cases, keeping the explanation clear for developers. 
                    Output the description in three sentences."""
                },
                {
                    "role": "user",
                    "content": f"You are provided with the following tool, including its structure and arguments: {str(data[i])}."
                }]
        )
        descriptions.append(chat_response.choices[0].message.content)
    return descriptions