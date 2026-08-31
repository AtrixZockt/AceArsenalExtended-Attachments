#include "..\script_component.hpp"
#include "..\defines.hpp"
/*
 * The class actually fitted to the slot the right panel is showing.
 *
 * This is the addon's answer to "what is on the weapon", as opposed to "what does
 * the listbox say". The two can disagree, and when they do the weapon is right:
 *
 *   - the collapse deletes rows, which shifts every row below the deleted one and
 *     leaves a previously correct selection index pointing somewhere else;
 *   - ACE normalises the equipped attachment through fnc_baseWeapon before matching
 *     it against lbData (fnc_fillRightPanel), so a variant that declares baseWeapon
 *     selects a different class of the same model -- or fails to match and falls
 *     back to <empty>.
 *
 * ACEAX does the same thing on the left panel and for the same reason: see
 * aceax_arsenal_fnc_onSelChangedLeft, which calls ACE's handler and then re-reads
 * the result out of ace_arsenal_currentItems rather than trusting the row.
 *
 * Reads the ace_arsenal globals directly rather than taking arguments, like
 * fnc_currentPanelRoot -- the panel state is the input, and every caller would
 * otherwise have to fetch it first.
 *
 * Arguments:
 * None
 *
 * Return Value:
 * Equipped class, "" when this panel has no single equipped item <STRING>
 */

if (isNil "ace_arsenal_currentItems") exitWith { "" };

// Which weapon's items array. -1 means a container is selected on the left, in
// which case ACE swaps the right panel over to the listnbox entirely and there is
// no attachment slot on show.
private _weaponIndex = [WEAPON_PANEL_IDCS] find (missionNamespace getVariable ["ace_arsenal_currentLeftPanel", -1]);
if (_weaponIndex == -1) exitWith { "" };

// Which slot within it. -1 covers the compatible-ammunition tabs, grenades and
// explosives -- panels that list what fits rather than what is fitted.
private _slotIndex = [EQUIPPED_SLOT_IDCS] find (missionNamespace getVariable ["ace_arsenal_currentRightPanel", -1]);
if (_slotIndex == -1) exitWith { "" };

// param rather than select: ACE builds the array with six entries, but a weapon
// with no secondary muzzle is one case where reading past the end is plausible.
((ace_arsenal_currentItems select (IDX_CURR_PRIMARY_WEAPON_ITEMS + _weaponIndex)) param [_slotIndex, ""])
