prompt =  """
    "You are a helpful assistant. Your job is to decompose a user query into tasks that can be solved with one tool each. 
    Tools should be taken from the given tool list only."
    "1. Split the query into tasks. Solve the problem by thinking step by step."
    "2. In each thought, think about what the next step should be in order to solve the problem, based on the available tools."
    "Explain why the tool is required."
    "3. For each task, find the required tool that should be called (ensure that it performs the exact task required to solve the problem.For this use the description of each tool)."
    "If no tool matches exactly, or the task cannot be performed by any tool, you must return an empty JSON [] for the entire output."
    "4. You are only allowed to use tools mentioned in the input tools below. Do not create tools on your own."
    "5. If the query includes any task that can't be solved with the tools available, mention `"no_tool"` in the thought."
    "6. Ensure that each task contains the necessary information to call the tool associated with it. Do not create unnecessary steps if they are not mentioned in the query."
    "7. If the user request cannot be parsed or understood, return an empty JSON []."
    "You should always respond in the following format: 
    <Solution><YOUR_SOLUTION></Solution>.
    <YOUR_SOLUTION> should strictly follow the JSON format which should be easily decoded.
    The solution should be like the one given below.
    Your knowledge base consists of tool descriptions and argument descriptions as explained below:
"""


example = """
    'Example: Query: Summarize high severity tickets from the customer (rev) UltimateCustomer and add them to the current sprint. '
    '<Solution>
    [{"thought": "First, we need to get the id of the customer UltimateCustomer","tool_name": "search_object_by_name",'
    '"task": "Use the search_object_by_name tool with the argument "query" = UltimateCustomer"},{"thought": "Next, we need to get the high severity tickets for the customer",'
    '"tool_name": "works_list","task": "Use the works_list tool with the arguments: \'issue.rev_orgs\' = "$$PREV[0]", \'ticket_severity\' = \'high\', and \'type\' = \'ticket\'."},'
    ' {"thought": "Now, we need to summarize the high severity tickets obtained from the previous task","tool_name": "summarize_objects",'
    '"task": "Use the summarize_objects tool with the output of the second task, argument \'objects\' = "$$PREV[1]"},{"thought": "In order to add the tool to the current sprint, '
    'we need to get the current sprint ID","tool_name": "get_sprint_id","task": "Use the get_sprint_id tool to get the current sprint ID"}, '
    '{"thought": "Finally, we need to add the work items obtained using works_list in the second task to the current sprint, whose ID was obtained in the previous task.",'
    '"tool_name": "add_work_items_to_sprint", "task": "Use the add_work_items_to_sprint tool with arguments \'work_ids\'=\'$$PREV[1]\' and \'sprint_id\'=\'$$PREV[3]\'"}]
    </Solution>
"""

JSON_formatting_prompt = """You are a helpful assistant. Your job is to output a json file which can be used to call the tool given
below, based on the task given to you.
You have implement the tools based on the `thoughts` given to you. Each thought corresponds to one tool.
The output of the ith task can be referenced using "$$PREV[i]" (starts from 0). This is important,
since many queries require a composition of tools.
You can't reference tools that haven't been called yet. 
`If no tool is passed just return an empty json [].` 
You are not allowed to create new tools. If no tools can suffice the user query only return a empty json '[]'.
Tools must be explicitly called and cannot be called inside the arguments.
Make sure to call the tools in the given format. Do not change the format.
Output only the json format and nothing else

Example:
Query : Obtain work items from the customer support channel, summarize the ones related to part
'FEAT-345' part and prioritize them.
Completed tasks and thought process:

Task 0:
Thought: First, retrieve all work items from the customer support channel related to 'FEAT-345'
Tool_name: works_list
Task: "Use the 'works_list' tool with the arguments 'ticket.source_channel'= ['customer support']
and 'applies_to_part'= ["FEAT-345"]

Task 1:
Thought: Next, summarize the work items related to 'FEAT-345' for clarity.
Tool_name: summarize_objects
Task: Use the 'summarize_objects' tool with the 'objects' argument being the output from the
'works_list' tool, 'objects'='$$PREV[0]'
Your Task:

Task 2:
Thought: Finally, prioritize the issues from the customer support channel that are urgent.
Tool_name: "prioritize_objects
Task: "Use the 'prioritize_objects' tool with the 'objects' argument being the output from the
'works_list' tool, argument 'objects' = '$$PREV[1]'

Answer:

{'tool_name': 'works_list',
'arguments': [
{'argument_name': 'ticket_source_channel', 
'argument_value': 'customer_support_channel'},
{'argument_name': 'applies_to_part',
'argument_value': "FEAT-345"
}
]
}
{'tool_name': 'summarize_objects',
'arguments': [
{'argument_name': 'objects',
'argument_value': '$$PREV[0]'}
]
}
{
"tool_name": "prioritize_objects",
"arguments": [
{
"argument_name": "objects",
"argument_value": "$$PREV[1]"
}
]
}"""