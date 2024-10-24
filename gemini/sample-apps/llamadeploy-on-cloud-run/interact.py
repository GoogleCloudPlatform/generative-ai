from flask import Flask, jsonify, request
from llama_deploy import ControlPlaneConfig, LlamaDeployClient

app = Flask(__name__)


@app.route("/", methods=["POST"])
async def run() -> jsonify:
    """Provides a Flask application to interact with the deployed workflow."""

    data = request.get_json()
    workflow_name = data.get("workflow", "my_workflow")  # Default to 'my_workflow'
    print(workflow_name)
    arguments = data.get("args", {})
    print(arguments)

    client = LlamaDeployClient(ControlPlaneConfig())
    print("Client success made")
    print(client.control_plane_config)
    session = client.create_session()

    result = session.run(
        workflow_name, query=arguments["query"], num_steps=arguments["num_steps"]
    )
    print(result)

    print("Completed workflow")
    return jsonify({"status": 200, "answer": result})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)
