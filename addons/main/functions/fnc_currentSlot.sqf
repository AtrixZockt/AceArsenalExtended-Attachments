#include "..\script_component.hpp"
#include "..\defines.hpp"
/*
 * Which attachment slot the right panel is showing.
 *
 * Arguments:
 * None
 *
 * Return Value:
 * Slot index -- 0=muzzle 1=pointer 2=optic 3=bipod -- or -1 if the right panel is
 * showing something else (magazines, grenades, a container's contents). <NUMBER>
 */

// ACE nils this when the arsenal closes, and the collapse runs a frame late, so it
// can land after that even though the display check passed.
if (isNil "ace_arsenal_currentRightPanel") exitWith { -1 };

[ATTACHMENT_SLOT_IDCS] find ace_arsenal_currentRightPanel
