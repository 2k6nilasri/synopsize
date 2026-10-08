import socket
import struct


class AntivirusUnavailableError(RuntimeError):
    """Raised when the configured antivirus scanner cannot be reached."""


class MalwareDetectedError(RuntimeError):
    """Raised when the antivirus scanner identifies malware."""


def scan_with_clamd(
    file_bytes: bytes, host: str, port: int, timeout: float
) -> str:
    """Stream file bytes to ClamAV and return its clean response."""
    try:
        with socket.create_connection((host, port), timeout=timeout) as scanner:
            scanner.settimeout(timeout)
            scanner.sendall(b"zINSTREAM\0")
            for offset in range(0, len(file_bytes), 64 * 1024):
                chunk = file_bytes[offset : offset + 64 * 1024]
                scanner.sendall(struct.pack("!I", len(chunk)))
                scanner.sendall(chunk)
            scanner.sendall(struct.pack("!I", 0))

            response = bytearray()
            while not response.endswith(b"\0"):
                packet = scanner.recv(4096)
                if not packet:
                    raise AntivirusUnavailableError(
                        "Antivirus scanner closed the connection without a result."
                    )
                response.extend(packet)
    except (OSError, TimeoutError) as error:
        raise AntivirusUnavailableError(
            f"Could not complete antivirus scan: {error}"
        ) from error

    result = response.rstrip(b"\0").decode("utf-8", errors="replace")
    if result.endswith(" OK"):
        return result
    if result.endswith(" FOUND"):
        raise MalwareDetectedError(result)
    raise AntivirusUnavailableError(f"Antivirus scanner returned an error: {result}")
