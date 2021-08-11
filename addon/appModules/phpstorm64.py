# PHPStorm add-on for NVDA
# PHPStorm enhancements. Provides support for DOCBlock annotations indents, better controls readability (proper labeling), code readability when navigating through code with keyboard shortcuts, code reading when jumping through debug breakpoints, last log message reading capability, better word-by-word navigation.
# Copyright 2021 Paulius Leveris

import appModuleHandler, controlTypes, buildVersion, tones, ui, api
from NVDAObjects import NVDAObject
from editableText import EditableTextWithoutAutoSelectDetection
from scriptHandler import script
from winsound import PlaySound, SND_ASYNC, SND_ALIAS
import speech, textInfos, treeInterceptorHandler
from speech.types import SpeechSequence

old = False
if buildVersion.version_year <= 2020: old = True # NVDA 2021.1 has updated speech function calls, so in order to provide support for previous releases, need to ensure the version of NVDA user is running.
original = speech.speech.speak if not old else speech.speak

class AppModule(appModuleHandler.AppModule):

	def __init__(self, *args, **kwargs):
		super(AppModule, self).__init__(*args, **kwargs)
		global original, old
		original = speech.speech.speak if not old else speech.speak
		ui.message("PHPStorm enhancement loaded")

	def terminate(self):
		super().terminate()
		if not old:
			speech.speech.speak = original
		else:
			speech.speak = original

	# Different classes according to things that needed to be handled.
	def chooseNVDAObjectOverlayClasses (self, obj, clsList):
		if obj.role is controlTypes.ROLE_EDITABLETEXT and obj.hasFocus and obj.windowClassName == 'SunAwtFrame': # Main editor window
			clsList.insert(0, EnhancedCodeNavigation)

	# For a purpose to read logs
	@script(gesture = 'kb:NVDA+i')
	def script_readStatusBar(self, gesture):
		obj = api.getForegroundObject().simpleFirstChild
		tones.beep(500,50)

		while obj is not None:
			if obj.role is controlTypes.ROLE_STATUSBAR and obj.simpleFirstChild is not None:
				msg = obj.simpleFirstChild.name
				ui.browseableMessage(msg, isHtml=False)
				return
			obj = obj.simpleNext
		ui.message('No info in logs')

	# Read elements that otherwise are skipped and needed to be checked with Review cursor instead.
	def event_gainFocus(self, obj, nextHandler):
		# Read editable element names
		if obj.role is controlTypes.ROLE_EDITABLETEXT and obj.name:
			ui.message(obj.name + ' editable')
		# Read radio button labels altogether with corresponding their values which happened to be names here
		elif obj.role is controlTypes.ROLE_RADIOBUTTON and obj.name and obj.previous:
			# Find that label
			objPrev = obj.previous
			while objPrev is not None and objPrev.role and objPrev.role is controlTypes.ROLE_RADIOBUTTON and objPrev.previous:
				objPrev = objPrev.previous
			# Check if we found the label
			if objPrev.role is controlTypes.ROLE_STATICTEXT:
				obj.name = objPrev.name + ' ' + obj.name
		# Read edit boxes which have panel as a parent and that parent has previous item as a label
		elif obj.role is controlTypes.ROLE_EDITABLETEXT and not obj.name and obj.parent.previous and obj.parent.previous.role is controlTypes.ROLE_STATICTEXT and obj.parent.previous.name:
			obj.name = obj.parent.previous.name
		# Read edit boxes which have a label as previous item
		elif obj.role is controlTypes.ROLE_EDITABLETEXT and not obj.name and obj.previous and obj.previous.role is controlTypes.ROLE_STATICTEXT and obj.previous.name:
			obj.name = obj.previous.name
		# Read comboboxes which have their values, but their labels are as previous items
		elif obj.role is controlTypes.ROLE_COMBOBOX and not obj.name and obj.value and obj.previous and obj.previous.role is controlTypes.ROLE_STATICTEXT and obj.previous.name:
			obj.name = obj.previous.name
		nextHandler()

# Rewrite default source code navigation behaviour, indentation included.
class EnhancedCodeNavigation(EditableTextWithoutAutoSelectDetection):
	# Remember if last keyboard shortcut was related to debugging to know how to react when caret changes
	lastDebuggingGesture = False

	# Remember last announced indentation level to avoid repetition
	lastIndentationLevelAnnounced = 0

	__gestures = {
		# these PHPStorm commands change caret position by line, so they should trigger reading new line position.
		# Go to next method
				"kb:alt+downArrow": "caret_moveByLine",
				# Go to previous method
		"kb:alt+upArrow": "caret_moveByLine",
		# Move to code block start
		"kb:control+[": "caret_moveByLine",
		# Move to code block end
		"kb:control+]": "caret_moveByLine",
		# Move to next highlighted error
		"kb:f2": "caret_moveByLine",
		# Move to previous highlighted error
		"kb:shift+f2": "caret_moveByLine",
		# Find next
		"kb:f3": "caret_moveByLine",
		# Find previous
		"kb:shift+f3": "caret_moveByLine",
		# Go to declaration
		"kb:control+b": "caret_moveByLine",
		# Navigate back
		"kb:control+alt+leftArrow": "caret_moveByLine",
		# Navigate forward
		"kb:control+alt+rightArrow": "caret_moveByLine",
		# Undo
		"kb:control+z": "caret_moveByLine",
		# Go to super method/ super class
		"kb:control+u": "caret_moveByLine",
		# Go to last edit location
		"kb:control+shift+backspace": "caret_moveByLine",
		# Comment / Uncomment with Line Comment
		"kb:control+/": "caret_moveByLine",

		# Trigger waiting for caret to be moved for debugging purposes
		# Step into
		"kb:f7": "currentlyDebugging",
		# Step over
		"kb:f8": "currentlyDebugging",
		# Step out
		"kb:shift+f8": "currentlyDebugging",
		# Resume program
		"kb:f9": "currentlyDebugging",
		
		# These gestures trigger caret movement by word
		# Next word
		"kb:control+leftArrow": "moveByWord",
		# Previous word
		"kb:control+rightArrow": "moveByWord",
		
		# these gestures trigger selection change
		# Select Successively Incresing Code blocks
		"kb:control+w": "caret_changeSelection",
		# Decrease Current Selection to Previous State
		"kb:control+shift+w": "caret_changeSelection",
		# Select till code block start
		"kb:control+shift+[": "caret_changeSelection",
		# Select till code block end
		"kb:control+shift+]": "caret_changeSelection",
		# If more shortcuts are needed: https://shortcutworld.com/PhpStorm/win/JetBrains-PhpStorm_Shortcuts
	}
	
	# When caret movement fails, different event will be triggered to make a sound
	shouldFireCaretMovementFailedEvents = True

	# Make a sound when cursor does not move so it is clear if there is an end or a beginning of a file / line.
	def event_caretMovementFailed(self, gesture):
		key = gesture.vkCode
		if key == 37 or key == 39: # Left or right arrow pressed. Avoids reading problems char by char.
			return
		PlaySound('SystemExclamation', SND_ASYNC | SND_ALIAS)

	# Debugging state determined by keyboard hotkeys.
	def script_currentlyDebugging(self, gesture):
		self.lastDebuggingGesture = True
		gesture.send()

	# Better word handleing to avoid annoying repetition due to PHPStorm's behaviour when navigating by words.
	# To work properly,In PHPStorm Settings -> General, setting "When moving by words": should be "Always jump to the word start (Windows default).
	def script_moveByWord(self, gesture):
		# Retrieve current caret position to be able later to check if movement to next / previous word was successful
		obj = api.getCaretObject()
		caretInfo = obj.makeTextInfo(textInfos.POSITION_CARET)
		caretInfo.expand(textInfos.UNIT_WORD)
		startPosForWord = caretInfo._startOffset
		endPosForWord = caretInfo._endOffset
		# Safety count is needed to avoid looping forever if something goes wrong
		safetyCount = 0
		# Move caret in IDE until it goes to the other word
		while caretInfo._startOffset == startPosForWord and caretInfo._endOffset == endPosForWord and safetyCount < 20:
			safetyCount += 1
			# Try to move cursor to next / previous word
			gesture.send()
			# Get caret cursor after movement
			caretInfo = obj.makeTextInfo(textInfos.POSITION_CARET)
			caretInfo.expand(textInfos.UNIT_WORD)
		speech.speakTextInfo(caretInfo, reason = controlTypes.OutputReason.CARET, unit = textInfos.UNIT_WORD)

# Trigger when editor gains focus.
	def event_gainFocus(self):
		# Read indentation
		global original, old
		if not old: speech.speech.speak = self.speakIndentation
		else: speech.speak = self.speakIndentation
		self.countAnnounced = 0

	def event_loseFocus(self):
		if not old: speech.speech.speak = original
		else: speech.speak = original

	# Speaks indentation in a special way - not only the beginning of a line, but after * character in docblocks as well.
	def speakIndentation(self, sequence, *args, **kwargs):
	# Retrieve last message to be spoken
		lastSequenceIndex = len(sequence) -1
		item = sequence[lastSequenceIndex]
		# Check if this part of a source code has nested indentation
		if isinstance(item, str) and (item.startswith('* ') or item.startswith('*	')):
			indentationSymbol = item[1]
			indentationSymbolText = 'tab' if indentationSymbol == '	' else 'space'
			indentationLevel = 1
			# Look up where indentation chars end
			while item[indentationLevel + 1] == item[indentationLevel]:
				indentationLevel += 1
			# If indentation level is different, announce it
			if self.lastIndentationLevelAnnounced != indentationLevel:
				sourceContent = item[indentationLevel + 1:]
				text = '{} {} {} {}'.format(item[0], indentationLevel, indentationSymbolText, sourceContent)
				sequence[lastSequenceIndex] = text
			# Update last spoken indentation level to current one for checking later on
			self.lastIndentationLevelAnnounced = indentationLevel
		# Announce non-indents
		elif isinstance(item, str) and item.startswith('*'):
			if self.lastIndentationLevelAnnounced != 0:
				sequence[lastSequenceIndex] = 'No inner indent ' + sequence[lastSequenceIndex]
			self.lastIndentationLevelAnnounced = 0
		else:
			self.lastIndentationLevelAnnounced = 0
		original(sequence, *args, **kwargs)

	# Override to catch caret movements when debugging and report the current line.
	def event_caret(self):
		if self.lastDebuggingGesture:
			self.lastDebuggingGesture = False
			self.reportCurrentLine()

	def reportCurrentLine(self):
		obj=api.getFocusObject()
		treeInterceptor=obj.treeInterceptor
		if isinstance(treeInterceptor,treeInterceptorHandler.DocumentTreeInterceptor) and not treeInterceptor.passThrough:
			obj=treeInterceptor
		try:
			info=obj.makeTextInfo(textInfos.POSITION_CARET)
		except (NotImplementedError, RuntimeError):
			info=obj.makeTextInfo(textInfos.POSITION_FIRST)
		info.expand(textInfos.UNIT_LINE)
		speech.speakTextInfo(info, unit=textInfos.UNIT_LINE, reason=controlTypes.OutputReason.CARET)
		return

	# For testing, currently not used.
	def isDebuggerWindowActive() -> bool:
		obj = api.getFocusObject()
		try:
			if obj.role == controlTypes.ROLE_LISTITEM and obj.parent.parent.parent.parent.parent.parent.name == 'Frames' and obj.parent.parent.parent.parent.parent.parent.parent.parent.parent.parent.parent.name == 'Debugger':
				return True
			else:
				return False
		except AttributeError:
			pass
			return False
