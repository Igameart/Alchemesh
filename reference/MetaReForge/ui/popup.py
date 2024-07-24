import bpy

def PopupMessage(
        message: str = "",
        title: str = "Message Box",
        icon: str = 'INFO',
        align: bool = True
) -> None:

    def draw(self, context):
        col = self.layout.column(align=align)
        lines = message.split("\n")
        for line in lines:
            col.label(text=line)

    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)

if __name__ == "__main__":
    PopupMessage("This is my test popup\nHow are you doing?\nWHASUUUUP!", "Test Title", icon="ERROR")
