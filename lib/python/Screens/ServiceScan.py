import Screens.InfoBar
from enigma import eServiceReference, eTimer, eListboxPythonConfigContent, eDVBDB
from os.path import exists

from Screens.Screen import Screen
from Components.ServiceScan import ServiceScan as CScan
from Components.ProgressBar import ProgressBar
from Components.Label import Label
from Components.ActionMap import ActionMap
from Components.MenuList import MenuList
from Components.Sources.FrontendInfo import FrontendInfo
from Components.config import config


class FIFOList(MenuList):
	def __init__(self, len=10):
		self.len = len
		self.list = []
		MenuList.__init__(self, self.list)

	def addItem(self, item):
		self.list.append(item)
		self.l.setList(self.list[-self.len:])

	def clear(self):
		del self.list[:]
		self.l.setList(self.list)

	def getCurrentSelection(self):
		return self.list and self.getCurrent() or None

	def listAll(self):
		self.l.setList(self.list)
		self.selectionEnabled(True)


class ServiceScanSummary(Screen):
	skin = """
	<screen position="0,0" size="132,64">
		<widget name="Title" position="6,4" size="120,42" font="Regular;16" transparent="1" />
		<widget name="scan_progress" position="6,50" zPosition="1" borderWidth="1" size="56,12" backgroundColor="dark" />
		<widget name="Service" position="6,22" size="120,26" font="Regular;12" transparent="1" />
	</screen>"""

	def __init__(self, session, parent, showStepSlider=True):
		Screen.__init__(self, session, parent)

		self["Title"] = Label(parent.title or _("Service scan"))
		self["Service"] = Label(_("No service"))
		self["scan_progress"] = ProgressBar()

	def updateProgress(self, value):
		self["scan_progress"].setValue(value)

	def updateService(self, name):
		self["Service"].setText(name)


class ServiceScan(Screen):

	def up(self):
		self["servicelist"].up()
		selectedService = self["servicelist"].getCurrentSelection()
		if selectedService:
			self.session.summary.updateService(selectedService[0])

	def down(self):
		self["servicelist"].down()
		selectedService = self["servicelist"].getCurrentSelection()
		if selectedService:
			self.session.summary.updateService(selectedService[0])

	def ok(self):
		if self["scan"].isDone():
			try:
				from Plugins.SystemPlugins.LCNScanner.plugin import LCNBuildHelper
				lcn = LCNBuildHelper()
				lcn.buildAfterScan()
			except Exception as e:
				print(e)

			if self.currentInfobar.__class__.__name__ == "InfoBar":
				selectedService = self["servicelist"].getCurrentSelection()
				if selectedService and self.currentServiceList is not None:
					self.currentServiceList.setTvMode()
					bouquets = self.currentServiceList.getBouquetList()
					last_scanned_bouquet = bouquets and next((x[1] for x in bouquets if x[0] == "Last Scanned"), None)
					if last_scanned_bouquet:
						self.currentServiceList.enterUserbouquet(last_scanned_bouquet)
						self.currentServiceList.setCurrentSelection(eServiceReference(selectedService[1]))
						service = self.currentServiceList.getCurrentSelection()
						if not self.session.postScanService or service != self.session.postScanService:
							self.session.postScanService = service
							self.currentServiceList.addToHistory(service)
						config.servicelist.lastmode.save()
						self.currentServiceList.saveChannel(service)
						self.doCloseRecursive()
			self.cancel()

	def cancel(self):
		self.exit(False)

	def doCloseRecursive(self):
		self.exit(True)

	def exit(self, returnValue):
		if self.currentInfobar.__class__.__name__ == "InfoBar":
			self.close(returnValue)
		self.close()
		if exists(str(self.bouquetLastScanned)) and "en" not in config.osd.language.value:  # [norhap][OpenSPA]
			with open(self.bouquetLastScanned, "r") as fr:
				bouquetread = fr.readlines()
				with open(self.bouquetLastScanned, "w") as fw:
					for line in bouquetread:
						fw.write(line.replace("Last Scanned", _("Last Scanned")))
			eDVBDB.getInstance().reloadBouquets()

	def __init__(self, session, scanList):
		Screen.__init__(self, session)

		self["Title"] = Label(_("Scanning..."))
		self.scanList = scanList
		self.bouquetLastScanned = "/etc/enigma2/userbouquet.LastScanned.tv"

		if hasattr(session, 'infobar'):
			self.currentInfobar = Screens.InfoBar.InfoBar.instance
			if self.currentInfobar:
				self.currentServiceList = self.currentInfobar.servicelist
				if self.session.pipshown and self.currentServiceList:
					if self.currentServiceList.dopipzap:
						self.currentServiceList.togglePipzap()
					if hasattr(self.session, 'pip'):
						del self.session.pip
					self.session.pipshown = False
		else:
			self.currentInfobar = None

		self.session.nav.stopService()

		self["scan_progress"] = ProgressBar()
		self["scan_state"] = Label(_("scan state"))
		self["network"] = Label()
		self["transponder"] = Label()

		self["pass"] = Label("")
		self["servicelist"] = FIFOList(len=10)
		self["FrontendInfo"] = FrontendInfo()
		self["key_red"] = Label(_("Cancel"))
		self["key_green"] = Label(_("OK"))

		self["actions"] = ActionMap(["SetupActions", "MenuActions"],
		{
			"up": self.up,
			"down": self.down,
			"ok": self.ok,
			"save": self.ok,
			"cancel": self.cancel,
			"menu": self.doCloseRecursive
		}, -2)
		self.setTitle(_("Service scan"))
		self.onFirstExecBegin.append(self.doServiceScan)
		self.scanTimer = eTimer()
		self.scanTimer.callback.append(self.scanPoll)

	def scanPoll(self):
		if self["scan"].isDone():
			self.scanTimer.stop()
			self["servicelist"].moveToIndex(0)
			selectedService = self["servicelist"].getCurrentSelection()
			if selectedService:
				self.session.summary.updateService(selectedService[0])

	def doServiceScan(self):
		self["servicelist"].len = self["servicelist"].instance.size().height() // self["servicelist"].l.getItemSize().height()
		self["scan"] = CScan(self["scan_progress"], self["scan_state"], self["servicelist"], self["pass"], self.scanList, self["network"], self["transponder"], self["FrontendInfo"], self.session.summary)
		self.scanTimer.start(250)

	def createSummary(self):
		return ServiceScanSummary
