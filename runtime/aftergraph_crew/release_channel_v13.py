from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from typing import Iterable

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


def _utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        raise ValueError('channel:timezone_required')
    return dt.astimezone(timezone.utc)


def _sha(value: str) -> str:
    if len(value) != 64 or any(c not in '0123456789abcdef' for c in value.lower()):
        raise ValueError('channel:invalid_sha256')
    return value.lower()


@dataclass(frozen=True, slots=True)
class ChannelArtifact:
    name: str
    sha256: str
    size: int
    media_type: str
    edition: str

    def __post_init__(self) -> None:
        if not self.name or self.size < 0 or not self.media_type:
            raise ValueError('channel:artifact_invalid')
        if self.edition not in {'full','community'}:
            raise ValueError('channel:edition_invalid')
        object.__setattr__(self, 'sha256', _sha(self.sha256))


@dataclass(frozen=True, slots=True)
class ReleaseChannelManifest:
    schema: str
    channel: str
    sequence: int
    release_version: str
    python_version: str
    published_at: datetime
    artifacts: tuple[ChannelArtifact, ...]
    previous_manifest_digest: str | None = None
    signer_key_id: str | None = None
    signature: str | None = None

    def __post_init__(self) -> None:
        if self.schema != 'ReleaseChannelManifest/v1':
            raise ValueError('channel:schema')
        if self.channel not in {'frontier','stable','community'}:
            raise ValueError('channel:name')
        if self.sequence < 1 or not self.release_version or not self.python_version:
            raise ValueError('channel:identity')
        object.__setattr__(self, 'published_at', _utc(self.published_at))
        object.__setattr__(self, 'artifacts', tuple(sorted(self.artifacts, key=lambda x: x.name)))
        if self.previous_manifest_digest is not None:
            object.__setattr__(self, 'previous_manifest_digest', _sha(self.previous_manifest_digest))
        names=[x.name for x in self.artifacts]
        if len(names)!=len(set(names)):
            raise ValueError('channel:duplicate_artifact')

    def payload(self) -> dict:
        return {
            'schema': self.schema,
            'channel': self.channel,
            'sequence': self.sequence,
            'release_version': self.release_version,
            'python_version': self.python_version,
            'published_at': self.published_at.isoformat().replace('+00:00','Z'),
            'artifacts': [asdict(x) for x in self.artifacts],
            'previous_manifest_digest': self.previous_manifest_digest,
            'signer_key_id': self.signer_key_id,
        }

    @property
    def digest(self) -> str:
        return hashlib.sha256(json.dumps(self.payload(), sort_keys=True, separators=(',',':')).encode()).hexdigest()

    def signed(self, private_key: Ed25519PrivateKey, key_id: str) -> 'ReleaseChannelManifest':
        unsigned=replace(self, signer_key_id=key_id, signature=None)
        sig=private_key.sign(bytes.fromhex(unsigned.digest))
        return replace(unsigned, signature=base64.b64encode(sig).decode())

    def verify(self, public_key: Ed25519PublicKey, *, expected_key_id: str, previous: 'ReleaseChannelManifest | None'=None) -> tuple[str,...]:
        errors=[]
        if self.signer_key_id != expected_key_id:
            errors.append('channel:key_id_mismatch')
        if not self.signature:
            errors.append('channel:signature_missing')
        else:
            try:
                public_key.verify(base64.b64decode(self.signature, validate=True), bytes.fromhex(self.digest))
            except Exception:
                errors.append('channel:signature_invalid')
        if previous is not None:
            if self.channel != previous.channel:
                errors.append('channel:previous_channel_mismatch')
            if self.sequence != previous.sequence + 1:
                errors.append('channel:sequence_not_monotonic')
            if self.previous_manifest_digest != previous.digest:
                errors.append('channel:lineage_mismatch')
            if self.published_at <= previous.published_at:
                errors.append('channel:time_not_monotonic')
        if self.channel == 'community' and any(a.edition != 'community' for a in self.artifacts):
            errors.append('channel:community_contains_private_edition')
        return tuple(errors)
