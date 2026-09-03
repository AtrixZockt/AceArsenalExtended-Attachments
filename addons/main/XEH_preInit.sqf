#include "script_component.hpp"
#include "defines.hpp"
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
// True between a fill and the work that has to happen after ACE has sorted the
// panel -- and set ONLY in the Eden Editor, which has no frame to defer to. See
// fnc_onRightPanelFilled for why, and fnc_onSelChangedRight for what consumes it.
GVAR(edenPending) = false;
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

// ---------------------------------------------------------------------------
// Arsenal hooks.
//
// These live in preInit rather than postInit because postInit NEVER RUNS IN THE
// EDEN EDITOR, and ACE's arsenal opens there.
//
// CBA fires Extended_PostInit_EventHandlers only from CBA_fnc_postInit, which is
// declared `postInit = 1` in cba_xeh's CfgFunctions -- so the engine calls it once
// a mission initialises, and 3DEN is not a mission. In the editor CBA instead runs
// cba_xeh_fnc_initDisplay3DEN, which hangs MouseMoving/MouseHolding watchdogs on
// the editor display that call CBA_fnc_preInit, and preInit ONLY. Nothing in CBA
// reaches postInit from 3DEN at all.
//
// The symptom was as quiet as that implies: preInit still ran, so every function
// was compiled and every GVAR set, but not one event was subscribed. No collapse,
// no option panel, and nothing in the RPT to say why. ACEAX works in the editor
// precisely because it registers in preInit (aceax_arsenal's XEH_preInit.sqf).
//
// Registering here loses nothing. The previous comment justified postInit as
// "runs after every addon's preInit, so this fires after ACEAX's own
// rightPanelFilled handler regardless of load order" -- that ordering still holds,
// by a different route: CfgPatches requires aceax_arsenal, which puts our class
// after ACEAX's in Extended_PreInit_EventHandlers, and CBA_fnc_compileEventHandlers
// walks that with configProperties -- in config order -- for CBA_fnc_preInit to
// execute in turn. The coupling is weak in any case: ACEAX's only rightPanelFilled
// handler applies texture options to the 3D preview and never touches the listbox.
// ---------------------------------------------------------------------------

// Hook the right panel's selection event at RUNTIME rather than in config.
//
// ctrlAddEventHandler adds a handler alongside the control's config-defined
// onLBSelChanged; it does not replace it (that is ctrlSetEventHandler). So ACE's
// own handler still runs and still equips the item, and this one only rebuilds the
// option panel.
//
// Which of the two the engine calls FIRST is deliberately not relied on anywhere.
// It is not documented, and an earlier version that assumed ACE went first read
// ace_arsenal_currentItems here and showed the previous attachment until you clicked
// twice -- see TESTING.md, "the third live failure". Handlers on this control take
// their answer from the arguments they are handed, which is also how ACE hooks
// controls it does not own (ace_inventory_fnc_onLBSelChanged).
//
// The alternative -- patching `class rightTabContent` in config -- is what broke
// the panel entirely the first time round: re-declaring an existing class without
// restating its parent resets that parent, and the control lost its listbox type.
// Attaching at runtime touches no ACE class at all, so it cannot break inheritance
// and cannot fight another addon hooking the same control.
["ace_arsenal_displayOpened", {
    params ["_display"];

    private _ctrl = _display displayCtrl IDC_rightTabContent;

    // 5 is CT_LISTBOX. A null control, or one that is not a listbox, means
    // something has broken rightTabContent -- most likely an addon patching it in
    // config without restating its parent. Naming it here turns a silently blank
    // panel into one line in the RPT.
    if (isNull _ctrl) exitWith {
        ERROR("rightTabContent (idc 14) not found -- attachment merging disabled for this session");
    };

    if (ctrlType _ctrl != 5) exitWith {
        ERROR_1("rightTabContent is not a listbox (ctrlType %1) -- another addon has probably reset its base class; attachment merging disabled for this session",ctrlType _ctrl);
    };

    _ctrl ctrlAddEventHandler ["LBSelChanged", {
        _this call FUNC(onSelChangedRight);
    }];

    // Re-label after a sort. ACE's sortPanel uses each row's right-hand text as a
    // sort key and clears it when it is done, so changing either sort combo wipes
    // the model labels; this puts them back. ACEAX solves the same problem on the
    // left by forking sortLeftTab in config and re-writing the labels after calling
    // ACE's sort -- and ACE's sortRightTab inherits from sortLeftTab, so ACEAX's
    // handler is already what runs here, bailing out for the right-hand IDCs.
    //
    // Deferred a frame rather than ordered against it: as with the listbox above,
    // which handler the engine calls first is not documented, so the work is simply
    // put beyond the reach of both. The two combos also fire during ACE's own
    // fillSort, which is why labelPanel is idempotent.
    {
        private _sortCtrl = _display displayCtrl _x;

        if (isNull _sortCtrl) then {
            ERROR_1("sort control (idc %1) not found -- model labels will not survive a re-sort",_x);
        } else {
            _sortCtrl ctrlAddEventHandler ["LBSelChanged", {
                params ["_control"];

                [{
                    params ["_display"];
                    if (isNull _display) exitWith {};

                    [_display] call FUNC(labelPanel);
                }, [ctrlParent _control]] call CBA_fnc_execNextFrame;
            }];
        };
    } forEach [IDC_sortRightTab, IDC_sortRightTabDirection];
}] call CBA_fnc_addEventHandler;

["ace_arsenal_rightPanelFilled", {
    _this call FUNC(onRightPanelFilled);
}] call CBA_fnc_addEventHandler;

// ---------------------------------------------------------------------------
// Hide the option panel whenever ACE hides the arsenal.
//
// ace_arsenal_fnc_buttonHide ctrlShows a hardcoded list of ACE's own IDCs, so it
// never touches ours -- without these the panel floats on top of the loadouts
// screen. See fnc_toggleUI.
// ---------------------------------------------------------------------------
["ace_arsenal_loadoutsDisplayOpened", { [false] call FUNC(toggleUI); }] call CBA_fnc_addEventHandler;
["ace_arsenal_loadoutsDisplayClosed", { [true] call FUNC(toggleUI); }] call CBA_fnc_addEventHandler;

// Also covers the Hide button (idc 1002) and its BACKSPACE keybind, which the
// two events above miss -- buttonHide is called from all three places.
//
// Newer ACE than the loadouts events (added 2026-02-12, ACE #11285), so it is an
// addition to them rather than a replacement: on an older ACE it simply never
// fires and the loadouts case is still handled. On the loadouts path both fire;
// that is harmless, since they set the same state and ctrlShow is idempotent.
["ace_arsenal_showToggle", {
    params ["", "_show"];
    [_show] call FUNC(toggleUI);
}] call CBA_fnc_addEventHandler;

// Nothing is grouped once the arsenal is gone; drop the state so a stale model
// cannot leak into the next session.
["ace_arsenal_displayClosed", {
    GVAR(currentModel) = "";
    GVAR(currentRoot) = "";
    GVAR(currentModelOptions) = [];
    GVAR(valuesIdc) = [];
    GVAR(idcToConfig) = createHashMap;
    GVAR(allowedItems) = createHashMap;
    GVAR(collapsed) = false;
    GVAR(edenPending) = false;
    // Closing the arsenal from the loadouts screen leaves this set. Without the
    // reset the panel would stay hidden for the rest of the session, because
    // nothing raises a show event on the way back in.
    GVAR(uiHidden) = false;
}] call CBA_fnc_addEventHandler;
