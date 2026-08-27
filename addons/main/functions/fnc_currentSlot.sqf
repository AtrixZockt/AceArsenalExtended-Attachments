#include "..\script_component.hpp"
#include "..\defines.hpp"
/*
 * Which attachment slot the right panel is showing, and what is in it.
 *
 * Reproduces the lookup ace_arsenal_fnc_onSelChangedRight does: the right panel's
 * meaning depends on BOTH panels. The left panel says which weapon's attachments
 * are being listed, the right panel says which slot of it.
 *
 * A container (uniform / vest / backpack) on the left is still valid -- the right
 * panel then lists every attachment rather than the ones compatible with a
 * weapon, and nothing is "equipped". That case returns an empty class name.
 *
 * Arguments:
 * None
 *
 * Return Value:
 * [] if the right panel is not an attachment slot, otherwise:
 * 0: Slot index, 0=muzzle 1=pointer 2=optic 3=bipod <NUMBER>
 * 1: Class currently in that slot, "" if none or no weapon selected <STRING>
 */

// ACE nils these when the arsenal closes. refreshOptions runs a frame late, so it
// can land after that even though its display check passed.
if (isNil "ace_arsenal_currentRightPanel" || {isNil "ace_arsenal_currentItems"}) exitWith { [] };

private _slotIndex = [ATTACHMENT_SLOT_IDCS] find ace_arsenal_currentRightPanel;

// Magazines, grenades, misc items and the container panels all land here.
if (_slotIndex == -1) exitWith { [] };

private _weaponIndex = if (isNil "ace_arsenal_currentLeftPanel") then { -1 } else {
    [WEAPON_PANEL_IDCS] find ace_arsenal_currentLeftPanel
};
private _equipped = "";

if (_weaponIndex != -1) then {
    // WEAPON_PANEL_IDCS is ordered to match IDX_CURR_PRIMARY_WEAPON_ITEMS ..
    // IDX_CURR_BINO_ITEMS, so the position is the offset.
    private _items = ace_arsenal_currentItems param [IDX_CURR_PRIMARY_WEAPON_ITEMS + _weaponIndex, []];
    _equipped = _items param [_slotIndex, ""];
};

[_slotIndex, _equipped]
