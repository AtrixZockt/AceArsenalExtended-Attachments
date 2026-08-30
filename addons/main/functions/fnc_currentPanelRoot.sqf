#include "..\script_component.hpp"
#include "..\defines.hpp"
/*
 * Which config root the right panel is currently listing, "" if it is showing
 * something this addon does not group.
 *
 * The panel holds classes from exactly one root at a time, and that root is the
 * only thing the rest of the addon needs to know about it: every ACEAX gearinfo
 * function takes the root as its first argument, so answering this question once
 * is what lets one code path serve attachments and magazines alike.
 *
 * This used to return an attachment slot index, which read as though the index
 * mattered. It never did -- both callers only ever tested it for >= 0.
 *
 * Arguments:
 * None
 *
 * Return Value:
 * "CfgWeapons" for an attachment slot, "CfgMagazines" for one of the ammunition
 * tabs, "" for anything else -- grenades, explosives, a container's contents. <STRING>
 */

// ACE nils this when the arsenal closes, and the collapse runs a frame late, so it
// can land after that even though the display check passed.
if (isNil "ace_arsenal_currentRightPanel") exitWith { "" };

private _panel = ace_arsenal_currentRightPanel;

switch (true) do {
    case (_panel in [ATTACHMENT_SLOT_IDCS]): { "CfgWeapons" };
    case (_panel in [MAGAZINE_SLOT_IDCS]): { "CfgMagazines" };
    default { "" };
};
