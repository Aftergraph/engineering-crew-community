from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

from .policy import AuthorityEnvelope


def _utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        raise ValueError('timezone_required')
    return dt.astimezone(timezone.utc)


def _dt(dt: datetime) -> str:
    return _utc(dt).isoformat().replace('+00:00', 'Z')


def _sha(value: str) -> str:
    if len(value) != 64 or any(c not in '0123456789abcdef' for c in value.lower()):
        raise ValueError('invalid_sha256')
    return value.lower()


def _normalize(value: Any) -> Any:
    if isinstance(value, datetime):
        return _dt(value)
    if isinstance(value, frozenset):
        return sorted(value)
    if isinstance(value, tuple):
        return [_normalize(x) for x in value]
    if isinstance(value, Mapping):
        return {str(k): _normalize(v) for k, v in sorted(value.items(), key=lambda x: str(x[0]))}
    if is_dataclass(value):
        return {f.name: _normalize(getattr(value, f.name)) for f in fields(value) if f.name not in {'schema'}}
    return value


class CanonicalContract:
    schema: str = 'Contract/v1'

    def to_dict(self) -> dict[str, Any]:
        payload = {'schema': self.schema}
        payload.update(_normalize(self))
        return payload

    def canonical_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(',', ':'))

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.canonical_json().encode('utf-8')).hexdigest()


@dataclass(frozen=True, slots=True)
class AgentPrincipal(CanonicalContract):
    schema = 'AgentPrincipal/v1'
    principal_id: str
    host: str
    workspace: str
    role: str
    session_id: str
    authenticated: bool
    generation: int

    def __post_init__(self) -> None:
        if not all((self.principal_id, self.host, self.workspace, self.role, self.session_id)):
            raise ValueError('principal_identity_required')
        if self.generation < 0:
            raise ValueError('invalid_generation')


@dataclass(frozen=True, slots=True)
class DelegationGrant(CanonicalContract):
    schema = 'DelegationGrant/v1'
    grant_id: str
    issuer_principal_id: str
    subject_principal_id: str
    allowed_scopes: frozenset[str]
    generation: int
    issued_at: datetime
    expires_at: datetime
    parent_grant_id: str | None = None

    @classmethod
    def create(cls, *, grant_id: str, issuer: AgentPrincipal, subject: AgentPrincipal,
               allowed_scopes: Iterable[str], generation: int, issued_at: datetime,
               expires_at: datetime, parent_grant_id: str | None = None) -> 'DelegationGrant':
        if issuer.generation != generation or subject.generation != generation:
            raise ValueError('delegation_generation_mismatch')
        return cls(grant_id, issuer.principal_id, subject.principal_id, frozenset(allowed_scopes),
                   generation, _utc(issued_at), _utc(expires_at), parent_grant_id)

    def __post_init__(self) -> None:
        if not self.grant_id or not self.issuer_principal_id or not self.subject_principal_id:
            raise ValueError('delegation_identity_required')
        object.__setattr__(self, 'allowed_scopes', frozenset(self.allowed_scopes))
        object.__setattr__(self, 'issued_at', _utc(self.issued_at))
        object.__setattr__(self, 'expires_at', _utc(self.expires_at))
        if self.generation < 0 or self.expires_at <= self.issued_at:
            raise ValueError('invalid_delegation_window')

    def derive_authority(self, issuer_authority: AuthorityEnvelope, *, now: datetime) -> AuthorityEnvelope:
        now = _utc(now)
        if now < self.issued_at or now >= self.expires_at:
            raise ValueError('delegation_not_active')
        return issuer_authority.derive(self.allowed_scopes)


@dataclass(frozen=True, slots=True)
class CredentialHandle(CanonicalContract):
    schema = 'CredentialHandle/v1'
    handle_id: str
    issuer: str
    audience: str
    scopes: frozenset[str]
    expires_at: datetime
    generation: int

    def __post_init__(self) -> None:
        if not self.handle_id or not self.issuer or not self.audience:
            raise ValueError('credential_handle_identity_required')
        object.__setattr__(self, 'scopes', frozenset(self.scopes))
        object.__setattr__(self, 'expires_at', _utc(self.expires_at))
        if self.generation < 0:
            raise ValueError('invalid_generation')


@dataclass(frozen=True, slots=True)
class TrustLabel(CanonicalContract):
    schema = 'TrustLabel/v1'
    provenance: str
    confidentiality: str
    integrity: str
    sensitivity: frozenset[str]
    externality: str
    contamination: frozenset[str]

    def __post_init__(self) -> None:
        object.__setattr__(self, 'sensitivity', frozenset(self.sensitivity))
        object.__setattr__(self, 'contamination', frozenset(self.contamination))
        if not self.provenance or not self.confidentiality or not self.integrity or not self.externality:
            raise ValueError('trust_label_required')

    @classmethod
    def public_trusted(cls) -> 'TrustLabel':
        return cls('local-trusted', 'public', 'trusted', frozenset(), 'internal', frozenset())


@dataclass(frozen=True, slots=True)
class DeclassificationGrant(CanonicalContract):
    schema = 'DeclassificationGrant/v1'
    grant_id: str
    issuer_principal_id: str
    allowed_sensitivity: frozenset[str]
    target_externality: str
    expires_at: datetime

    def __post_init__(self) -> None:
        if not self.grant_id or not self.issuer_principal_id or not self.target_externality:
            raise ValueError('declassification_identity_required')
        object.__setattr__(self, 'allowed_sensitivity', frozenset(self.allowed_sensitivity))
        object.__setattr__(self, 'expires_at', _utc(self.expires_at))


@dataclass(frozen=True, slots=True)
class EvidenceRef(CanonicalContract):
    schema = 'EvidenceRef/v1'
    evidence_id: str
    subject: str
    sha256: str
    issuer: str
    source_revision: str
    observed_at: datetime
    expires_at: datetime

    def __post_init__(self) -> None:
        if not self.evidence_id or not self.subject or not self.issuer or not self.source_revision:
            raise ValueError('evidence_identity_required')
        object.__setattr__(self, 'sha256', _sha(self.sha256))
        object.__setattr__(self, 'observed_at', _utc(self.observed_at))
        object.__setattr__(self, 'expires_at', _utc(self.expires_at))

    def assert_fresh(self, now: datetime) -> None:
        if _utc(now) >= self.expires_at:
            raise ValueError('evidence_expired')

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> 'EvidenceRef':
        if raw.get('schema') != cls.schema:
            raise ValueError('evidence_schema')
        return cls(raw['evidence_id'], raw['subject'], raw['sha256'], raw['issuer'], raw['source_revision'],
                   datetime.fromisoformat(raw['observed_at'].replace('Z', '+00:00')),
                   datetime.fromisoformat(raw['expires_at'].replace('Z', '+00:00')))


@dataclass(frozen=True, slots=True)
class CapabilityAttestation(CanonicalContract):
    schema = 'CapabilityAttestation/v1'
    capability_id: str
    subject: str
    owner: str
    verifier: str
    maturity: str
    evidence: EvidenceRef
    observed_at: datetime
    expires_at: datetime
    signature: str

    def __post_init__(self) -> None:
        if self.maturity not in {'unavailable','beta','integration_partial','verified'}:
            raise ValueError('invalid_maturity')
        if not all((self.capability_id, self.subject, self.owner, self.verifier, self.signature)):
            raise ValueError('capability_attestation_required')
        if self.owner == self.verifier:
            raise ValueError('independent_verifier_required')
        object.__setattr__(self, 'observed_at', _utc(self.observed_at))
        object.__setattr__(self, 'expires_at', _utc(self.expires_at))


@dataclass(frozen=True, slots=True)
class ExecutionRequest(CanonicalContract):
    schema = 'ExecutionRequest/v1'
    mission_id: str
    work_unit_id: str
    generation: int
    subject: str
    exact_head: str
    requested_scopes: frozenset[str]
    credential_handles: tuple[CredentialHandle, ...]
    trust_label: TrustLabel

    def __post_init__(self) -> None:
        if not self.mission_id or not self.work_unit_id:
            raise ValueError('execution_identity_required')
        if not self.subject or not self.exact_head:
            raise ValueError('exact_subject_required')
        if self.generation < 0:
            raise ValueError('invalid_generation')
        object.__setattr__(self, 'requested_scopes', frozenset(self.requested_scopes))
        object.__setattr__(self, 'credential_handles', tuple(self.credential_handles))


@dataclass(frozen=True, slots=True)
class ExecutionReceipt(CanonicalContract):
    schema = 'ExecutionReceipt/v1'
    request_digest: str
    executor_principal_id: str
    subject: str
    exact_head: str
    effect_digest: str | None
    observed_at: datetime
    evidence: tuple[EvidenceRef, ...]

    def __post_init__(self) -> None:
        _sha(self.request_digest)
        if self.effect_digest is not None:
            _sha(self.effect_digest)
        if not self.executor_principal_id or not self.subject or not self.exact_head:
            raise ValueError('execution_receipt_identity_required')
        object.__setattr__(self, 'observed_at', _utc(self.observed_at))
        object.__setattr__(self, 'evidence', tuple(self.evidence))


@dataclass(frozen=True, slots=True)
class HostInstallReceipt(CanonicalContract):
    schema = 'HostInstallReceipt/v1'
    host: str
    version: str
    artifact_sha256: str
    observed_at: datetime
    host_identity: str
    source: str

    def __post_init__(self) -> None:
        object.__setattr__(self, 'artifact_sha256', _sha(self.artifact_sha256))
        object.__setattr__(self, 'observed_at', _utc(self.observed_at))
        if not all((self.host, self.version, self.host_identity, self.source)):
            raise ValueError('host_receipt_identity_required')


@dataclass(frozen=True, slots=True)
class HostInvocationReceipt(CanonicalContract):
    schema = 'HostInvocationReceipt/v1'
    host: str
    artifact_sha256: str
    invocation_id: str
    observed_at: datetime
    host_identity: str
    source: str

    def __post_init__(self) -> None:
        object.__setattr__(self, 'artifact_sha256', _sha(self.artifact_sha256))
        object.__setattr__(self, 'observed_at', _utc(self.observed_at))
        if not all((self.host, self.invocation_id, self.host_identity, self.source)):
            raise ValueError('host_receipt_identity_required')


@dataclass(frozen=True, slots=True)
class MCPConnectionReceipt(CanonicalContract):
    schema = 'MCPConnectionReceipt/v1'
    host: str
    server_id: str
    protocol_version: str
    transport: str
    observed_at: datetime
    source: str

    def __post_init__(self) -> None:
        if not all((self.host, self.server_id, self.protocol_version, self.transport, self.source)):
            raise ValueError('mcp_receipt_identity_required')
        object.__setattr__(self, 'observed_at', _utc(self.observed_at))


@dataclass(frozen=True, slots=True)
class TraceEnvelope(CanonicalContract):
    schema = 'TraceEnvelope/v1'
    trace_id: str
    span_id: str
    parent_span_id: str | None
    subject: str


@dataclass(frozen=True, slots=True)
class SupplyChainVerification(CanonicalContract):
    schema = 'SupplyChainVerification/v1'
    artifact_sha256: str
    source_revision: str
    builder_identity: str
    sbom_sha256: str
    provenance_sha256: str
    trusted: bool
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, 'artifact_sha256', _sha(self.artifact_sha256))
        object.__setattr__(self, 'sbom_sha256', _sha(self.sbom_sha256))
        object.__setattr__(self, 'provenance_sha256', _sha(self.provenance_sha256))
        object.__setattr__(self, 'reasons', tuple(self.reasons))
