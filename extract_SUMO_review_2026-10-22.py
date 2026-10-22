#!/usr/bin/env python3
"""Rebuild and extract the reviewed SUMO package from its numbered text parts."""
from pathlib import Path
import base64, hashlib, io, tarfile

EXPECTED_SHA256 = "1f6e1f0883dbf88c6999223dd9bb8096707eaf8be91fd9479ab3083435f42ce9"
PART_PATTERN = "SUMO_review_2026-10-22.part*.b64.txt"

def main() -> None:
    here = Path(__file__).resolve().parent
    parts = sorted(here.glob(PART_PATTERN))
    if len(parts) != 5:
        raise SystemExit(f"Expected 5 parts, found {len(parts)}")
    encoded = "".join(p.read_text(encoding="ascii") for p in parts)
    data = base64.b64decode(encoded)
    actual = hashlib.sha256(data).hexdigest()
    if actual != EXPECTED_SHA256:
        raise SystemExit(f"Checksum mismatch: {actual}")
    destination = here.resolve()
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        members = archive.getmembers()
        for member in members:
            target = (destination / member.name).resolve()
            if target != destination and destination not in target.parents:
                raise SystemExit(f"Unsafe path: {member.name}")
            if member.issym() or member.islnk():
                raise SystemExit(f"Archive links are not allowed: {member.name}")
        archive.extractall(destination, members=members)
    print(f"Extracted review_2026-10-22 to {destination}")

if __name__ == "__main__":
    main()
