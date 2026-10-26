"""First-run setup and paths for the lead-gen workflow on this computer.

The repository holds only the method (skills, agents, scripts, templates). Each computer keeps its own data folder:
    <data folder>/
    ├── LeadGen_Memory/   country and product profiles, keyword files (started from templates/LeadGen_Memory)
    ├── Database/         lead workbooks and company registries
    └── Queue/            registry-compile's write queue, applied records and backups
Its location is saved in a per-user settings file outside the repository (%APPDATA%\\MindtracLeadGen\\config.json on
Windows, ~/.config/mindtrac-leadgen/config.json elsewhere). LEADGEN_ROOT overrides it (tests, cloud runners).

    python LeadGen_Tools/leadgen_setup.py status             what is set up (exit 0 = ready, 2 = not set up)
    python LeadGen_Tools/leadgen_setup.py init --data-root <folder>   create / connect the data folder
    python LeadGen_Tools/leadgen_setup.py init               same, asking for the folder
    python LeadGen_Tools/leadgen_setup.py keys               store the Hunter / Apollo keys (hidden input; run it
                                                             yourself in a terminal, never through a chat)
    python LeadGen_Tools/leadgen_setup.py keys --delete HUNTER_API_KEY
    python LeadGen_Tools/leadgen_setup.py where              print the data folder only"""
import argparse, json, os, shutil, sys

import leadgen_secrets as secrets

TOOLS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TOOLS)
TEMPLATES = os.path.join(REPO, "templates", "LeadGen_Memory")
SUBFOLDERS = ("LeadGen_Memory", "Database", "Queue")
DEFAULT_DATA = os.path.join(os.path.expanduser("~"), "Documents", "Mindtrac-LeadGen-Data")

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


def config_file():
    return os.environ.get("LEADGEN_CONFIG") or os.path.join(secrets.app_dir(), "config.json")


def read_config():
    try:
        return json.load(open(config_file(), encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def data_root(required=True):
    """The data folder: LEADGEN_ROOT, else the saved setting. required=True stops with the setup command when unset."""
    root = os.environ.get("LEADGEN_ROOT") or read_config().get("data_root")
    if root and os.path.isdir(root):
        return os.path.abspath(root)
    if not required:
        return None
    why = f"the saved data folder {root} does not exist" if root else "no data folder is set on this computer"
    sys.exit(f"LEAD-GEN NOT SET UP: {why}. Ask the user where to keep the lead-gen data, then run:\n"
             f'  python "{os.path.join(TOOLS, "leadgen_setup.py")}" init --data-root "<folder>"')


def memory_dir(root=None):
    return os.environ.get("LEADGEN_MEMORY") or os.path.join(root or data_root(), "LeadGen_Memory")


def queue_root(root=None):
    return os.path.join(root or data_root(), "Queue")


def _copy_templates(memory):
    """Copy the templates into LeadGen_Memory without overwriting anything already there. -> files copied."""
    copied = []
    for d, _, files in os.walk(TEMPLATES):
        for f in files:
            src = os.path.join(d, f)
            dst = os.path.join(memory, os.path.relpath(src, TEMPLATES))
            if not os.path.exists(dst):
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
                copied.append(os.path.relpath(dst, memory))
    return copied


def init(root):
    root = os.path.abspath(os.path.expanduser(root.strip().strip('"')))
    try:
        inside = os.path.commonpath([root, REPO]) == REPO
    except ValueError:  # different drives
        inside = False
    if inside:
        sys.exit(f"Choose a data folder outside the repository ({REPO}), so lead data is never committed to GitHub.")
    for sub in SUBFOLDERS:
        os.makedirs(os.path.join(root, sub), exist_ok=True)
    os.makedirs(os.path.join(root, "LeadGen_Memory", "countries"), exist_ok=True)
    os.makedirs(os.path.join(root, "LeadGen_Memory", "products"), exist_ok=True)
    copied = _copy_templates(os.path.join(root, "LeadGen_Memory"))
    os.makedirs(os.path.dirname(config_file()), exist_ok=True)
    cfg = read_config()
    cfg["data_root"] = root
    json.dump(cfg, open(config_file(), "w", encoding="utf-8"), indent=2)
    print(f"Data folder: {root}")
    print(f"  created/kept: {', '.join(SUBFOLDERS)}; templates copied: {len(copied)}")
    print(f"Saved in: {config_file()}")


def status(as_json=False):
    root = data_root(required=False)
    keys = {n: secrets.stored(n) for n in secrets.KEY_NAMES}
    out = {"repo": REPO, "config_file": config_file(), "data_root": root,
           "folders": {s: bool(root) and os.path.isdir(os.path.join(root, s)) for s in SUBFOLDERS},
           "key_store": secrets.backend(), "keys": {n: (v or "missing") for n, v in keys.items()}}
    ready = bool(root) and all(out["folders"].values())
    out["ready"] = ready
    if as_json:
        print(json.dumps(out, indent=2))
    else:
        print(f"Repository:   {REPO}")
        print(f"Data folder:  {root or 'NOT SET'}")
        if root:
            print("  " + ", ".join(f"{s} {'ok' if ok else 'MISSING'}" for s, ok in out["folders"].items()))
        print(f"Key store:    {out['key_store'] or 'none (pip install keyring)'}")
        for n, v in keys.items():
            print(f"  {n}: {'set (' + v + ')' if v else 'missing'}")
        if not ready:
            print("\nNOT SET UP: run `python LeadGen_Tools/leadgen_setup.py init` (asks for the data folder).")
        if not all(keys.values()):
            print("Keys missing: the user runs `python LeadGen_Tools/leadgen_setup.py keys` in their own terminal. "
                  "Until then enrichment runs with --skip-hunter / without Apollo and the run report says so.")
    return 0 if ready else 2


def keys(names, delete=None):
    if delete:
        secrets.delete(delete)
        print(f"{delete} removed from this computer's key store.")
        return
    if not sys.stdin.isatty():
        sys.exit("Keys are typed only by the user in an interactive terminal (hidden input). "
                 "Open a terminal yourself and run:  python LeadGen_Tools/leadgen_setup.py keys")
    import getpass
    print(f"Keys are stored in: {secrets.backend() or 'NO SAFE STORE'} (never in the repository).")
    for n in names:
        have = secrets.stored(n)
        v = getpass.getpass(f"{n}{' (Enter keeps the current one)' if have else ''}: ")
        if not v.strip():
            print(f"  {n}: {'kept' if have else 'skipped'}")
            continue
        where = secrets.put(n, v)
        print(f"  {n}: saved ({where})")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd")
    s = sub.add_parser("status")
    s.add_argument("--json", action="store_true")
    i = sub.add_parser("init")
    i.add_argument("--data-root")
    k = sub.add_parser("keys")
    k.add_argument("--name", action="append", choices=secrets.KEY_NAMES)
    k.add_argument("--delete", choices=secrets.KEY_NAMES)
    sub.add_parser("where")
    a = p.parse_args()
    if a.cmd == "init":
        root = a.data_root
        if not root:
            if not sys.stdin.isatty():
                sys.exit("init needs --data-root <folder> when not run in a terminal.")
            cur = data_root(required=False)
            root = input(f"Data folder for lead-gen [{cur or DEFAULT_DATA}]: ").strip() or cur or DEFAULT_DATA
        init(root)
        sys.exit(status())
    elif a.cmd == "keys":
        keys(a.name or list(secrets.KEY_NAMES), a.delete)
    elif a.cmd == "where":
        print(data_root())
    else:
        sys.exit(status(getattr(a, "json", False)))
