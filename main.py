import streamlit as st
import json
import networkx as nx
import matplotlib.pyplot as plt
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from mistralai import Mistral
from collections import deque
from sklearn.metrics.pairwise import cosine_similarity
import re
from helper import *
from prompts import *

sen_transform_model = SentenceTransformer("local_toolbench_model")
mistral_model = 'mistral-small-latest'
api_key_thoughts = "JFjnvpdvtuUHt8L4CvxhlZIcm7ju4cGF"
api_key = api_key_thoughts
api_client2 = api_key_thoughts
api_final = api_key_thoughts
i = 0


st.title('Tools and LLMs')

# File uploader for a JSON file
uploaded_file = st.file_uploader("Choose a JSON file", type=["json"])

# Check if a file has been uploaded
if uploaded_file is not None:
    st.write(f"You uploaded: {uploaded_file.name}")
    file_contents = uploaded_file.read().decode("utf-8")
    try:
        data = json.loads(file_contents)
    except json.JSONDecodeError:
        st.error("The file you uploaded is not a valid JSON.")

    ############################# Creating graph #############################
    G = create_graph(data)
    st.sidebar.header("Graph Visualization")
    fig, ax = plt.subplots(figsize=(5, 5))
    nx.draw(G, with_labels=True, node_color='lightblue', node_size=500, font_size=10, font_color='black', edge_color='gray', ax=ax)
    st.sidebar.pyplot(fig)




    ############################# Tool Description Augmentation #############################

    client_d = Mistral(api_key=api_key)
    # descriptions = augment_descriptions(data, client_d)




    ############################# Generating Vector Store #############################
    descriptions = []
    for tool in data:
        tool_n = tool['tool_name']
        args_desc = ' '.join([arg['arg_name'] + ': ' + arg['arg_description'] for arg in tool['args']])
        d = tool_n + ': ' + tool['tool_description'] + ' || Arguments: ' + args_desc
        if (d not in descriptions):
            descriptions.append(d)
    index = generate_embeddings(descriptions, sen_transform_model, t='cosine')




    ##################################################################################
    query = st.text_input("Please enter the query")
    if query:  # Proceed only if a query has been entered




        ############################# Tool retrieval #############################
        k = 10
        distances, indices, tools, relevance_dict = return_retrieved_tools(data, descriptions, query, sen_transform_model, index, k, t='cosine')
        retrieved_tools = [descriptions[i].split(':')[0] for i in indices[0]]
        r_values = calculate_r_values(G, retrieved_tools, relevance_dict, 0.9)
        r_values = dict(sorted(r_values.items(), key=lambda item: item[1], reverse=True))
        k = 13  # top k matching tools
        tools = [i for i in list(r_values.keys())[:k]]
        tools_comb = []
        for tool_name in tools:
            for tool in data:
                if (tool['tool_name'] == tool_name):
                    tools_comb.append(str(tool))




            ############################# Retrieving Examples ###################################
            # with open('./example_generation.txt', 'r') as f:
            #     examples = f.read()
            #
            # pattern = r"('Example: Query:.*?</Solution>)"
            # examples_list = re.findall(pattern, examples, re.DOTALL)
            # document_embeddings = modsen_transform_model.encode(examples_list, convert_to_tensor=True)
            # document_embeddings = document_embeddings.numpy()
            #
            # query = """I need to order tests "CBC", "Lipid Panel", and "Liver Function" for the patient with ID "P-12345"."""
            # query_embedding = sen_transform_model.encode([query], convert_to_tensor=True).cpu().numpy()
            # selected_indices = mmr(query_embedding, document_embeddings, k=3, lambda_param=0.2)
            # retrieved_documents = [examples_list[i] for i in selected_indices]
            # relevant_examples = '\n'.join(retrieved_documents)
            # # print("Retrieved Documents:", '\n'.join(retrieved_documents))




        ################################# Query 1 ######################################
        tools_str = " ".join(tools_comb)
        final_prompt = str(prompt) + tools_str + str(example)


        client_thoughts = Mistral(api_key=api_key_thoughts)
        chat_response_thoughts = client_thoughts.chat.complete(
            model=mistral_model,
            messages=[
                {
                    "role": "assistant",
                    "content": str(final_prompt),
                },
                {
                    "role": "user",
                    "content": str(query),
                },

            ],
        )
        # st.write(chat_response_thoughts.choices[0].message.content)
        print(chat_response_thoughts.choices[0].message.content)
        thoughts = extract_solution(chat_response_thoughts.choices[0].message.content)
        tools = extract_tools(data, thoughts)


        if (len(tools) < len(thoughts)):
            st.write('[]')
        else:
            print(thoughts)




            ######################## JSON formatting ##########################
            user_prompt = f"""
                            Query: {query}
    
                            Thoughts = {thoughts}
    
                            Tools = {tools}
                            """

            client2 = Mistral(api_key=api_client2)
            chat_response2 = client2.chat.complete(
                model=mistral_model,
                messages=[
                    {
                        "role": "assistant",
                        "content": str(JSON_formatting_prompt),
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],

            )
            i += 1
            DEFAULT_SYSTEM_PROMPT = "You are a repeater machine. You should output as it is what is given to you as an Input."
            client_final = Mistral(api_key=api_final)
            chat_response_final = client_final.chat.complete(
                model=mistral_model,
                messages=[
                    {
                        "role": "assistant",
                        "content": str(DEFAULT_SYSTEM_PROMPT),
                    },
                    {
                        "role": "user",
                        "content": str(chat_response2.choices[0].message.content),
                    },

                ], response_format={
                    "type": "json_object",
                }
            )

            st.write(chat_response2.choices[0].message.content)
