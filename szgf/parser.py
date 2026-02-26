from __future__ import annotations

from enum import StrEnum
from operator import itemgetter
from typing import TYPE_CHECKING

import hb_data

from szgf.schemas.original import Section
from szgf.schemas.parsed import (
    ParsedCharacter,
    ParsedGuide,
    ParsedTeam,
    ParsedTeamMember,
    ParsedTeamSection,
    ParsedWeaponSection,
)

if TYPE_CHECKING:
    from szgf.schemas.original import (
        Character,
        DiscSection,
        DiscSetSection,
        OriginalGuide,
        Team,
        TeamMember,
        TeamSection,
        WeaponSection,
    )

SINGLE_DISC_ICON_URL = "https://raw.githubusercontent.com/seriaati/szgf/refs/heads/main/assets/drive_discs/single/{id}.webp"
COMBINED_DISC_ICON_URL = "https://raw.githubusercontent.com/seriaati/szgf/refs/heads/main/assets/drive_discs/combined/{id1}_{id2}.webp"


class Stat(StrEnum):
    HP = "hp"
    ATK = "atk"
    DEF = "def"
    CRIT_RATE = "cr"
    CRIT_DMG = "cd"
    ENERGY_REGEN = "er"
    IMPACT = "imp"
    ANOMALY_MASTERY = "am"
    ANOMALY_PROFICIENCY = "ap"
    PEN_RATIO = "pr"
    PEN = "pen"

    SHEER_FORCE = "sf"
    AAA = "aaa"
    """Automatic Adrenaline Accumulation"""

    ETHER_DMG_BONUS = "ether"
    PHYSICAL_DMG_BONUS = "physical"
    FIRE_DMG_BONUS = "fire"
    ICE_DMG_BONUS = "ice"
    ELECTRIC_DMG_BONUS = "elec"


STAT_KW_MATCHES = {
    Stat.HP: ("hp", "max hp", "flat hp", "hp%"),
    Stat.ATK: ("atk", "flat atk", "atk%"),
    Stat.DEF: ("def", "flat def", "def%"),
    Stat.CRIT_RATE: ("crit rate", "cr", "crit rate%", "cr%", "crate%"),
    Stat.CRIT_DMG: ("crit damage", "crit dmg", "cd", "crit dmg%", "cd%", "cdmg%"),
    Stat.ENERGY_REGEN: ("energy regen", "er", "er%"),
    Stat.IMPACT: ("impact",),
    Stat.ANOMALY_MASTERY: ("anomaly mastery", "am"),
    Stat.ANOMALY_PROFICIENCY: ("anomaly proficiency", "ap"),
    Stat.PEN_RATIO: ("pen ratio", "pen ratio%"),
    Stat.PEN: ("pen", "flat pen"),
    Stat.SHEER_FORCE: ("sheer force",),
    Stat.AAA: ("aaa", "automatic adrenaline accumulation", "adrenaline"),
    Stat.ETHER_DMG_BONUS: ("ether damage bonus", "ether dmg bonus", "ether dmg", "ether"),
    Stat.PHYSICAL_DMG_BONUS: (
        "physical damage bonus",
        "physical dmg bonus",
        "physical dmg",
        "physical",
    ),
    Stat.FIRE_DMG_BONUS: ("fire damage bonus", "fire dmg bonus", "fire dmg", "fire"),
    Stat.ICE_DMG_BONUS: ("ice damage bonus", "ice dmg bonus", "ice dmg", "ice"),
    Stat.ELECTRIC_DMG_BONUS: (
        "electric damage bonus",
        "electric dmg bonus",
        "electric dmg",
        "electric",
    ),
}


async def get_character_by_name(name: str) -> hb_data.zzz.Character | None:
    async with hb_data.ZZZClient() as client:
        characters = client.get_characters()
        for character in characters:
            if (
                character.name.lower() == name.lower()
                or character.full_name.lower() == name.lower()
            ):
                return character
    return None


async def get_weapon_by_name(name: str) -> hb_data.zzz.Weapon | None:
    async with hb_data.ZZZClient() as client:
        weapons = client.get_weapons()
        for weapon in weapons:
            if weapon.name.lower() == name.lower():
                return weapon
    return None


async def get_drive_disc_by_name(name: str) -> hb_data.zzz.DriveDiscSet | None:
    async with hb_data.ZZZClient() as client:
        drive_discs = client.get_drive_disc_sets()
        for disc in drive_discs:
            if disc.name.lower() == name.lower():
                return disc
    return None


async def _parse_character(original_character: Character) -> ParsedCharacter:
    """Parse character data from original guide."""
    character = await get_character_by_name(original_character.name)
    if character is None:
        msg = f"Character '{original_character.name}' not found"
        raise ValueError(msg)

    return ParsedCharacter(
        name=character.name,
        id=character.id,
        element=character.element,
        specialty=character.specialty,
        rarity=original_character.rarity,
        banner=f"https://zzz.honeyhunterworld.com/img/character/{character.id}-char_mindscape3_icon.webp",
    )


async def _parse_weapons(original_weapons: list[WeaponSection]) -> list:
    """Parse weapons data from original guide."""
    parsed_weapons = []

    for weapon in original_weapons:
        weapon_data = await get_weapon_by_name(weapon.name)
        if weapon_data is not None:
            parsed_weapon = ParsedWeaponSection(
                id=weapon_data.id,
                rarity=weapon_data.rarity_str,
                specialty=weapon_data.specialty,
                icon=weapon.icon or weapon_data.icon,
                **weapon.model_dump(exclude={"icon"}),
            )
            parsed_weapons.append(parsed_weapon)
        else:
            parsed_weapons.append(weapon)

    return parsed_weapons


async def _parse_four_piece_discs(four_pieces: list[DiscSetSection]) -> None:
    """Parse four-piece disc sections and set their icons in-place."""
    for disc_section in four_pieces:
        disc_data = await get_drive_disc_by_name(disc_section.name)
        if disc_data is None:
            msg = f"Drive disc '{disc_section.name}' not found"
            raise ValueError(msg)

        disc_section.icon = SINGLE_DISC_ICON_URL.format(id=disc_data.id)


async def _parse_two_piece_discs(two_pieces: list[DiscSetSection]) -> None:
    """Parse two-piece disc sections and set their icons in-place."""
    for disc_section in two_pieces:
        disc_names = disc_section.name.split(" / ")
        disc_ids = []
        for disc_name in disc_names:
            disc_data = await get_drive_disc_by_name(disc_name)
            if disc_data is None:
                msg = f"Drive disc '{disc_name}' not found"
                raise ValueError(msg)
            disc_ids.append(disc_data.id)

        if len(disc_ids) == 1:
            disc_section.icon = SINGLE_DISC_ICON_URL.format(id=disc_ids[0])
        elif len(disc_ids) == 2:
            disc_section.icon = disc_section.icon or COMBINED_DISC_ICON_URL.format(
                id1=disc_ids[0], id2=disc_ids[1]
            )
        else:
            msg = f"Drive disc section '{disc_section.name}' has an invalid number of discs ({len(disc_ids)})"
            raise ValueError(msg)


async def _parse_discs(discs_section: DiscSection | None) -> DiscSection | None:
    """Parse disc sections (both four-piece and two-piece) in-place."""
    if discs_section is not None:
        await _parse_four_piece_discs(discs_section.four_pieces)
        await _parse_two_piece_discs(discs_section.two_pieces)
    return discs_section


async def _parse_team_member(member: TeamMember) -> ParsedTeamMember:
    """Parse a single team member with multiple character alternatives."""
    member_names = member.name.split(" / ")
    member_ids: list[int] = []
    member_icons: list[str] = []

    for name in member_names:
        member_data = await get_character_by_name(name)
        if member_data is None:
            msg = f"Team member '{name}' not found"
            raise ValueError(msg)
        member_ids.append(member_data.id)
        member_icons.append(member_data.icon)

    return ParsedTeamMember(ids=member_ids, icons=member_icons, name=member.name)


async def _parse_team(team: Team) -> ParsedTeam:
    """Parse a single team with all its members."""
    parsed_members: list[ParsedTeamMember] = []

    for member in team.characters:
        parsed_member = await _parse_team_member(member)
        parsed_members.append(parsed_member)

    return ParsedTeam(name=team.name, characters=parsed_members, description=team.description)


async def _parse_team_section(original_team: TeamSection | None) -> ParsedTeamSection | None:
    """Parse team section with all teams."""
    if original_team is None:
        return None

    parsed_teams: list[ParsedTeam] = []

    for team in original_team.teams:
        parsed_team = await _parse_team(team)
        parsed_teams.append(parsed_team)

    return ParsedTeamSection(teams=parsed_teams, extra_sections=original_team.extra_sections)


def _replace_stat_keywords(string: str) -> str:
    """Replace stat keywords with formatted versions including icon placeholders.

    This function:
    1. Converts text to lowercase for case-insensitive matching
    2. Finds all keyword matches and their positions
    3. Reverts to original text with proper casing
    4. Adds formatting and icon placeholders

    Example:
        Input: "BIS W-Engine, has a HP% Main Stat"
        Output: "BIS W-Engine, has a <hp> **HP%** Main Stat"
    """
    lowered = string.lower()

    # Collect all matches with their positions
    matches: list[tuple[int, int, str, Stat]] = []  # (start, end, original_text, stat)

    for stat, keywords in STAT_KW_MATCHES.items():
        # Sort keywords by length (longest first) to match longer phrases first
        sorted_keywords = sorted(keywords, key=len, reverse=True)

        for kw in sorted_keywords:
            kw_lower = kw.lower()
            start = 0

            while True:
                # Find next occurrence of keyword
                pos = lowered.find(kw_lower, start)
                if pos == -1:
                    break

                end = pos + len(kw_lower)

                # Check if this is a whole word match (not part of another word)
                before_ok = pos == 0 or lowered[pos - 1] in {
                    " ",
                    "\n",
                    "\t",
                    ",",
                    ".",
                    "(",
                    "[",
                    ":",
                    "/",
                }
                after_ok = end == len(lowered) or lowered[end] in {
                    " ",
                    "\n",
                    "\t",
                    ",",
                    ".",
                    ")",
                    "]",
                    ":",
                    "/",
                }

                if before_ok and after_ok:
                    # Check if this position overlaps with an existing match
                    overlaps = any(
                        (pos < match_end and end > match_start)
                        for match_start, match_end, _, _ in matches
                    )

                    if not overlaps:
                        # Get the original text (with proper casing) from the input string
                        original_text = string[pos:end]
                        matches.append((pos, end, original_text, stat))

                start = pos + 1

    # Sort matches by position (reverse order to replace from end to start)
    matches.sort(key=itemgetter(0), reverse=True)

    # Replace each match with formatted version
    result = string
    for start, end, original_text, stat in matches:
        formatted = f"<{stat.value}> {original_text}"
        result = result[:start] + formatted + result[end:]

    return result


def _mass_replace_stat_keywords(original: OriginalGuide) -> None:  # noqa: PLR0912
    # Guide description
    original.description = _replace_stat_keywords(original.description)

    # Weapon
    for weapon in original.weapons:
        weapon.description = _replace_stat_keywords(weapon.description)

    # Discs
    if original.discs is not None:
        for disc_set in original.discs.four_pieces:
            disc_set.description = _replace_stat_keywords(disc_set.description)
        for disc_set in original.discs.two_pieces:
            disc_set.description = _replace_stat_keywords(disc_set.description)

    # Stats
    if original.stat is not None:
        for main_stat in original.stat.main_stats:
            main_stat.stat_priority = _replace_stat_keywords(main_stat.stat_priority)
        original.stat.sub_stats = _replace_stat_keywords(original.stat.sub_stats)
        original.stat.baseline_stats = _replace_stat_keywords(original.stat.baseline_stats)
        original.stat.extra_sections = [
            Section(title=section.title, description=_replace_stat_keywords(section.description))
            for section in original.stat.extra_sections
        ]

    # Skill priority
    if original.skill_priority is not None and original.skill_priority.description is not None:
        original.skill_priority.description = _replace_stat_keywords(
            original.skill_priority.description
        )

    # Skills
    for skill in original.skills:
        skill.description = _replace_stat_keywords(skill.description)
        skill.explanation = _replace_stat_keywords(skill.explanation)

    # Mindscapes
    for mindscape in original.mindscapes:
        mindscape.description = _replace_stat_keywords(mindscape.description)

    # Team
    if original.team is not None:
        for team in original.team.teams:
            if team.description is not None:
                team.description = _replace_stat_keywords(team.description)
        for section in original.team.extra_sections:
            section.description = _replace_stat_keywords(section.description)

    # Rotation
    if original.rotation is not None:
        original.rotation.description = _replace_stat_keywords(original.rotation.description)


async def parse_original_guide(original: OriginalGuide) -> ParsedGuide:
    """Parse an original guide into a parsed guide with enriched data."""
    _mass_replace_stat_keywords(original)

    parsed_character = await _parse_character(original.character)
    parsed_weapons = await _parse_weapons(original.weapons)
    parsed_discs = await _parse_discs(original.discs)
    parsed_team_section = await _parse_team_section(original.team)

    return ParsedGuide(
        character=parsed_character,
        weapons=parsed_weapons,
        team=parsed_team_section,
        discs=parsed_discs,
        **original.model_dump(exclude={"character", "weapons", "team", "discs"}),
    )
