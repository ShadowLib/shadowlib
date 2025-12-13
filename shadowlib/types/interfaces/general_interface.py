import shadowlib.utilities.timing as timing
from shadowlib.client import client
from shadowlib.types.box import Box
from shadowlib.types.widget import Widget, WidgetFields


class GeneralInterface:
    """
    Interface-type class for scroll-like interfaces with optional scrollbox support.
    """

    def __init__(
        self,
        group: int,
        button_ids: list[int],
        get_children: bool = True,
        wrong_text: str = "5f5f5d",
        menu_text: str | None = None,
        scrollbox: int | None = None,
        max_scroll: int = 10,
    ):
        self.group = group
        self.get_children = get_children
        self.wrong_text = wrong_text
        self.menu_text = menu_text
        self.max_scroll = max_scroll
        self.scrollbox_bounds: Box | None = None

        # Cache scrollbox bounds once if provided
        if scrollbox:
            w = Widget(scrollbox).enable(WidgetFields.getBounds)
            bounds = w.get().get("bounds", [0, 0, 0, 0])
            if bounds[2] > 0 and bounds[3] > 0:
                self.scrollbox_bounds = Box.fromRect(*bounds)

        self.buttons = []
        for button_id in button_ids:
            button = Widget(button_id)
            button.enable(WidgetFields.getBounds)
            button.enable(WidgetFields.getText)
            self.buttons.append(button)

    def getWidgetInfo(self) -> list:
        if self.get_children:
            return Widget.getBatchChildren(self.buttons)
        return Widget.getBatch(self.buttons)

    def isOpen(self) -> bool:
        return self.group in client.interfaces.getOpenInterfaces()

    def isRightOption(self, widget_info: dict, option_text: str = "") -> bool:
        widget_text = widget_info.get("text", "")
        if option_text:
            return option_text in widget_text and self.wrong_text not in widget_text
        return widget_text and self.wrong_text not in widget_text

    def _scroll(self, up: bool = False) -> None:
        """Scroll in the scrollbox area."""
        if self.scrollbox_bounds:
            self.scrollbox_bounds.hover()
            client.input.mouse.scroll(up=up, count=1)
            timing.sleep(0.1)

    def _isVisible(self, bounds: list) -> bool:
        """Check if bounds are visible within scrollbox."""
        if not self.scrollbox_bounds or bounds[2] <= 0 or bounds[3] <= 0:
            return bounds[2] > 0 and bounds[3] > 0
        return self.scrollbox_bounds.contains(Box.fromRect(*bounds))

    def interact(self, option_text: str = "", index: int = -1) -> bool:
        if not self.isOpen():
            return False

        for _ in range(self.max_scroll + 1):
            info = self.getWidgetInfo()

            # Index-based interaction
            if 0 <= index < len(info):
                w = info[index]
                bounds = w.get("bounds", [0, 0, 0, 0])
                if not self._isVisible(bounds):
                    self._scroll(up=False)
                    continue
                if self.isRightOption(w, option_text):
                    return Box.fromRect(*bounds).clickOption(self.menu_text)
                return False

            # Text-based interaction
            if option_text:
                for widget_info in info:
                    if self.isRightOption(widget_info, option_text):
                        bounds = widget_info.get("bounds", [0, 0, 0, 0])
                        if not self._isVisible(bounds):
                            continue
                        menu = self.menu_text if self.menu_text else option_text
                        return Box.fromRect(*bounds).clickOption(menu)

                if self.scrollbox_bounds:
                    self._scroll(up=False)
                    continue
                print(f"Option '{option_text}' not found in interface.")
                return False

            print("No valid option_text or index provided.")
            return False

        print(f"Max scroll attempts ({self.max_scroll}) reached.")
        return False
