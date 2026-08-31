#include "..\script_component.hpp"
#include "..\defines.hpp"
/*
 * Show or hide the whole right-hand option panel.
 *
 * ACE hides the arsenal -- behind the loadouts screen, and for its own Hide
 * button -- with ace_arsenal_fnc_buttonHide, which ctrlShows a hardcoded list of
 * ACE's own IDCs. A third-party control is not in that list, so ours stays on
 * screen floating over whatever replaced the arsenal. Every addon that adds a
 * control to that display has to hide it itself; this is that.
 *
 * One ctrlShow does the whole panel: generateOptionsUI creates every value
 * control as a child of IDC_optionsGroup, and hiding a controls group hides its
 * children. Nothing touches geometry, so there is nothing to restore on the way
 * back -- the panel returns at whatever height it already had.
 *
 * Distinct from the height-0 teardown in generateOptionsUI: that is "nothing is
 * selected" and also resizes the list control back. This is "ACE hid the UI" and
 * must leave the layout exactly as it found it.
 *
 * Arguments:
 * 0: Show the panel <BOOL>
 *
 * Return Value:
 * None
 */

params ["_show"];

// Read back by generateOptionsUI. Its rebuild is deferred a frame, so it can in
// principle land while ACE has the UI hidden, and its unconditional ctrlShow
// would otherwise pop the panel back on over the loadouts screen.
GVAR(uiHidden) = !_show;

private _display = findDisplay IDD_ace_arsenal;
if (isNull _display) exitWith {};

private _configControl = _display displayCtrl IDC_optionsGroup;
_configControl ctrlShow _show;
_configControl ctrlCommit 0;
