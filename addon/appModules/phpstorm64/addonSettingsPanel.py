# addonSettingsPanel.py
# A part of PHPStorm addon for NVDA
#Copyright (C) 2021 Paulius Leveris, Justinas Kilciauskas
#This file is covered by the GNU General Public License.
#See the file COPYING for more details.

import wx
import addonHandler
import config
import gui

addonHandler.initTranslation()

class SettingsPanel(gui.SettingsPanel):
	# Translators: Title for the settings panel in NVDA's multi-category settings
	title = _("PHPStorm")

	def makeSettings(self, settingsSizer):
		# Translators: A setting for enabling/disabling announcements of DOCBlock annotation indents.
		self.docblockAnnotationIndentsCheckBox = wx.CheckBox(self,
			wx.NewId(),
			label=_("Enable DOCBlock &annotation indents"))
		self.docblockAnnotationIndentsCheckBox.SetValue(
			config.conf["PHPStorm"]["docblockAnnotationIndents"])
		settingsSizer.Add(self.docblockAnnotationIndentsCheckBox, border=10, flag=wx.BOTTOM)

		# Translators: A setting for enabling/disabling line length indicator.
		self.lineLengthIndicatorCheckBox = wx.CheckBox(self,
			wx.NewId(),
			label=_("Enable &line length indicator"))
		self.lineLengthIndicatorCheckBox.SetValue(
			config.conf["PHPStorm"]["lineLengthIndicator"])
		settingsSizer.Add(self.lineLengthIndicatorCheckBox, border=10, flag=wx.BOTTOM)
		maxLineLengthSizer = wx.BoxSizer(wx.HORIZONTAL)
		# Translators: Setting for maximum line length used by line length indicator
		maxLineLengthLabel = wx.StaticText(self, -1, label=_("&Maximum line length:"))
		self.maxLineLengthEdit = wx.TextCtrl(self, wx.NewId())
		self.maxLineLengthEdit.SetValue(str(config.conf["PHPStorm"]["maxLineLength"]))
		maxLineLengthSizer.AddMany([maxLineLengthLabel, self.maxLineLengthEdit])
		settingsSizer.Add(maxLineLengthSizer, border=10, flag=wx.BOTTOM)

	def onSave(self):
		config.conf["PHPStorm"]["lineLengthIndicator"] = self.lineLengthIndicatorCheckBox.IsChecked()
		config.conf["PHPStorm"]["maxLineLength"] = int(self.maxLineLengthEdit.Value)
		config.conf["PHPStorm"]["docblockAnnotationIndents"] = self.docblockAnnotationIndentsCheckBox.IsChecked()
