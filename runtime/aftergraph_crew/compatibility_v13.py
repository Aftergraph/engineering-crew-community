from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


def _major(version: str) -> int:
    try:
        return int(version.split('.',1)[0])
    except Exception as exc:
        raise ValueError('compat:invalid_version') from exc


@dataclass(frozen=True, slots=True)
class MigrationStep:
    step_id: str
    from_schema: int
    to_schema: int
    reversible: bool
    description: str

    def __post_init__(self) -> None:
        if not self.step_id or self.from_schema < 0 or self.to_schema <= self.from_schema:
            raise ValueError('compat:migration_step_invalid')


@dataclass(frozen=True, slots=True)
class UpgradeContract:
    schema: str
    from_version: str
    to_version: str
    state_schema_from: int
    state_schema_to: int
    min_python: tuple[int,int]
    min_host_protocol: str
    downgrade_supported: bool
    migration_steps: tuple[MigrationStep,...]

    def __post_init__(self) -> None:
        if self.schema != 'UpgradeContract/v1':
            raise ValueError('compat:schema')
        if _major(self.to_version) < _major(self.from_version):
            raise ValueError('compat:upgrade_contract_downgrade')
        if self.state_schema_to < self.state_schema_from:
            raise ValueError('compat:schema_regression')
        object.__setattr__(self,'migration_steps',tuple(self.migration_steps))
        if self.state_schema_to == self.state_schema_from and self.migration_steps:
            raise ValueError('compat:unneeded_migration')
        if self.state_schema_to > self.state_schema_from:
            if not self.migration_steps:
                raise ValueError('compat:migration_missing')
            current=self.state_schema_from
            for step in self.migration_steps:
                if step.from_schema != current:
                    raise ValueError('compat:migration_gap')
                current=step.to_schema
            if current != self.state_schema_to:
                raise ValueError('compat:migration_incomplete')
        if self.downgrade_supported and any(not x.reversible for x in self.migration_steps):
            raise ValueError('compat:unsafe_downgrade_claim')

    def assert_environment(self, *, python_version: tuple[int,int], host_protocol: str) -> tuple[str,...]:
        errors=[]
        if python_version < self.min_python:
            errors.append('compat:python_too_old')
        if host_protocol != self.min_host_protocol:
            errors.append('compat:host_protocol_mismatch')
        return tuple(errors)


@dataclass(frozen=True, slots=True)
class MigrationReceipt:
    schema: str
    from_schema: int
    to_schema: int
    applied_steps: tuple[str,...]
    reversible: bool


def plan_migration(contract: UpgradeContract) -> MigrationReceipt:
    return MigrationReceipt('MigrationReceipt/v1', contract.state_schema_from, contract.state_schema_to,
                            tuple(x.step_id for x in contract.migration_steps),
                            all(x.reversible for x in contract.migration_steps))
