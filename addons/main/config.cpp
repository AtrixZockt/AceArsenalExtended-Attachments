#include "script_component.hpp"

class CfgPatches {
    class ADDON {
        name = "ACEAX Attachments";
        units[] = {};
        weapons[] = {};
        requiredVersion = REQUIRED_VERSION;
        // Genuine dependencies, unlike a compat addon: this is useless without
        // ACEAX, and it MUST load after aceax_arsenal so that our
        // ace_arsenal_rightPanelFilled handler registers after ACEAX's.
        requiredAddons[] = {"ace_arsenal", "aceax_arsenal", "aceax_gearinfo"};
        author = "DiGii";
        VERSION_CONFIG;
    };
};

#include "CfgEventHandlers.hpp"

#include "defines.hpp"

class RscControlsGroup;
class RscText;
class RscCheckBox;
class RscPicture;
class RscPictureKeepAspect;
class RscButton;

class ace_arsenal_display {
    class controls {
        // ACE's own controls are deliberately NOT patched here.
        //
        // An earlier version added a single property to rightTabContent:
        //
        //     class rightTabContent { onLBSelChanged = ...; };
        //
        // Re-declaring an existing class without restating its parent RESETS that
        // parent. ACE defines `rightTabContent: leftTabContent`, so this quietly
        // turned it into a class with no base at all -- losing its type, style and
        // geometry. The RPT said so plainly:
        //
        //     Updating base class 'leftTabContent'->'', by '...aceaxatt_main'
        //     Warning: no type entry inside class
        //              ace_arsenal_display/controls/rightTabContent
        //
        // and the arsenal's whole attachment panel rendered as nothing.
        //
        // Restating the parent would fix it, but doing config surgery on another
        // mod's control means the last addon to patch it wins. The selection
        // handler is attached at runtime instead -- see XEH_preInit.sqf --
        // which adds alongside ACE's rather than replacing it.
        //
        // The grey model label fnc_labelPanel writes needs no patch here either:
        // ACE declares `rightTabContent: leftTabContent` and does not restate
        // colorTextRight, so the panel inherits ACEAX's {0.5,0.5,0.5,1} from its
        // fork of leftTabContent rather than ACE's own alpha-0 default.
        //
        // Only NEW classes below this line.

        // Mirror of ACEAX's leftTabCustom, on the right-hand column.
        // rightTabContent sits at safeZoneX + safeZoneW - 93 grid units and is
        // 80 wide, ending 28 units above the bottom (ACE's leftTabContent ends
        // at 24.5), so the numbers below differ from ACEAX's by that offset.
        class GVAR(rightTabCustom): RscControlsGroup {
            idc = IDC_optionsGroup;

            colorBackground[] = {255,255,255,255};
            x = QUOTE(safezoneX + safezoneW - 93 * GRID_W);
            y = QUOTE((safezoneY + 14 * GRID_H) + (safezoneH - 28 * GRID_H));
            w = QUOTE(80 * GRID_W);
            h = 0;
            sizeEx = QUOTE(7 * GRID_H);

            class controls {
                class Title: RscText {
                    idc = IDC_optionsLabel;
                    sizeEx = QUOTE(7 * GRID_H);
                    shadow = 0;
                    text = "Label";
                    x = QUOTE(0 * GRID_W);
                    y = QUOTE(0 * GRID_H);
                    w = QUOTE(80 * GRID_W);
                    h = QUOTE(7 * GRID_H);
                };

                class ModTitle: RscText {
                    idc = IDC_optionsAuthor;
                    sizeEx = QUOTE(4 * GRID_H);
                    shadow = 0;
                    text = "Author";
                    x = QUOTE(0 * GRID_W);
                    y = QUOTE(7 * GRID_H);
                    w = QUOTE(80 * GRID_W);
                    h = QUOTE(4 * GRID_H);
                };
            };
        };
    };
};

// Control templates created at runtime by fnc_generateOptionsUI. Deliberately
// styled to match ACEAX's so both option panels look like one feature.
class GVAR(configTitle): RscText {
    sizeEx = QUOTE(5 * GRID_H);
    shadow = 0;
    text = "Label";
    x = QUOTE(0 * GRID_W);
    y = QUOTE(0 * GRID_H);
    w = QUOTE(80 * GRID_W);
    h = QUOTE(5 * GRID_H);
};

class GVAR(valueImage): RscPicture {
    text = "";
    x = QUOTE(0 * GRID_W);
    y = QUOTE(0 * GRID_H);
    w = QUOTE(19.5 * GRID_W);
    h = QUOTE(10 * GRID_H);
    colorBackground[] = {0,0,0,1};
    style = 144;
    tileH = 0.5128;
    tileW = 1;
};

class GVAR(valueImageCenterSquare): RscPictureKeepAspect {
    text = "";
    x = QUOTE(0 * GRID_W);
    y = QUOTE(0 * GRID_H);
    w = QUOTE(19.5 * GRID_W);
    h = QUOTE(10 * GRID_H);
    colorBackground[] = {0,0,0,1};
};

class GVAR(valueCheckbox): RscCheckBox {
    x = QUOTE(0 * GRID_W);
    y = QUOTE(0 * GRID_H);
    w = QUOTE(19.5 * GRID_W);
    h = QUOTE(10 * GRID_H);
    // Reuse ACEAX's checkbox art rather than shipping a duplicate copy; the
    // addon is a hard dependency so the paths are guaranteed to resolve.
    textureChecked = "\z\aceax\addons\arsenal\data\ui\checked.paa";
    textureUnchecked = "\z\aceax\addons\arsenal\data\ui\unchecked.paa";
    textureFocusedChecked = "\z\aceax\addons\arsenal\data\ui\checked.paa";
    textureFocusedUnchecked = "\z\aceax\addons\arsenal\data\ui\unchecked.paa";
    textureHoverChecked = "\z\aceax\addons\arsenal\data\ui\checked.paa";
    textureHoverUnchecked = "\z\aceax\addons\arsenal\data\ui\unchecked.paa";
    texturePressedChecked = "\z\aceax\addons\arsenal\data\ui\checked.paa";
    texturePressedUnchecked = "\z\aceax\addons\arsenal\data\ui\unchecked.paa";
    textureDisabledChecked = "\z\aceax\addons\arsenal\data\ui\disabled.paa";
    textureDisabledUnchecked = "\z\aceax\addons\arsenal\data\ui\disabled.paa";
    colorDisabled[] = {0.1, 0.1, 0.1, 0.5};
    colorBackgroundDisabled[] = {0.6, 0.6, 0.6, 0.25};
};

class GVAR(valueButton): RscButton {
    text = "Label";
    sizeEx = QUOTE(5 * GRID_H);
    x = QUOTE(0 * GRID_W);
    y = QUOTE(0 * GRID_H);
    w = QUOTE(19.5 * GRID_W);
    h = QUOTE(10 * GRID_H);

    colorText[] = {EXACT_MATCH_TEXT_COLOR};
    colorBackground[] = {INVISIBLE_COLOR};
    colorFocused[] = {INVISIBLE_COLOR};
    colorShadow[] = {INVISIBLE_COLOR};
    colorBorder[] = {INVISIBLE_COLOR};
    colorBackgroundActive[] = {ACTIVE_BG_COLOR};
    colorDisabled[] = {DISABLED_TEXT_COLOR};
    colorBackgroundDisabled[] = {INVISIBLE_COLOR};
};

VERSIONING
