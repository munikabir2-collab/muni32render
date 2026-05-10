import docker
import os


client = docker.from_env()

PORT_BASE = 9000


def build_and_run(project_path: str, project_name: str, project_id: int):
    """
    Build Docker image and run container for a project (Vercel-style deploy)
    """

    # ----------------------------
    # 1. Create unique image tag
    # ----------------------------
    image_tag = f"{project_name}:{project_id}"

    # ----------------------------
    # 2. Build Docker image
    # ----------------------------
    try:
        image, logs = client.images.build(
            path=project_path,
            tag=image_tag
        )

        # Print build logs (important for debugging)
        for log in logs:
            if "stream" in log:
                print(log["stream"].strip())

    except Exception as e:
        print("❌ Docker build failed:", str(e))
        raise e

    # ----------------------------
    # 3. Assign unique port
    # ----------------------------
    port = PORT_BASE + int(project_id)

    # ----------------------------
    # 4. Stop old container if exists
    # ----------------------------
    container_name = f"project_{project_id}"

    try:
        old = client.containers.get(container_name)
        old.stop()
        old.remove()
        print(f"♻️ Removed old container: {container_name}")
    except:
        pass  # no old container

    # ----------------------------
    # 5. Run new container
    # ----------------------------
    try:
        container = client.containers.run(
            image_tag,
            detach=True,
            ports={"8000/tcp": port},
            name=container_name,
            restart_policy={"Name": "always"}
        )

    except Exception as e:
        print("❌ Container start failed:", str(e))
        raise e

    # ----------------------------
    # 6. Return deploy result
    # ----------------------------
    return {
        "container_id": container.id,
        "url": f"http://localhost:{port}"
    }