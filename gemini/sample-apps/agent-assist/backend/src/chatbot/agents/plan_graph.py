import base64

from flask_socketio import emit

from utils.gemini_text import GeminiText

image_path = "data/app/plan_graph.png"


PROMPT = """
You are a python expert. Your aim is to assist in
plotting an execution plan for a given task.
You need to use networkx and matplotlib to plot the graph.

Given a list of steps to be performed for a task,
you need to plot the graph for the task.
A list of agents with their descriptions has been provided to you.

Important Instructions:
- The labels in the graph should only be from the list of agents
- You do not have to use your own knowledge for any part
- Think step by step for each task
- The output should be a python code enclosed between <PYTHON> </PYTHON>
--------------------------------------

LIST OF AGENTS:
 * 'Search' : for searching anything either in the policy or in the database.
   This also includes things like finding the best policy and comparing policy.
 * 'Send Mail' : this is for sending emails.
 * 'Create \n Meet' : this is for creating or setting up meetings.
 *'Get Email': this is for getting email conversation summaries.
 *'Get \n Appointments' : this is for getting appointments.
 * 'Sales Pitch' : this is for drafting/creating a sales pitch.
 * 'Chat' : this is for chatting with the customer.
   This is always used when the code invokes the fallback component.

 --------------------------------------

 Some examples:

 STEPS:
 Step 1:
  Compare Homeshield and My Asset for accidental fire damage coverage.
Step 2:
 Send the comparison to channit.
Step 3:
 Set up a meeting with him tomorrow at 6pm.
Step 4:
 Show the conversation summary with him.
Step 5:
 Show the appointments for tomorrow.

CODE:
answer = search(query="Compare Homeshield and My Asset for accidental fire
    damage coverage",
    policy_list=["Home Shield", "My Asset Home Insurance"])
subject, body = generate_email(prompt=answer)
result = send_email(email_id="channitdak@gmail.com", subject=subject,
    body=body)
schedule_calendar_event(date="06/02/2024", start_time= "18:00",
    end_time= "19:00", participants=["channitdak@gmail.com"] )
result = get_email_conversation_summary("channitdak@gmail.com")
result = get_calendar_events(dates=["06/02/2024"])

OUTPUT:
<PYTHON>
import matplotlib.pyplot as plt
import networkx as nx

# Set the matplotlib backend to 'agg'
plt.switch_backend('agg')

# Create a directed graph
G = nx.DiGraph()

# Define steps
steps = {{
    'Step1': 'Search',
    'Step2': 'Send Mail',
    'Step3': 'Create \\n Meet',
    'Step4': 'Get Email',
    'Step5': 'Get \\n Appointments',
}}

# Add nodes and edges
for step, description in steps.items():
    G.add_node(description)
    # print(description)

edges = [(steps['Step1'], steps['Step2']),
(steps['Step2'], steps['Step3']),
(steps['Step3'], steps['Step4']),
(steps['Step4'], steps['Step5'])]
G.add_edges_from(edges)

# Draw the graph
n = len(list(steps.keys()))
pos={{}}
for i, node in enumerate(steps.keys()):
    pos[steps[node]] = (i, -i)

fig, ax = plt.subplots()
node_labels = nx.get_edge_attributes(G, 'label')
nx.draw(G, pos, with_labels=True, node_size=3000,
node_color='#1976d2', font_size=8, font_color='black')
nx.draw_networkx_labels(G, pos, labels=node_labels,
font_size=8, font_color='black', font_weight='bold',
verticalalignment='center', horizontalalignment='center')
plt.savefig('data/app/plan_graph.png')
plt.close(fig)
</PYTHON>

--------------------------------------

STEPS:
{steps}

CODE:
{code}

OUTPUT:
"""


def generate_plan_graph(steps: str, code: str) -> None:
    """
    Generates a plan graph for the given steps and code.

    Args:
        steps (str): The steps to be performed for the task.
        code(str): The code to be executed to generate the plan graph.

    """
    print("generate plan graph")
    gt = GeminiText()
    response = gt.generate_response(PROMPT.format(steps=steps, code=code))
    print("response", response)

    matplotlib_code = response.split("<PYTHON>")[1].split("</PYTHON>")[0]

    print("mat", matplotlib_code)

    d = {}
    exec(matplotlib_code, globals(), d)

    with open(image_path, "rb") as image_file:
        encoded_image = base64.b64encode(image_file.read()).decode("utf-8")

    emit("chat", ["Generating..."])
    emit("chat", [{"intent": "Plan Graph", "data": encoded_image}])

    # print('tikz', d['tikz_code'])

    # return d['tikz_code']
