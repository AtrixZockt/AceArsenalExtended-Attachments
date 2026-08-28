#include "..\script_component.hpp"
#include "..\defines.hpp"
/*
 * Bring the right-hand option panel in line with whatever is selected.
 *
 * Idempotent: the controls are only rebuilt when the selected model changes, which
 * is what makes it safe to call from both onSelChangedRight and the deferred pass
 * in onRightPanelFilled.
 *
 * Arguments:
 * 0: Arsenal display <DISPLAY>
 *
 * Return Value:
 * None
 */

params ["_display"];

private _model = "";
private _class = "";

// GVAR(collapsed) is false when the collapse did not run -- the addon is switched
// off, the slot is not one it handles, or fnc_collapsePanel bailed. Offering
// dropdowns over a list that still holds every duplicate would be worse than
// offering none, so the panel stays down.
if (missionNamespace getVariable [QGVAR(enabled), true]
    && {GVAR(collapsed)}
    && {(call FUNC(currentSlot)) >= 0}) then {

    private _ctrl = _display displayCtrl IDC_rightTabContent;
    private _curSel = lbCurSel _ctrl;

    if (_curSel >= 0) then {
        // "" is ACE's <empty> row, which unequips rather than selecting an item.
        _class = _ctrl lbData _curSel;

        if (_class != "") then {
            _model = ["CfgWeapons", _class] call GEARINFO(getConfigModel);
        };
    };
};

if (_model != GVAR(currentModel)) then {
    [_display, _model] call FUNC(generateOptionsUI);
    GVAR(currentModel) = _model;
};

if (_model == "") exitWith {
    GVAR(currentModelOptions) = [];
};

GVAR(currentModelOptions) = ["CfgWeapons", _class, _model] call GEARINFO(getConfigOptions);

[_display] call FUNC(refreshCheckboxes);
