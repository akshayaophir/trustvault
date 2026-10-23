import re

MAX_BYTES = 5 * 1024 * 1024
ALLOWED = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "txt": "text/plain",
}


class UploadError(Exception):
    def __init__(self, message: str, status: int = 400):
        self.message = message
        self.status = status


def clean_name(raw: str) -> str:
    """Keep only the last path part and safe characters."""
    name = (raw or "").replace("\\", "/").split("/")[-1]
    name = re.sub(r"[^A-Za-z0-9._ -]", "_", name).strip(" .")
    return name[:150]


def detect_kind(data: bytes) -> str | None:
    """Look at the file's real content, not its name."""
    if data.startswith(b"%PDF-"):
        return "pdf"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if b"\x00" not in data:
        try:
            data.decode("utf-8")
            return "txt"
        except UnicodeDecodeError:
            return None
    return None


def validate_upload(filename: str, data: bytes) -> tuple[str, str]:
    """Return (safe_name, mime) or raise UploadError."""
    if len(data) > MAX_BYTES:
        raise UploadError("File too large (max 5 MB)", 413)
    if not data:
        raise UploadError("Empty file")
    name = clean_name(filename)
    if "." not in name:
        raise UploadError("File name needs an extension")
    ext = name.rsplit(".", 1)[1].lower()
    if ext not in ALLOWED:
        raise UploadError("File type not allowed")
    expected = "jpg" if ext in ("jpg", "jpeg") else ext
    if detect_kind(data) != expected:
        raise UploadError("File content does not match its extension")
    return name, ALLOWED[ext]