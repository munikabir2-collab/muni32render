import subprocess
import uuid

def run_container(project_path: str, port: int):

    image_name = f"project_{uuid.uuid4().hex[:6]}"

    subprocess.run([
        "docker", "build",
        "-t", image_name,
        project_path
    ])

    subprocess.run([
        "docker", "run", "-d",
        "-p", f"{port}:8000",
        image_name
    ])

    return f"http://localhost:{port}"