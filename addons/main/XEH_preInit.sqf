#include "script_component.hpp"
ADDON = false;
#include "XEH_PREP.hpp"
ADDON = true;

// ---------------------------------------------------------------------------
// Right-panel option state.
//
// Deliberately separate from ACEAX's equivalents: both panels can hold a grouped
// item at the same time -- a merged weapon on the left, a merged optic on the
// right -- so sharing state with aceax_arsenal would make the two fight over it.
// ---------------------------------------------------------------------------

// Model currently shown in the right-hand option panel, "" when none.
GVAR(currentModel) = "";
// Option values of the currently selected attachment, index-aligned with the
// model's options[] array.
GVAR(currentModelOptions) = [];
// IDCs of the controls we created, so they can be deleted on the next refresh.
GVAR(valuesIdc) = [];
// value-control IDC -> [optionIndex, optionName, valueIndex, valueName]
GVAR(idcToConfig) = createHashMap;
// model -> the attachment classes that were actually in the listbox for the
// weapon currently selected. This is what restricts the dropdown to values that
// fit this weapon, and it is rebuilt on every fill.
GVAR(allowedItems) = createHashMap;
GVAR(adjustedHeight) = 0;

[
    QGVAR(enabled),
    "CHECKBOX",
    [LSTRING(SettingEnabled), LSTRING(SettingEnabledTip)],
    "ACE Arsenal Extended",
    true,
    true
] call CBA_fnc_addSetting;
