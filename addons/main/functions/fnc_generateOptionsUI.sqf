#include "..\script_component.hpp"
#include "..\defines.hpp"
/*
 * Build (or tear down) the option controls under the right panel.
 *
 * Mirrors aceax_arsenal_fnc_generateOptionsUI, with three differences:
 *   - it uses the right-hand column's geometry, which is 28 grid units short at
 *     the bottom rather than the left column's 24.5;
 *   - it uses the IDC block reserved in defines.hpp, because ACEAX's panel can be
 *     showing a grouped weapon at the same moment;
 *   - there is no "textureoptions" pass. Those apply a hiddenSelection to worn
 *     gear via setObjectTexture; an attachment is not worn and has none.
 *
 * Arguments:
 * 0: Arsenal display <DISPLAY>
 * 1: Model to show, "" to hide the panel <STRING>
 *
 * Return Value:
 * None
 */

params ["_display", ["_model", ""]];

private _configControl = _display displayCtrl IDC_optionsGroup;
private _listControl = _display displayCtrl IDC_rightTabContent;

// Remove previous controls if any
{ ctrlDelete (_display displayCtrl _x); } forEach GVAR(valuesIdc);
GVAR(valuesIdc) = [];
GVAR(idcToConfig) = createHashMap;

if (_model == "") exitWith {
    _listControl ctrlSetPositionH (safeZoneH - 28 * GRID_H);
    _configControl ctrlSetPositionY ((safeZoneY + 14 * GRID_H) + (safeZoneH - 28 * GRID_H));
    _configControl ctrlSetPositionH 0;
    _listControl ctrlCommit 0.2;
    _configControl ctrlCommit 0.2;
};

private _modelDefinition = configFile >> "XtdGearModels" >> "CfgWeapons" >> _model;

(_display displayCtrl IDC_optionsLabel) ctrlSetText getText (_modelDefinition >> "label");
(_display displayCtrl IDC_optionsAuthor) ctrlSetText getText (_modelDefinition >> "author");

// Only the attachments that were actually in the list for this weapon. ACEAX's
// getModelOptions intersects the model's declared values[] with the options of
// these classes, so a dropdown never offers a variant the selected weapon cannot
// take.
private _allowedItems = GVAR(allowedItems) getOrDefault [_model, []];

private _posY = 12;
private _currentFaction = if (!isNull player) then { faction player } else { "" };

private _options = ["CfgWeapons", _model, _modelDefinition, "options", _allowedItems] call GEARINFO(getModelOptions);

{
    private _optionIndex = _forEachIndex;
    _x params ["_optionName", "_optionLabel", "", "", "_values", "_optionCenterImage"];

    private _titleIdc = IDC_OPTION_TITLE_BASE + _optionIndex;
    GVAR(valuesIdc) pushBack _titleIdc;

    private _ctrl = _display ctrlCreate [QGVAR(configTitle), _titleIdc, _configControl];
    _ctrl ctrlSetPosition [0, _posY * GRID_H];
    _ctrl ctrlSetText _optionLabel;
    _ctrl ctrlCommit 0;

    private _posX = 0;
    _posY = _posY + 6;

    {
        private _valueIndex = _forEachIndex;
        _x params ["_valueName", "_valueLabel", "_valueImage", "", "_valueDesc", "_factionFilter"];

        // Hide value if faction is provided and doesn't match, but ignore civilians
        if (count _factionFilter != 0 && {!(_currentFaction in ["", "CIV_F"])}) then {
            if (!(_currentFaction in _factionFilter)) then { continue };
        };

        // up to 40 options, up to 250 values per option
        private _valueIdcBase = IDC_OPTION_VALUE_BASE + (_optionIndex * 1000) + (_valueIndex * 4);

        GVAR(valuesIdc) pushBack _valueIdcBase;
        GVAR(valuesIdc) pushBack (_valueIdcBase + 1);
        GVAR(valuesIdc) pushBack (_valueIdcBase + 2);

        GVAR(idcToConfig) set [_valueIdcBase, [_optionIndex, _optionName, _valueIndex, _valueName]];

        private _ctrl = _display ctrlCreate [
            [QGVAR(valueImage), QGVAR(valueImageCenterSquare)] select (_optionCenterImage > 0),
            _valueIdcBase,
            _configControl
        ];
        _ctrl ctrlSetPosition [_posX * GRID_W, _posY * GRID_H];
        _ctrl ctrlSetText _valueImage;
        _ctrl ctrlCommit 0;

        _ctrl = _display ctrlCreate [QGVAR(valueCheckbox), _valueIdcBase + 1, _configControl];
        _ctrl ctrlSetPosition [_posX * GRID_W, _posY * GRID_H];
        _ctrl ctrlCommit 0;

        _ctrl = _display ctrlCreate [QGVAR(valueButton), _valueIdcBase + 2, _configControl];
        _ctrl ctrlSetPosition [_posX * GRID_W, _posY * GRID_H];
        _ctrl ctrlSetText _valueLabel;
        _ctrl ctrlSetTooltip _valueDesc;
        _ctrl ctrlAddEventHandler ["ButtonClick", {
            [ctrlParent (_this select 0), _this select 0] call FUNC(onValueButton);
        }];
        _ctrl ctrlCommit 0;

        _posX = _posX + 20;
        if (_posX == 80) then {
            _posX = 0;
            _posY = _posY + 10;
        };
    } forEach _values;

    if (_posX != 0) then { _posY = _posY + 10 };
    _posY = _posY + 2;
} forEach _options;

GVAR(adjustedHeight) = 120 min (_posY + 10);

// Shrink the list to make room. The extra 4 units are the gap ACEAX leaves
// between the list and the option block.
_listControl ctrlSetPositionH (safeZoneH - (GVAR(adjustedHeight) + 32) * GRID_H);
_configControl ctrlSetPositionY ((safeZoneY + 14 * GRID_H) + (safeZoneH - (GVAR(adjustedHeight) + 28) * GRID_H));
_configControl ctrlSetPositionH (GVAR(adjustedHeight) * GRID_H);
_configControl ctrlShow true;
_listControl ctrlCommit 0.2;
_configControl ctrlCommit 0.2;

// Same workaround ACEAX needs: resizing the listbox does not refresh its
// scrollbar, which leaves rows at the bottom unreachable until something else
// forces an update.
[{
    params ["_listControl", "_configControl"];
    if (GVAR(currentModel) != "") then {
        _listControl ctrlSetPositionH (safeZoneH - (GVAR(adjustedHeight) + 32) * GRID_H);
        _configControl ctrlSetPositionY ((safeZoneY + 14 * GRID_H) + (safeZoneH - (GVAR(adjustedHeight) + 28) * GRID_H));
        _configControl ctrlSetPositionH (GVAR(adjustedHeight) * GRID_H);
        _listControl ctrlCommit 0;
        _configControl ctrlCommit 0;
    };
}, [_listControl, _configControl], 1] call CBA_fnc_waitAndExecute;
