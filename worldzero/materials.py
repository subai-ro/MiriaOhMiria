from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


MATERIAL_CONTACT_SCHEMA = "material_medium_contact.v1"


def _clean(value: str, label: str) -> str:
    cleaned = " ".join(str(value).split())
    if not cleaned:
        raise ValueError(f"{label} cannot be empty")
    return cleaned


def _round(value: float) -> float:
    return round(float(value), 12)


@dataclass(frozen=True)
class MaterialConstituent:
    """One objectively known constituent of an item material profile."""

    material_id: str
    mass_fraction: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "material_id", _clean(self.material_id, "material_id"))
        fraction = float(self.mass_fraction)
        if not 0.0 < fraction <= 1.0:
            raise ValueError("material mass_fraction must be in (0, 1]")
        object.__setattr__(self, "mass_fraction", _round(fraction))


@dataclass(frozen=True)
class ItemMaterialProfile:
    """Authoritative composition and contact geometry for an item kind.

    The profile is ordinary object data.  It does not know which hidden laws
    may respond to a constituent and therefore cannot encode a story trigger.
    """

    item_id: str
    constituents: tuple[MaterialConstituent, ...]
    aqueous_contact_factor: float = 1.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "item_id", _clean(self.item_id, "item_id"))
        constituents = tuple(self.constituents)
        if not constituents:
            raise ValueError("an item material profile needs at least one constituent")
        material_ids = [item.material_id for item in constituents]
        if len(material_ids) != len(set(material_ids)):
            raise ValueError("an item material profile cannot repeat a constituent")
        total = sum(item.mass_fraction for item in constituents)
        if total > 1.0 + 1e-12:
            raise ValueError("item material mass fractions cannot exceed 1")
        factor = float(self.aqueous_contact_factor)
        if not 0.0 < factor <= 1.0:
            raise ValueError("aqueous_contact_factor must be in (0, 1]")
        object.__setattr__(self, "constituents", constituents)
        object.__setattr__(self, "aqueous_contact_factor", _round(factor))

    @property
    def material_fractions(self) -> dict[str, float]:
        return {
            item.material_id: item.mass_fraction
            for item in sorted(self.constituents, key=lambda value: value.material_id)
        }

    def fraction_of(self, material_id: str) -> float:
        wanted = _clean(material_id, "material_id")
        return self.material_fractions.get(wanted, 0.0)


@dataclass(frozen=True)
class MaterialMediumContact:
    """A general, event-embeddable record of item/medium contact.

    Hidden-metaphysics processes consume this schema instead of subscribing to
    gameplay verbs such as ``FISHED``.  New verbs can therefore participate by
    recording the same physical contract.
    """

    medium_kind: str
    medium_ref: str
    contact_item_id: str
    contact_units: float
    material_fractions: tuple[tuple[str, float], ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "medium_kind", _clean(self.medium_kind, "medium_kind"))
        object.__setattr__(self, "medium_ref", _clean(self.medium_ref, "medium_ref"))
        object.__setattr__(self, "contact_item_id", _clean(self.contact_item_id, "contact_item_id"))
        units = float(self.contact_units)
        if not 0.0 < units:
            raise ValueError("contact_units must be positive")
        fractions: list[tuple[str, float]] = []
        seen: set[str] = set()
        for material_id, fraction in self.material_fractions:
            cleaned = _clean(material_id, "material_id")
            numeric = float(fraction)
            if cleaned in seen:
                raise ValueError("material contact cannot repeat a constituent")
            if not 0.0 < numeric <= 1.0:
                raise ValueError("contact material fractions must be in (0, 1]")
            seen.add(cleaned)
            fractions.append((cleaned, _round(numeric)))
        if not fractions or sum(value for _, value in fractions) > 1.0 + 1e-12:
            raise ValueError("material contact needs a valid composition")
        object.__setattr__(self, "contact_units", _round(units))
        object.__setattr__(self, "material_fractions", tuple(sorted(fractions)))

    def as_dict(self) -> dict:
        return {
            "schema": MATERIAL_CONTACT_SCHEMA,
            "medium_kind": self.medium_kind,
            "medium_ref": self.medium_ref,
            "contact_item_id": self.contact_item_id,
            "contact_units": self.contact_units,
            "material_fractions": dict(self.material_fractions),
        }


class MaterialCatalog:
    """Small authoritative catalog; it owns composition, not metaphysics."""

    def __init__(self, profiles: Iterable[ItemMaterialProfile] = ()) -> None:
        self._profiles: dict[str, ItemMaterialProfile] = {}
        for profile in profiles:
            self.register(profile)

    @property
    def profiles(self) -> tuple[ItemMaterialProfile, ...]:
        return tuple(self._profiles[key] for key in sorted(self._profiles))

    def register(self, profile: ItemMaterialProfile) -> None:
        if profile.item_id in self._profiles:
            raise ValueError(f"item material profile already exists: {profile.item_id}")
        self._profiles[profile.item_id] = profile

    def get(self, item_id: str) -> ItemMaterialProfile | None:
        return self._profiles.get(_clean(item_id, "item_id"))

    def require(self, item_id: str) -> ItemMaterialProfile:
        cleaned = _clean(item_id, "item_id")
        try:
            return self._profiles[cleaned]
        except KeyError as exc:
            raise ValueError(f"unknown material profile for contact item: {cleaned}") from exc

    def medium_contact(
        self,
        *,
        item_id: str,
        medium_kind: str,
        medium_ref: str,
        base_contact_units: float,
    ) -> MaterialMediumContact:
        profile = self.require(item_id)
        return MaterialMediumContact(
            medium_kind=medium_kind,
            medium_ref=medium_ref,
            contact_item_id=profile.item_id,
            contact_units=float(base_contact_units) * profile.aqueous_contact_factor,
            material_fractions=tuple(profile.material_fractions.items()),
        )


def create_default_material_catalog() -> MaterialCatalog:
    """Seed catalog used by the current vertical slice.

    ``silver_rod`` is data in this catalog, not a branch in the echo law.  A
    different item with the same composition obeys the same material contract.
    """

    return MaterialCatalog(
        (
            ItemMaterialProfile(
                "hands",
                (MaterialConstituent("living_tissue", 1.0),),
                aqueous_contact_factor=0.35,
            ),
            ItemMaterialProfile(
                "silver_rod",
                (
                    MaterialConstituent("silver", 0.925),
                    MaterialConstituent("hardwood", 0.075),
                ),
                aqueous_contact_factor=0.60,
            ),
            ItemMaterialProfile(
                "iron_rod",
                (MaterialConstituent("iron", 1.0),),
                aqueous_contact_factor=0.60,
            ),
        )
    )
