import subprocess
import sys
from pathlib import Path

VENV_DIR = ".venv"
ALEMBIC_DIR = "alembic"
ALEMBIC_INI = "alembic.ini"
DB_URL = "sqlite:///DesignSouq.db"
MIGRATION_MSG = "Add updated_at to projects"


def run(cmd: list[str], cwd: Path, label: str) -> None:
    print(f"[STEP] {label}: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ERROR] {label} failed")
        if result.stdout.strip():
            print("[STDOUT]")
            print(result.stdout.strip())
        if result.stderr.strip():
            print("[STDERR]")
            print(result.stderr.strip())
        raise SystemExit(result.returncode)

    print(f"[OK] {label}")
    if result.stdout.strip():
        print(result.stdout.strip())


def ensure_venv(root: Path) -> Path:
    venv_path = root / VENV_DIR
    python_exe = venv_path / "Scripts" / "python.exe"

    if venv_path.exists() and python_exe.exists():
        print(f"[INFO] Virtual environment already exists: {venv_path}")
        return python_exe

    print(f"[INFO] Creating virtual environment at: {venv_path}")
    run([sys.executable, "-m", "venv", VENV_DIR], root, "Create virtual environment")

    if not python_exe.exists():
        print(f"[ERROR] Venv Python executable not found: {python_exe}")
        raise SystemExit(1)

    print(f"[OK] Virtual environment ready: {venv_path}")
    return python_exe


def get_venv_executables(root: Path) -> tuple[Path, Path, Path]:
    scripts_dir = root / VENV_DIR / "Scripts"
    python_exe = scripts_dir / "python.exe"
    pip_exe = scripts_dir / "pip.exe"
    alembic_exe = scripts_dir / "alembic.exe"

    if not python_exe.exists():
        print(f"[ERROR] Missing venv python: {python_exe}")
        raise SystemExit(1)

    return python_exe, pip_exe, alembic_exe


def upgrade_pip(python_exe: Path, root: Path) -> None:
    run([str(python_exe), "-m", "pip", "install", "--upgrade", "pip"], root, "Upgrade pip")


def install_packages(python_exe: Path, root: Path) -> None:
    run(
        [str(python_exe), "-m", "pip", "install", "alembic", "SQLAlchemy", "Pillow"],
        root,
        "Install required packages",
    )


def init_alembic_if_needed(alembic_exe: Path, root: Path) -> None:
    if (root / ALEMBIC_DIR).exists():
        print("[INFO] Alembic already initialized")
        return

    print("[INFO] Alembic not found, initializing...")
    run([str(alembic_exe), "init", ALEMBIC_DIR], root, "Initialize Alembic")


def update_alembic_ini(root: Path) -> None:
    ini_path = root / ALEMBIC_INI
    if not ini_path.exists():
        print(f"[ERROR] {ALEMBIC_INI} not found in project root")
        raise SystemExit(1)

    print(f"[INFO] Updating {ALEMBIC_INI} with database URL: {DB_URL}")
    lines = ini_path.read_text(encoding="utf-8").splitlines()
    updated = False

    for i, line in enumerate(lines):
        if line.strip().startswith("sqlalchemy.url ="):
            lines[i] = f"sqlalchemy.url = {DB_URL}"
            updated = True
            break

    if not updated:
        lines.append(f"sqlalchemy.url = {DB_URL}")

    ini_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("[OK] alembic.ini updated")


def patch_env_py(root: Path) -> None:
    env_path = root / ALEMBIC_DIR / "env.py"
    if not env_path.exists():
        print(f"[ERROR] alembic env file not found: {env_path}")
        raise SystemExit(1)

    print("[INFO] Patching alembic/env.py for SQLAlchemy metadata autogenerate")
    text = env_path.read_text(encoding="utf-8")

    if "from app.models import Base" not in text:
        text = text.replace(
            "from alembic import context",
            "from alembic import context\nfrom app.models import Base",
        )

    if "target_metadata = Base.metadata" not in text:
        text = text.replace("target_metadata = None", "target_metadata = Base.metadata")

    env_path.write_text(text, encoding="utf-8")
    print("[OK] alembic/env.py patched")


def create_migration(alembic_exe: Path, root: Path, message: str) -> None:
    run(
        [str(alembic_exe), "revision", "--autogenerate", "-m", message],
        root,
        "Create migration",
    )


def apply_migration(alembic_exe: Path, root: Path) -> None:
    run([str(alembic_exe), "upgrade", "head"], root, "Apply migration")


def main() -> None:
    root = Path(__file__).resolve().parent
    print(f"[START] Project root: {root}")

    ensure_venv(root)
    python_exe, _pip_exe, alembic_exe = get_venv_executables(root)

    # Windows note: instead of shell activation, commands are run with venv executables directly.
    print(f"[INFO] Using venv Python: {python_exe}")

    upgrade_pip(python_exe, root)
    install_packages(python_exe, root)

    if not alembic_exe.exists():
        print(f"[ERROR] alembic executable not found: {alembic_exe}")
        print("[HINT] Dependency installation may have failed.")
        raise SystemExit(1)

    init_alembic_if_needed(alembic_exe, root)
    update_alembic_ini(root)
    patch_env_py(root)
    create_migration(alembic_exe, root, MIGRATION_MSG)
    apply_migration(alembic_exe, root)

    print("[DONE] Full Alembic setup and migration completed successfully")


if __name__ == "__main__":
    main()
