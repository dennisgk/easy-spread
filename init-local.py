#!/usr/bin/env python3
import argparse
import os
import re
import stat
import subprocess
import sys
from pathlib import Path
import secrets
import urllib.request

REPO = "https://github.com/quadratichq/quadratic-selfhost.git"
SELF_HOSTING_URI = "https://selfhost.quadratichq.com/"
INVALID_LICENSE_KEY = "Invalid license key."

BASE_DIR = Path.cwd()
REPO_DIR = BASE_DIR / "quadratic-selfhost"

UUID_REGEX = re.compile(
    r"^[0-9a-fA-F]{8}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{12}$"
)

def download_env_local():
    url = "https://raw.githubusercontent.com/quadratichq/quadratic-selfhost/refs/heads/main/.env.local"
    print("Downloading .env.local from GitHub...")
    urllib.request.urlretrieve(url, ".env.local")
    print("Saved .env.local")

def get_license_key_interactive() -> str:
    prompt = (
        f"Enter your license key "
        f"(Get one for free instantly at {SELF_HOSTING_URI}): "
    )
    user_input = input(prompt).strip()

    if UUID_REGEX.match(user_input):
        return user_input
    print(INVALID_LICENSE_KEY)
    sys.exit(1)


def checkout_repo():
    if not REPO_DIR.exists():
        print(f"Cloning {REPO} into {REPO_DIR}...")
        subprocess.run(["git", "clone", REPO], check=True, cwd=BASE_DIR)
    else:
        print(f"Repository directory already exists at {REPO_DIR}, skipping clone.")

    os.chdir(REPO_DIR)
    subprocess.run(["git", "checkout"], check=True)


def load_env_file(env_path: Path) -> dict:
    env = {}
    if not env_path.exists():
        return env

    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        env[key] = value
    return env


def parse_profile(env_path: Path) -> str:
    env = load_env_file(env_path)

    variables = [
        "DATABASE_IN_DOCKER_COMPOSE",
        "PUBSUB_IN_DOCKER_COMPOSE",
        "CADDY_IN_DOCKER_COMPOSE",
        "ORY_IN_DOCKER_COMPOSE",
        "QUADRATIC_CLIENT_IN_DOCKER_COMPOSE",
        "QUADRATIC_API_IN_DOCKER_COMPOSE",
        "QUADRATIC_MULTIPLAYER_IN_DOCKER_COMPOSE",
        "QUADRATIC_FILES_IN_DOCKER_COMPOSE",
        "QUADRATIC_CLOUD_CONTROLLER_IN_DOCKER_COMPOSE",
        "QUADRATIC_CONNECTION_IN_DOCKER_COMPOSE",
        "QUADRATIC_CONNECTION_DB_IN_DOCKER_COMPOSE",
        "QUADRATIC_CONNECTION_DB_POSTGRES_IN_DOCKER_COMPOSE",
        "QUADRATIC_CONNECTION_DB_MYSQL_IN_DOCKER_COMPOSE",
        "QUADRATIC_CONNECTION_DB_MSSQL_IN_DOCKER_COMPOSE",
        "QUADRATIC_CONNECTION_DB_POSTGRES_SSH_IN_DOCKER_COMPOSE",
        "QUADRATIC_CONNECTION_DB_MYSQL_SSH_IN_DOCKER_COMPOSE",
        "QUADRATIC_CONNECTION_DB_MSSQL_SSH_IN_DOCKER_COMPOSE",
    ]

    values = []
    for var_name in variables:
        raw_val = env.get(var_name, "")
        if raw_val.lower() == "true":
            stripped = var_name.replace("_IN_DOCKER_COMPOSE", "")
            lowered = stripped.lower()
            values.append(f"--profile {lowered}")

    return " ".join(values)

def normalize_line_endings(repo_dir: Path) -> None:
    # Force LF endings for all shell scripts in the repo
    for path in repo_dir.rglob("*.sh"):
        if path.is_file():
            data = path.read_bytes()
            new = data.replace(b"\r\n", b"\n")
            if new != data:
                path.write_bytes(new)
                print(f"Normalized line endings to LF in {path}")

def generate_random_encryption_key() -> str:
    return secrets.token_hex(32)

def build_custom_quadratic_api():
    # Paths
    custom_dir = Path("custom")
    dockerfile_path = custom_dir / "Dockerfile"
    compose_path = REPO_DIR / "docker-compose.yml"
    backup_path = compose_path.with_suffix(".yml.bak")

    # 1) Validate paths
    if not custom_dir.is_dir():
        raise FileNotFoundError("The directory 'custom/' does not exist.")

    if not dockerfile_path.is_file():
        raise FileNotFoundError("custom/Dockerfile does not exist.")

    print(f"[+] Using Dockerfile at: {dockerfile_path}")

    # 2) Build Docker image
    print("[+] Building Docker image 'my-quadratic-api'...")
    subprocess.check_call(["docker", "build", "-t", "my-quadratic-api", str(custom_dir)])

    # 3) Update docker-compose.yml
    if not compose_path.is_file():
        raise FileNotFoundError("docker-compose.yml not found in current directory.")

    original = compose_path.read_text(encoding="utf-8")

    old_line = "image: ${ECR_URL}/quadratic-api:${IMAGE_TAG}"
    new_line = "image: my-quadratic-api"

    if old_line not in original:
        print("[!] WARNING: Expected image line not found in docker-compose.yml.")
        return

    updated = original.replace(old_line, new_line)

    # Backup
    backup_path.write_text(original, encoding="utf-8")

    # Write updated version
    compose_path.write_text(updated, encoding="utf-8")

    print(f"[+] docker-compose.yml updated (backup saved as {backup_path})")
    print("[✓] Done!")

def main():
    parser = argparse.ArgumentParser(
        description="Self-hosting initialization for Quadratic (Python version)"
    )
    parser.add_argument(
        "license_key",
        nargs="?",
        help="License key (optional, otherwise read from file or prompt)",
    )
    args = parser.parse_args()

    # 1) Determine LICENSE_KEY
    license_key = ""
    existing_license_file = REPO_DIR / "LICENSE_KEY"

    if existing_license_file.exists():
        license_key = existing_license_file.read_text().strip()
        print(f"Using existing license key from {existing_license_file}")
    elif args.license_key:
        if not UUID_REGEX.match(args.license_key.strip()):
            print(INVALID_LICENSE_KEY)
            sys.exit(1)
        license_key = args.license_key.strip()
        print("Using license key provided on command line.")
    else:
        license_key = get_license_key_interactive()

    # 2) Retrieve code from GitHub
    checkout_repo()  # cwd is now REPO_DIR
    normalize_line_endings(REPO_DIR)

    # 3) Copy local config files
    kratos_local = Path("docker/ory-auth/config/kratos.local.yml")
    kratos_target = Path("docker/ory-auth/config/kratos.yml")
    if kratos_local.exists():
        kratos_target.write_text(kratos_local.read_text())
        print(f"Copied {kratos_local} -> {kratos_target}")
    else:
        print(f"WARNING: {kratos_local} does not exist.")

    download_env_local()

    env_local = Path(".env.local")
    env_file = Path(".env")
    if env_local.exists():
        env_file.write_text(env_local.read_text())
        print(f"Copied {env_local} -> {env_file}")
    else:
        print(f"WARNING: {env_local} does not exist.")

    # 4) Write LICENSE_KEY
    license_path = Path("LICENSE_KEY")
    license_path.write_text(license_key + "\n")
    print(f"Wrote LICENSE_KEY to {license_path}")

    # 5) PROFILE
    profile_str = parse_profile(env_file)
    profile_path = Path("PROFILE")
    profile_path.write_text(profile_str + "\n")
    print(f"Wrote PROFILE: {profile_str!r}")

    # 6) ENCRYPTION_KEY
    encryption_key = generate_random_encryption_key()
    encryption_path = Path("ENCRYPTION_KEY")
    encryption_path.write_text(encryption_key + "\n")
    print(f"Wrote ENCRYPTION_KEY ({len(encryption_key)} hex chars).")

    # 7) Replace placeholders in .env
    if env_file.exists():
        content = env_file.read_text()
        content = content.replace("#LICENSE_KEY#", license_key)
        content = content.replace("#ENCRYPTION_KEY#", encryption_key)
        env_file.write_text(content)
        print("Replaced #LICENSE_KEY# and #ENCRYPTION_KEY# in .env")
    else:
        print("WARNING: .env not found; skipping placeholder replacement.")

    # 8) chmod +x docker/postgres/scripts/init.sh
    init_sh = Path("docker/postgres/scripts/init.sh")
    if init_sh.exists():
        st = init_sh.stat()
        init_sh.chmod(st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        print(f"Made {init_sh} executable.")
    else:
        print(f"WARNING: {init_sh} not found; skipping chmod.")

    # 9) Build custom api
    os.chdir(BASE_DIR)
    build_custom_quadratic_api()

    # 10) Call start.py instead of sh start.sh
    os.chdir(REPO_DIR)
    start_py = Path("../start.py")
    if start_py.exists():
        print("Running start.py...")
        subprocess.run([sys.executable, str(start_py)], check=True)
    else:
        print("WARNING: start.py not found; not starting services.")
    os.chdir(BASE_DIR)


if __name__ == "__main__":
    main()
