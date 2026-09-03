#include "..\script_component.hpp"
#include "..\defines.hpp"
/*
 * Write the model label into the right-hand text of every collapsed row.
 *
 * The same hint ACEAX gives on the left panel: a small grey string on rows that
 * stand for a family rather than a single item, so it is visible from the list
 * alone that the option panel underneath has something to offer.
 *
 * It is the LISTBOX ROW's own right-aligned text, not a second control --
 * aceax_arsenal_fnc_sortPanel does exactly this on IDC_leftTabContent. The grey
 * comes from `colorTextRight[] = {0.5,0.5,0.5,1}`, which ACEAX sets on its fork of
 * ace_arsenal_display's leftTabContent; ACE declares `rightTabContent: leftTabContent`
 * without restating the property, so this panel inherits ACEAX's value rather than
 * ACE's own {0.5,0.5,0.5,0} -- alpha 0, because stock ACE uses the slot only as a
 * hidden sort key. `colorSelect2Right[] = {0,0,0,1}` comes down the same chain and
 * flips the label to black on the selected (white) row. aceax_arsenal is a hard
 * requiredAddon, so both are always present.
 *
 * MUST run after ACE has sorted the panel. ACE calls fnc_fillSort at the end of
 * fnc_fillRightPanel -- after the rightPanelFilled event we collapse in -- and its
 * sort writes a sort key into every row's right text and then clears it. Anything
 * written during the collapse is gone by the end of the same frame. See the callers:
 * both defer by a frame.
 *
 * Idempotent, and cheap enough to be: one getConfigModel per row, one config read per
 * distinct model.
 *
 * Arguments:
 * 0: Arsenal display <DISPLAY>
 *
 * Return Value:
 * None
 */

params ["_display"];

// Covers every reason there is nothing to advertise: the addon is switched off, the
// panel is not one we handle, or fnc_collapsePanel bailed. Labelling a list that still
// holds every duplicate would promise dropdowns that are not there.
if !(GVAR(collapsed)) exitWith {};

private _root = call FUNC(currentPanelRoot);
if (_root == "") exitWith {};

private _ctrl = _display displayCtrl IDC_rightTabContent;
private _size = lbSize _ctrl;

// model -> the string to write, "" for "this one gets no label".
private _labels = createHashMap;

for "_i" from 0 to (_size - 1) do {
    private _label = "";
    private _class = _ctrl lbData _i;

    if (_class != "") then {
        private _model = [_root, _class] call GEARINFO(getConfigModel);

        if (_model != "") then {
            _label = _labels getOrDefaultCall [_model, {
                // Only when this weapon can actually take a second variant.
                //
                // allowedItems holds the classes ACE listed for the selected weapon,
                // so this is the same test fnc_generateOptionsUI applies when deciding
                // whether an option is worth drawing: with a single allowed item every
                // axis narrows to one value and the panel stays empty. Attachment mods
                // hit that constantly -- Tier One ships 23 classes all called "LA-5B",
                // one per weapon platform, of which exactly one ever fits -- and
                // labelling those would just repeat the item's own name.
                if (count (GVAR(allowedItems) getOrDefault [_model, []]) > 1) then {
                    getText (configFile >> "XtdGearModels" >> _root >> _model >> "label")
                } else {
                    ""
                }
            }, true];
        };
    };

    // Written even when empty, which is what clears ACE's leftover sort key from the
    // <empty> row: its ascending pass parks five HIGHEST_VALUE_CHAR glyphs there and
    // its cleanup loop skips rows whose lbData is "", so ACE never takes them back off.
    // Harmless at ACE's alpha 0; not necessarily at the alpha 1 this panel inherits.
    _ctrl lbSetTextRight [_i, _label];
};
