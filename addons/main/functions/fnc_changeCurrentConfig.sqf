#include "..\script_component.hpp"
#include "..\defines.hpp"
/*
 * Swap the selected item for the variant the clicked value asks for.
 *
 * Mirrors aceax_arsenal_fnc_changeCurrentConfig: replace one value in the current
 * option tuple, resolve it to a class, then rewrite the selected row and re-enter
 * the selection handler so ACE equips it. Doing it through the listbox rather than
 * calling addWeaponItem directly means ACE stays the single owner of what is
 * actually on the weapon -- and it is what lets the same code swap a magazine,
 * since ACE's handler already knows what the current panel does with a click.
 *
 * Arguments:
 * 0: Arsenal display <DISPLAY>
 * 1: [option index, option name, value index, value name] <ARRAY>
 *
 * Return Value:
 * None
 */

params ["_display", "_data"];
_data params ["_optionIndex", "", "", "_valueName"];

if ((GVAR(currentModelOptions) param [_optionIndex, ""]) == _valueName) exitWith {};

private _model = GVAR(currentModel);
if (_model == "") exitWith {};

private _root = GVAR(currentRoot);
if (_root == "") exitWith {};

private _options = +GVAR(currentModelOptions);
_options set [_optionIndex, _valueName];

private _match = [_root, _model, _options] call GEARINFO(findConfig);

if (isNull _match) then {
    _match = [_root, _model, _optionIndex, _valueName] call GEARINFO(findConfigByValue);
};

if (isNull _match) exitWith {
    ERROR_2("Nothing found for %1 %2",_model,_options);
};

private _newValue = configName _match;

// The variant has to be one the current weapon can actually take -- an optic it
// accepts, or a magazine it chambers. getModelOptions already restricts the
// offered values to GVAR(allowedItems), so this should not fire -- but
// findConfigByValue searches every variation of the model, including ones that
// were filtered out of this list, so it is worth refusing rather than equipping
// something incompatible.
private _allowed = GVAR(allowedItems) getOrDefault [_model, []];
if (_allowed isNotEqualTo [] && {!(_newValue in _allowed)}) exitWith {
    TRACE_2("Resolved variant is not compatible with the selected weapon",_newValue,_model);
};

private _ctrlPanel = _display displayCtrl IDC_rightTabContent;
private _i = lbCurSel _ctrlPanel;

if (_i < 0) exitWith {};

private _config = configFile >> _root >> _newValue;
private _displayName = getText (_config >> "displayName");

_ctrlPanel lbSetData [_i, _newValue];
_ctrlPanel lbSetText [_i, _displayName];
_ctrlPanel lbSetTooltip [_i, format ["%1\n%2", _displayName, _newValue]];
_ctrlPanel lbSetPicture [_i, getText (_config >> "picture")];

// Rewriting the row's data does not fire LBSelChanged -- the selected index has
// not changed -- so ACE is asked to equip the swapped-in class directly. Doing it
// through ACE rather than calling addWeaponItem here keeps it the single owner of
// what is actually on the weapon.
[_ctrlPanel, _i] call ace_arsenal_fnc_onSelChangedRight;

[_display] call FUNC(refreshOptions);
