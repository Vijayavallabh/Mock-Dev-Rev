import os
import json
from click import prompt
import google.generativeai as genai
API_KEY_GEMINI = 'Enter API key'
examples = ["""
    'Example: Query: List work items owned by ’DEVU-789’ needing response for organization ’REV-654’ '
    '<Solution>
    [
    {
        "thought": "First, we need to list the work items created by users 'DEVU-123' or 'DEVU-456' that also need a response.",
        "tool_name": "works_list",
        "task": "Use the works_list tool with the arguments: 'created_by' = ['DEVU-123', 'DEVU-456'], 'type' = ['issue', 'task'], and 'ticket_need_response' = true."
    }
    ]
    </Solution>
""","""
    'Example: Query: List issues with ’blocker’ severity categorized as tickets '
    '<Solution>
    [
    {
        "thought": "First, we need to list all issues with 'blocker' severity and filter them to include only those categorized as tickets.",
        "tool_name": "works_list",
        "task": "Use the works_list tool with the arguments: 'ticket_severity' = ['blocker'] and 'type' = ['ticket']."
    }
    ]
    </Solution>
    ""","""
    'Example: Query: Find issues or tasks created by users ’DEVU-123’ or ’DEVU-456’ '
    '<Solution>
    [
    {
        "thought": "First, we need to retrieve all issues and tasks created by the specified users, 'DEVU-123' and 'DEVU-456'.",
        "tool_name": "works_list",
        "task": "Use the works_list tool with the arguments: 'created_by' = ['DEVU-123', 'DEVU-456'] and 'type' = ['issue', 'task']."
    }
    ]
    </Solution>
    ""","""
    'Example: Query: Fetch ’p3’ priority work items that need customer response for ’REV-333’ '
    '<Solution>
    [
    {
        "thought": "First, we need to identify all work items that have a priority level of 'p3' and also require a customer response.",
        "tool_name": "works_list",
        "task": "Use the works_list tool with the arguments: 'issue.priority' = ['p3'], 'ticket_need_response' = true, and 'ticket_rev_org' = ['REV-333']."
    }
    ]
    </Solution>
    ""","""
    'Example: Query: list their high-severity tickets for ’Globex’ user '
    '<Solution>
    [
    {
        "thought": "First, we need to find the user ID for 'Globex' using the search_object_by_name tool.",
        "tool_name": "search_object_by_name",
        "task": "Use the search_object_by_name tool with the argument 'query' = 'Globex'."
    },
    {
        "thought": "Next, we will use the retrieved user ID to list all high-severity tickets created by this user.",
        "tool_name": "works_list",
        "task": "Use the works_list tool with the arguments: 'created_by' = '$$PREV[0]', 'ticket_severity' = ['high'], and 'type' = ['ticket']."
    }
    ]
    </Solution>
    ""","""
    'Example: Query: Assign validated ’TASK-789’ and ’ISSUE-321’ to current user and sync with calendar '
    '<Solution>
    [
    {
        "thought": "First, we need to identify the current user using the who_am_i tool.",
        "tool_name": "who_am_i",
        "task": "Use the who_am_i tool to get the current user's ID."
    },
    {
        "thought": "Next, we need to validate the dependencies for the work items 'TASK-789' and 'ISSUE-321'.",
        "tool_name": "validate_work_dependency",
        "task": "Use the validate_work_dependency tool with the argument 'work_item_ids' = ['TASK-789', 'ISSUE-321']."
    },
    {
        "thought": "Then, we assign the validated work items to the current user.",
        "tool_name": "assign_work_items",
        "task": "Use the assign_work_items tool with the arguments: 'work_item_ids' = ['TASK-789', 'ISSUE-321'] and 'user_id' = '$$PREV[0]'."
    },
    {
        "thought": "Finally, we need to sync the assigned work items with the user's calendar.",
        "tool_name": "sync_work_items_with_calendar",
        "task": "Use the sync_work_items_with_calendar tool with the arguments: 'user_id' = '$$PREV[0]' and 'work_item_ids' = ['TASK-789', 'ISSUE-321']."
    }
]

    </Solution>
    ""","""
    'Example: Query: Summarize tickets from ’support’ channel '
    '<Solution>
    [
    {
        "thought": "First, we need to retrieve all tickets that originate from the 'support' channel.",
        "tool_name": "works_list",
        "task": "Use the works_list tool with the arguments: 'ticket_source_channel' = ['support'] and 'type' = ['ticket']."
    },
    {
        "thought": "Next, we need to summarize the tickets obtained from the previous step.",
        "tool_name": "summarize_objects",
        "task": "Use the summarize_objects tool with the argument 'objects' = '$$PREV[0]'."
    }
    ]
    </Solution>
    ""","""
    'Example: Query: Prioritize tasks for part ’ENH-789’ '
    '<Solution>
    [
    {
        "thought": "First, we need to retrieve all tasks that apply to the part 'ENH-789'.",
        "tool_name": "works_list",
        "task": "Use the works_list tool with the argument 'applies_to_part' = ['ENH-789']."
    },
    {
        "thought": "Next, we need to prioritize the tasks retrieved from the previous step.",
        "tool_name": "prioritize_objects",
        "task": "Use the prioritize_objects tool with the argument 'objects' = '$$PREV[0]'."
    }
]

    </Solution>
    ""","""
    'Example: Query: Fetch ’medium’ severity work items in ’QA Review’ or ’Testing’ '
    '<Solution>
    [
    {
        "thought": "First, we need to retrieve all work items that have a severity level of 'medium' and are currently in the stages 'QA Review' or 'Testing'.",
        "tool_name": "works_list",
        "task": "Use the works_list tool with the arguments: 'ticket_severity' = ['medium'] and 'stage_name' = ['QA Review', 'Testing']."
    }
]
    </Solution>
    ""","""
    'Example: Query: Assign ’TASK-123’ and ’TASK-456’ to ’DEVU-999’ and sync with their calendar '
    '<Solution>
    [
    {
        "thought": "First, we need to assign the work items 'TASK-123' and 'TASK-456' to the user 'DEVU-999'.",
        "tool_name": "assign_work_items",
        "task": "Use the assign_work_items tool with the arguments: 'work_item_ids' = ['TASK-123', 'TASK-456'] and 'user_id' = 'DEVU-999'."
    },
    {
        "thought": "Next, we need to sync the assigned work items with the calendar of 'DEVU-999'.",
        "tool_name": "sync_work_items_with_calendar",
        "task": "Use the sync_work_items_with_calendar tool with the arguments: 'user_id' = 'DEVU-999' and 'work_item_ids' = ['TASK-123', 'TASK-456']."
    }
]

    </Solution>
    ""","""
    'Example: Query: Check dependencies for ’FEAT-123’ and ’BUG-987’ then add to sprint '
    '<Solution>
    [
    {
        "thought": "First, we need to validate the dependencies for the work items 'FEAT-123' and 'BUG-987'.",
        "tool_name": "validate_work_dependency",
        "task": "Use the validate_work_dependency tool with the argument 'work_item_ids' = ['FEAT-123', 'BUG-987']."
    },
    {
        "thought": "Next, we need to retrieve the current sprint ID to which the work items will be added.",
        "tool_name": "get_sprint_id",
        "task": "Use the get_sprint_id tool to obtain the current sprint ID."
    },
    {
        "thought": "Finally, we need to add the validated work items to the current sprint using the obtained sprint ID.",
        "tool_name": "add_work_items_to_sprint",
        "task": "Use the add_work_items_to_sprint tool with the arguments: 'work_ids' = ['FEAT-123', 'BUG-987'] and 'sprint_id' = '$$PREV[1]'."
    }
]

    </Solution>
    """]
default_descriptions = ["who_am_i: The 'who_am_i' tool is a simple API command that returns the identification of the current user, making it useful for determining user context within a system. It does not require any arguments to be passed, as the tool automatically detects and retrieves the relevant user information. The output of this tool is a string containing the user ID, which can be used in subsequent API calls or for logging and tracking purposes.",
 'get_sprint_id: The tool "get\\_sprint\\_id" is designed to retrieve the unique identifier of the currently active sprint in an agile project management system. It does not require any input arguments, as it automatically detects and fetches information about the ongoing sprint. The output of this tool is a string representing the sprint ID, which can be used for various purposes such as tracking progress, generating reports, or integrating with other tools to automate processes. In summary, get\\_sprint\\_id is a valuable tool for developers working on agile projects, providing a quick and easy way to access important sprint information.',
 "works_list: The `works_list` tool retrieves a list of work items based on the provided arguments, making it useful for filtering and managing tasks within a project. Its arguments include various options like `applies_to_part`, `created_by`, `issue_priority`, and others, which are primarily strings (some accepting arrays) or a boolean for `ticket_need_response`, allowing for flexible query customization. The tool returns a list of matching work items in any format, as indicated by the 'any' arg_type in the output description.",
 'summarize_objects: The tool "summarize\\_objects" is designed to consolidate and provide a brief overview of a list of objects, with the summarization logic varying based on the object type. It accepts a single required argument, "objects", which should be an array of any data type. The output of this tool is a single summarized object, which can be of any data type, depending on the input provided. This tool is particularly useful when dealing with large and complex data structures, where it is essential to quickly grasp the key details.',
 'prioritize_objects: The tool `prioritize_objects` is designed to accept a single input of any data type, which can optionally be an array of objects, and returns an array of objects sorted by priority. The priority logic for each object is determined internally based on specific implementation details. This tool is useful when you need to organize a collection of items based on their importance, relevance, or urgency, allowing developers to easily manage their data according to predefined priority rules.',
 'add_work_items_to_sprint: The `add_work_items_to_sprint` tool allows developers to add specified work items to a sprint by providing their unique IDs. It accepts two required arguments: `work_ids`, which is an array of strings representing the IDs of the work items, and `sprint_id`, which is a string representing the ID of the sprint to which the items will be added. The tool returns a boolean value indicating whether the operation was successful or not, making it easy to manage sprint workloads programmatically.',
 'get_similar_work_items: The "get\\_similar\\_work\\_items" tool is designed to find and return a list of work items that bear resemblance to a specified work item. It accepts a single required string argument, "work\\_id", which uniquely identifies the work item in question. Upon successful execution, the tool generates an array of strings as output, representing the IDs of the similar work items found. This tool can be useful for developers in identifying related tasks, tracking progress across connected work items, or performing data analysis on similar tasks within a project.',
 'search_object_by_name: The tool "search\\_object\\_by\\_name" is designed to find an object\'s ID in the system of record based on a provided search string. It accepts a single argument, "query", which is a required string input. The tool returns the ID of the matching object with the highest confidence if there are multiple matches. This functionality is useful for developers looking to quickly and accurately locate specific objects in their system using a simple search query.',
 'create_actionable_tasks_from_text: The "create\\_actionable\\_tasks\\_from\\_text" tool analyzes input text and identifies potential action items, generating a list of tasks as output. It requires a single string argument, \'text\', which serves as the source for task extraction. The tool\'s output is an array of strings, each representing an actionable task derived from the input text, making it useful for organizing and tracking follow-up activities based on textual data, such as emails, meeting minutes, or project documents.']

with open('./tools.json', 'r') as json_file:
    default_tool_string = json_file.read()
    json_file.close()

genai.configure(api_key=API_KEY_GEMINI)
gemini = genai.GenerativeModel('gemini-1.5-flash')
def get_thought_prompt(json_string, descriptions = default_descriptions):
    prompt = f"""You are a dataset generator for generating new data for a different domain from one domain, Your task is to generate more query thought pairs following the format similar to these examples. 
    You may make use of the tools listed below to generate the pairs. You MUST NOT use tools that are not in the list of tools. 
    The tool descriptions are given to you. The tools used in the examples may be different from the list of tools given. BUT your examples should be from the tool list.
    REMEMBER to keep each example wrapped with 'Example:' and <solution>. Keep the examples as diverse as possible and do not output the given examples
    1. First understand each tool their purpose and their domain of usage. Understand the situations where the tools could be used.
    2. First generate few queries that you think could be answered using the tools from tool list. You may use new usernames, ids, org names other than mentioned in the examples.
    3. Then for each of these examples generate a query thought pair. **If you think the query cannot be solved then keep the thoughts as an empty list ie output '[]'**.
    4. Verify your results, ask your self if the thoughts, tools are actually relevant to the query if they are output the query thoought pairs together. 
    ** THE NEW QUERY THOUGHTS PAIRS SHOULD BE USING TOOLS FROM THE TOOLS LIST AND NOT THE EXAMPLES. dON'T USE THE TOOLS FROM EXAMPLES TO GENERATE THE NEW EXAMPLES.**
    **Else keep the thoughts empty list and output 'query' <solutoin> [] </solution>**
    TOOl LIST: 
    {json_string}

    TOOL DESCRIPTIONS of tools used in the examples:
    {"\n".join(descriptions)}

    EXAMPLES:
    {"\n".join(examples)}"""
    return prompt
def get_val_prompt(response, json_string = default_tool_string):
    resp = f"""
    YOU are a dataset validator and Filter. You must check for these rules in the dataset. You are provided with list of tools that are allowed in the dataset.
    1. The query-thought pairs should only use the tools that are provided in the tool list.
    2. The thoughts should be relevant to the query.
    3. The example dataset pairs shouldn't repeat too much.
    TOOLS LIST:
    {json_string} \n 
    query-thought examples DATASET:
    {response}"""
    return resp
def generate_query_thought_examples(out_path = './examples_query_thought.txt', tool_string = default_tool_string, tool_descriptions = default_descriptions, number_of_gen = 50):
    prompt = get_thought_prompt(tool_string,tool_descriptions)
    response = gemini.generate_content(f"""{prompt} \n **Generate {number_of_gen} such query thought pairs, Try not to repeate them or do same as in examples. You need not use the same org, names, ids.. like DEVU, REV YOU must create new names on your own** """)
    resp = get_val_prompt(response.text, tool_string)
    response = gemini.generate_content(f"""{resp} \n Help me with this. mention all the examples that failed the rules and also state no of tools that are passed. the thoughts should be relevant to the query, Output the final list of pairs after making modifications according to the rules, and dont output anything extra 
                                  YOU SHOULD OUTPUT FULL pairs together ie query and solution.
                                  **YOU MUST NOT REMOVE THE  HEADINGS OF " 'Example: Query: ...' and '<Solution> [...] </Solution>** """)
    f = open(out_path , 'w')
    f.write(str(response.text))
    f.close()
