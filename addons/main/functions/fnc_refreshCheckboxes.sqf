#include "..\script_component.hpp"
#include "..\defines.hpp"
/*
 * Tick the value matching the selected attachment and grey out the unreachable ones.
 *
 * Same rules as aceax_arsenal_fnc_refreshCheckboxes: a value is enabled if
 * swapping to it produces an exact config match, or -- for a model declaring
 * alwaysSelectable -- if the weak-match fallback can find something holding it.
 *
 * Arguments:
 * 0: Arsenal display <DISPLAY>
 *
 * Return Value:
 * None
 */

params ["_display"];

private _model = GVAR(currentModel);
if (_model == "") exitWith {};

private _modelDefinition = configFile >> "XtdGearModels" >> "CfgWeapons" >> _model;
private _allowedItems = GVAR(allowedItems) getOrDefault [_model, []];

private _options = ["CfgWeapons", _model, _modelDefinition, "options", _allowedItems] call GEARINFO(getModelOptions);

{
    private _optionIndex = _forEachIndex;
    _x params ["", "", "", "", "_values", "", "_alwaysSelectable"];

    // Single-value options are not drawn (see fnc_generateOptionsUI), so there are
    // no controls to refresh. The index is still consumed, to stay aligned.
    if ((count _values) < 2) then { continue };

    private _currentValue = GVAR(currentModelOptions) param [_optionIndex, ""];

    {
        private _valueIndex = _forEachIndex;
        _x params ["_valueName"];

        private _valueIdcBase = IDC_OPTION_VALUE_BASE + (_optionIndex * 1000) + (_valueIndex * 4);

        private _previewOptions = +GVAR(currentModelOptions);
        _previewOptions set [_optionIndex, _valueName];

        private _checkbox = _display displayCtrl (_valueIdcBase + 1);
        private _button = _display displayCtrl (_valueIdcBase + 2);

        // generateOptionsUI skips values filtered out by `faction`, so a control
        // for this index may not exist.
        if (isNull _checkbox || {isNull _button}) then { continue };

        private _exactMatch = !isNull (["CfgWeapons", _model, _previewOptions] call GEARINFO(findConfig));

        private _enabled = if (!_alwaysSelectable) then { _exactMatch } else {
            if (_exactMatch) then { true } else {
                !isNull (["CfgWeapons", _model, _optionIndex, _valueName] call GEARINFO(findConfigByValue))
            };
        };

        if (_alwaysSelectable) then {
            _button ctrlSetBackgroundColor ([[WEAK_MATCH_BG_COLOR], [INVISIBLE_COLOR]] select _exactMatch);
        };

        _button ctrlSetTextColor ([[WEAK_MATCH_TEXT_COLOR], [EXACT_MATCH_TEXT_COLOR]] select _exactMatch);
        _button ctrlEnable _enabled;
        _button ctrlCommit 0.1;

        _checkbox cbSetChecked (_valueName == _currentValue);
        _checkbox ctrlEnable _enabled;
        _checkbox ctrlCommit 0;
    } forEach _values;
} forEach _options;
