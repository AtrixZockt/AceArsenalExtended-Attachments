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
// Config root that model came from -- "CfgWeapons" for an attachment,
// "CfgMagazines" for a magazine, "" when none. Every ACEAX gearinfo lookup needs
// it, and it is set once per refresh rather than re-derived at each call site.
GVAR(currentRoot) = "";
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
// False when the collapse did not run -- switched off, a slot we do not handle, or
// fnc_collapsePanel bailed. The option panel stays down in that case: dropdowns over
// a list that still holds every duplicate would be worse than no dropdowns.
GVAR(collapsed) = false;
GVAR(adjustedHeight) = 0;
// True while ACE has the arsenal UI hidden -- the loadouts screen, or its own
// Hide button. Ours is a third-party control, so ACE's hide pass does not know
// about it and we track the state ourselves; see fnc_toggleUI.
GVAR(uiHidden) = false;

[
    QGVAR(enabled),
    "CHECKBOX",
    [LSTRING(SettingEnabled), LSTRING(SettingEnabledTip)],
    "ACE Arsenal Extended",
    true,
    true
] call CBA_fnc_addSetting;

// This addon patches a control belonging to someone else's mod, so when it goes
// wrong the useful question is always "what did the collapse actually see". Worth
// a permanent toggle rather than a debug build.
[
    QGVAR(debug),
    "CHECKBOX",
    [LSTRING(SettingDebug), LSTRING(SettingDebugTip)],
    "ACE Arsenal Extended",
    false,
    true
] call CBA_fnc_addSetting;
