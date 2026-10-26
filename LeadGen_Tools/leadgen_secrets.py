"""API keys (Hunter, Apollo) kept secret to this computer and this Windows/macOS/Linux user.

Keys are never written into the repository, a .env file or a run folder. They are stored, in this order of preference:
  1. the system keychain through the `keyring` package (Windows Credential Manager, macOS Keychain, Secret Service);
  2. on Windows without `keyring`: a file in the user's app-data folder encrypted with Windows DPAPI (CryptProtectData),
     which only this Windows user on this computer can decrypt.
An environment variable of the same name (HUNTER_API_KEY, APOLLO_API_KEY) still wins when set, e.g. in a cloud runner.

Keys are entered only by the user, in their own terminal, with hidden input:
    python LeadGen_Tools/leadgen_setup.py keys
Never paste a key into a chat, a file in this repository, or a command line."""
import base64, json, os, sys

SERVICE = "mindtrac-leadgen"
KEY_NAMES = ("HUNTER_API_KEY", "APOLLO_API_KEY")


def app_dir():
    """Per-user settings folder, outside every repository: %APPDATA%\\MindtracLeadGen or ~/.config/mindtrac-leadgen."""
    if os.environ.get("LEADGEN_APP_DIR"):
        return os.environ["LEADGEN_APP_DIR"]
    if os.name == "nt":
        return os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "MindtracLeadGen")
    return os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"), "mindtrac-leadgen")


def _keyring():
    if os.environ.get("LEADGEN_NO_KEYRING"):
        return None
    try:
        import keyring
        from keyring.backends import fail
        if isinstance(keyring.get_keyring(), fail.Keyring):
            return None
        return keyring
    except Exception:
        return None


# --- Windows DPAPI fallback -----------------------------------------------------------------------------------------
def _dpapi(data, protect):
    import ctypes
    from ctypes import wintypes

    class BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    buf = ctypes.create_string_buffer(data, len(data))
    blob_in, blob_out = BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))), BLOB()
    crypt32, kernel32 = ctypes.windll.crypt32, ctypes.windll.kernel32
    fn = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
    entropy = SERVICE.encode()
    ebuf = ctypes.create_string_buffer(entropy, len(entropy))
    blob_e = BLOB(len(entropy), ctypes.cast(ebuf, ctypes.POINTER(ctypes.c_char)))
    if protect:
        ok = fn(ctypes.byref(blob_in), "mindtrac-leadgen key", ctypes.byref(blob_e), None, None, 0x1, ctypes.byref(blob_out))
    else:
        ok = fn(ctypes.byref(blob_in), None, ctypes.byref(blob_e), None, None, 0x1, ctypes.byref(blob_out))
    if not ok:
        raise OSError("Windows DPAPI call failed")
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        kernel32.LocalFree(blob_out.pbData)


def _vault_path():
    return os.path.join(app_dir(), "secrets.dpapi.json")


def _vault_read():
    try:
        return json.load(open(_vault_path(), encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _vault_write(d):
    os.makedirs(app_dir(), exist_ok=True)
    tmp = _vault_path() + ".tmp"
    json.dump(d, open(tmp, "w", encoding="utf-8"))
    os.replace(tmp, _vault_path())


# --- public API -----------------------------------------------------------------------------------------------------
def backend():
    """Where keys are stored on this computer: 'keyring (<backend>)', 'windows-dpapi', or None (no safe store)."""
    kr = _keyring()
    if kr:
        return f"keyring ({type(kr.get_keyring()).__name__})"
    if os.name == "nt":
        return "windows-dpapi"
    return None


def get(name):
    """The key, or None. Environment variable first, then the system keychain, then the DPAPI file."""
    v = os.environ.get(name)
    if v and v.strip():
        return v.strip()
    kr = _keyring()
    if kr:
        try:
            v = kr.get_password(SERVICE, name)
            if v:
                return v
        except Exception:
            pass
    if os.name == "nt":
        enc = _vault_read().get(name)
        if enc:
            try:
                return _dpapi(base64.b64decode(enc), protect=False).decode("utf-8")
            except Exception:
                return None
    return None


def stored(name):
    """'env', 'store' or None – where get() would find the key (never returns the key itself)."""
    if (os.environ.get(name) or "").strip():
        return "env"
    saved = os.environ.pop(name, None)
    try:
        return "store" if get(name) else None
    finally:
        if saved is not None:
            os.environ[name] = saved


def put(name, value):
    value = value.strip()
    if not value:
        raise ValueError("empty key")
    kr = _keyring()
    if kr:
        kr.set_password(SERVICE, name, value)
        return backend()
    if os.name == "nt":
        d = _vault_read()
        d[name] = base64.b64encode(_dpapi(value.encode("utf-8"), protect=True)).decode("ascii")
        _vault_write(d)
        return backend()
    sys.exit("No safe key store on this computer: run `pip install keyring` and try again.")


def delete(name):
    kr = _keyring()
    if kr:
        try:
            kr.delete_password(SERVICE, name)
        except Exception:
            pass
    if os.name == "nt":
        d = _vault_read()
        if d.pop(name, None) is not None:
            _vault_write(d)
