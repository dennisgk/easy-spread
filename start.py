#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path.cwd()
ENV_PATH = BASE_DIR / ".env"
PROFILE_PATH = BASE_DIR / "PROFILE"


def load_env_into_os(env_path: Path):
    """
    Equivalent to:
      set -a
      . ./.env
      set +a

    i.e., load .env into the process environment so docker compose sees it.
    """
    if not env_path.exists():
        print(f"WARNING: {env_path} does not exist, skipping env load.")
        return

    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ[key] = value


def read_profile_args(profile_path: Path) -> list[str]:
    """
    PROFILE file contains something like:
      --profile database --profile quadratic_client ...
    We split that into arg tokens for docker compose.
    """
    if not profile_path.exists():
        print(f"WARNING: {profile_path} does not exist, using no profiles.")
        return []

    raw = profile_path.read_text().strip()
    if not raw:
        return []
    return raw.split()


def main():
    # 1) Read PROFILE
    profile_args = read_profile_args(PROFILE_PATH)

    # 2) Load .env into environment
    load_env_into_os(ENV_PATH)

    # Ensure we have ECR_URL and IMAGE_TAG for image names
    ecr_url = os.environ.get("ECR_URL")
    image_tag = os.environ.get("IMAGE_TAG")

    if not ecr_url or not image_tag:
        print("ERROR: ECR_URL and/or IMAGE_TAG missing from environment/.env.")
        print("       They are required to build cloud controller/worker image names.")
        sys.exit(1)

    # 3) docker compose ... down --volumes --remove-orphans
    print("Stopping existing containers (docker compose down)...")
    down_cmd = ["docker", "compose"] + profile_args + [
        "down", "--volumes", "--remove-orphans"
    ]
    subprocess.run(down_cmd, check=False)  # don't hard fail if nothing is running

    # 4) Check cloud controller/workers
    cloud_controller_image = f"{ecr_url}/quadratic-cloud-controller:{image_tag}"
    cloud_worker_image = f"{ecr_url}/quadratic-cloud-worker:{image_tag}"

    print(f"Pulling cloud controller image: {cloud_controller_image}")
    pull_controller = subprocess.run(
        ["docker", "pull", cloud_controller_image],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    if pull_controller.returncode != 0:
        print(
            "Cloud controller image not available, using 'hello-world' as fallback "
            f"tagged as {cloud_controller_image}"
        )
        subprocess.run(["docker", "pull", "hello-world"], check=True)
        subprocess.run(["docker", "tag", "hello-world", cloud_controller_image], check=True)
    else:
        print(f"Cloud controller image pulled successfully. Pulling worker image: {cloud_worker_image}")
        subprocess.run(["docker", "pull", cloud_worker_image], check=True)

    # 5) docker compose ... up -d
    print("Starting services (docker compose up -d)...")
    up_cmd = ["docker", "compose"] + profile_args + ["up", "-d"]
    subprocess.run(up_cmd, check=True)

    # 6) docker builder prune -af
    print("Pruning Docker builder cache (docker builder prune -af)...")
    subprocess.run(["docker", "builder", "prune", "-af"], check=False)

    print("Done.")


if __name__ == "__main__":
    main()
