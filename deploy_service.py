import subprocess
import random

def deploy_project(project_path, project_name, project_id):
    try:
        # 🔢 Random port (3000–9000)
        port = random.randint(3000, 9000)

        image_name = f"{project_name.lower()}-{project_id}"
        container_name = f"{project_name.lower()}-container-{project_id}"

        # 🧹 Remove old container if exists
        subprocess.run(
            ["docker", "rm", "-f", container_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # 🛠️ Build Docker image
        build = subprocess.run(
            ["docker", "build", "-t", image_name, project_path],
            capture_output=True,
            text=True
        )

        if build.returncode != 0:
            return {
                "error": build.stderr
            }

        # 🚀 Run Docker container
        run = subprocess.run(
            [
                "docker", "run", "-d",
                "-p", f"{port}:8000",
                "--name", container_name,
                image_name
            ],
            capture_output=True,
            text=True
        )

        if run.returncode != 0:
            return {
                "error": run.stderr
            }

        # 🌐 Local URL
        url = f"http://localhost:{port}"

        return {
            "url": url
        }

    except Exception as e:
        return {
            "error": str(e)
        }



import asyncio

async def send_log(message):
    from main import clients

    for client in clients:
        await client.send_text(message)
                