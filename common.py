import wx


class WarningDialog:
    def __init__(self, message: str, title: str):
        dlg = wx.MessageDialog(
            parent=None,
            message=message,
            caption=title,
            style=wx.OK | wx.ICON_WARNING,
        )
        dlg.ShowModal()
        dlg.Destroy()


class ErrorDialog:
    def __init__(self, message: str, title: str):
        dlg = wx.MessageDialog(
            parent=None,
            message=message,
            caption=title,
            style=wx.OK | wx.ICON_ERROR,
        )

        dlg.ShowModal()
        dlg.Destroy()
