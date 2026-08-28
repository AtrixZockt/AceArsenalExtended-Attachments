#include "..\script_component.hpp"
#include "..\defines.hpp"
/*
 * ace_arsenal_rightPanelFilled -- schedule the collapse for the next frame.
 *
 * ACE raises this event partway through fnc_fillRightPanel: after the list is
 * built, but BEFORE it calls fillSort (which re-sorts the panel) and before it
 * restores the previous selection. Doing the work here means interleaving with all
 * of that, which is what the first version tried and got wrong.
 *
 * Deferring by one frame means ACE has completely finished. The panel is sorted,
 * the selection is restored, and nothing of ACE's runs afterwards -- so the row to
 * keep is simply the selected one, and there is no ordering to reason about.
 *
 * The cost is one frame showing the un-collapsed list, which is imperceptible and
 * is already true of the option panel.
 *
 * Arguments:
 * 0: Arsenal display <DISPLAY>
 * 1: Current left panel IDC <NUMBER>
 * 2: Current right panel IDC <NUMBER>
 *
 * Return Value:
 * None
 */

params ["_display"];

[{
    params ["_display"];
    if (isNull _display) exitWith {};

    [_display] call FUNC(collapsePanel);
    [_display] call FUNC(refreshOptions);
}, [_display]] call CBA_fnc_execNextFrame;
