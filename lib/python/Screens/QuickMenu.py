from re import search, sub
from os.path import exists, isdir, realpath

from enigma import BT_SCALE, eEnv, eListboxPythonMultiContent, gFont, pNavigation

import NavigationInstance
from skin import getSkinFactor
from Components.ActionMap import HelpableActionMap
from Components.Console import Console
from Components.Label import Label
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryPixmapAlphaBlend, MultiContentEntryText
from Components.Network import iNetwork
from Components.NimManager import nimmanager
from Components.Sources.StaticText import StaticText
from Components.SystemInfo import BoxInfo, getBoxDisplayName
from Plugins.SystemPlugins.SoftwareManager.BackupRestore import BackupScreen, BackupSelection, RestoreScreen, getBackupFilename, getBackupPath, getOldBackupPath
from Screens.CCcamInfo import CCcamInfoMain
from Screens.HarddiskSetup import HarddiskConvertExt4Selection, HarddiskFsckSelection, HarddiskSelection
from Screens.MountManager import HddMount
from Screens.NetworkSetup import *
from Screens.OScamInfo import OSCamInfo
from Screens.ParentalControlSetup import ProtectedScreen
from Screens.PluginBrowser import PackageAction, PluginBrowser
from Screens.RestartNetwork import RestartNetwork
from Screens.Satconfig import NimSelection
from Screens.ScanSetup import ScanSimple, ScanSetup
from Screens.Screen import Screen
from Screens.Setup import Setup
from Screens.SkinSelection import SkinSelection
from Screens.SoftcamSetup import SoftcamSetup
from Screens.VideoMode import VideoSetup
from Tools.Directories import isPluginInstalled
from Tools.LoadPixmap import LoadPixmap

NETWORKBROWSER = isPluginInstalled("NetworkBrowser")
AUDIOSYNC = isPluginInstalled("AudioSync")
VIDEOENH = isPluginInstalled("VideoEnhancement") and exists("/proc/stb/vmpeg/0/pep_apply")
DFLASH = isPluginInstalled("dFlash")
DBACKUP = isPluginInstalled("dBackup")
POSSETUP = isPluginInstalled("PositionerSetup")
SATFINDER = isPluginInstalled("Satfinder")


def isFileSystemSupported(filesystem):
	try:
		for fs in open("/proc/filesystems"):
			if fs.strip().endswith(filesystem):
				return True
		return False
	except Exception as err:
		print("[Harddisk] Failed to read /proc/filesystems: %s" % str(err))


class QuickMenu(Screen, ProtectedScreen):
	skin = """
	<screen name="QuickMenu" position="center,center" size="1180,600" backgroundColor="black" flags="wfBorder">
		<widget name="list" position="21,32" size="370,400" backgroundColor="black" itemHeight="50" transparent="1" />
		<widget name="sublist" position="410,32" size="300,400" backgroundColor="black" itemHeight="50" />
		<eLabel position="400,30" size="2,400" backgroundColor="darkgrey" zPosition="3" />
		<widget source="session.VideoPicture" render="Pig" position="720,30" size="450,300" backgroundColor="transparent" zPosition="1" />
		<widget name="description" position="22,445" size="1150,110" zPosition="1" font="Regular;22" halign="center" backgroundColor="black" transparent="1" />
		<widget name="key_red" position="20,571" size="300,26" zPosition="1" font="Regular;22" halign="center" foregroundColor="white" backgroundColor="black" transparent="1" />
		<widget name="key_green" position="325,571" size="300,26" zPosition="1" font="Regular;22" halign="center" foregroundColor="white" backgroundColor="black" transparent="1" />
		<widget name="key_yellow" position="630,571" size="300,26" zPosition="1" font="Regular;22" halign="center" foregroundColor="white" backgroundColor="black" transparent="1" valign="center" />
		<widget name="key_blue" position="935,571" size="234,26" zPosition="1" font="Regular;22" halign="center" foregroundColor="white" backgroundColor="black" transparent="1" />
		<eLabel name="new eLabel" position="21,567" size="300,3" zPosition="3" backgroundColor="red" />
		<eLabel name="new eLabel" position="325,567" size="300,3" zPosition="3" backgroundColor="green" />
		<eLabel name="new eLabel" position="630,567" size="300,3" zPosition="3" backgroundColor="yellow" />
		<eLabel name="new eLabel" position="935,567" size="234,3" zPosition="3" backgroundColor="blue" />
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		if config.ParentalControl.configured.value:
			ProtectedScreen.__init__(self)
		Screen.setTitle(self, _("Quick Launch Menu"))
		ProtectedScreen.__init__(self)
		self["key_red"] = Label(_("Exit"))
		self["key_green"] = Label(_("System Info"))
		self["key_yellow"] = Label(_("Devices"))
		self["key_blue"] = Label()
		self["description"] = Label()
		self["summary_description"] = StaticText("")
		self.menu = 0
		self.list = []
		self["list"] = QuickMenuList(self.list)
		self.sublist = []
		self["sublist"] = QuickMenuSubList(self.sublist)
		self.selectedList = []
		self.onChangedEntry = []
		self["list"].onSelectionChanged.append(self.selectionChanged)
		self["sublist"].onSelectionChanged.append(self.selectionSubChanged)
		self["NavigationActions"] = HelpableActionMap(self, ["OkCancelActions", "NavigationActions"], {
			"ok": self.ok,
			"cancel": self.keyred,
			"left": self.goLeft,
			"right": self.goRight,
			"up": self.goUp,
			"down": self.goDown,
		}, prio=-1)
		self["ColorActions"] = HelpableActionMap(self, "ColorActions", {
			"red": self.keyred,
			"green": self.keygreen,
			"yellow": self.keyyellow,
		}, prio=0)
		self.MainQmenu()
		self.selectedList = self["list"]
		self.selectionChanged()
		self.onLayoutFinish.append(self.layoutFinished)

	def isProtected(self):
		return config.ParentalControl.setuppinactive.value and not config.ParentalControl.config_sections.main_menu.value and config.ParentalControl.config_sections.quickmenu.value

	def createSummary(self):
		pass

	def layoutFinished(self):
		self["sublist"].selectionEnabled(False)

	def selectionChanged(self):
		if self.selectedList == self["list"]:
			item = self["list"].getCurrent()
			if item:
				self["description"].text = item[4][7]
				self["summary_description"].text = item[0]
				self.okList()

	def selectionSubChanged(self):
		if self.selectedList == self["sublist"]:
			item = self["sublist"].getCurrent()
			if item:
				self["description"].text = item[3][7]
				self["summary_description"].text = item[0]

	def goLeft(self):
		if self.menu != 0:
			self.menu = 0
			self.selectedList = self["list"]
			self["list"].selectionEnabled(1)
			self["sublist"].selectionEnabled(0)
			self.selectionChanged()

	def goRight(self):
		if self.menu == 0:
			self.menu = 1
			self.selectedList = self["sublist"]
			self["sublist"].moveToIndex(0)
			self["list"].selectionEnabled(0)
			self["sublist"].selectionEnabled(1)
			self.selectionSubChanged()

	def goUp(self):
		self.selectedList.up()

	def goDown(self):
		self.selectedList.down()

	def keyred(self):
		self.close()

	def keygreen(self):
		from Screens.Information import DistributionInformation
		self.session.open(DistributionInformation)

	def keyyellow(self):
		self.session.open(QuickMenuDevices)

# ####### Main Menu ##############################
	def MainQmenu(self):
		self.menu = 0
		self.list = []
		self.oldlist = []
		self.list.append(QuickMenuEntryComponent("Software Manager", _("Update/Backup/Restore your box"), _("Update/Backup your firmware, Backup/Restore settings")))
		if BoxInfo.getItem("SoftCam"):
			self.list.append(QuickMenuEntryComponent("Softcam", _("Start/stop/select cam"), _("Start/stop/select your cam, You need to install first a softcam")))
		self.list.append(QuickMenuEntryComponent("System", _("System Setup"), _("Setup your System")))
		self.list.append(QuickMenuEntryComponent("Mounts", _("Mount Setup"), _("Setup your mounts for network")))
		self.list.append(QuickMenuEntryComponent("Network", _("Setup your local network"), _("Setup your local network. For Wlan you need to boot with a USB-Wlan stick")))
		self.list.append(QuickMenuEntryComponent("AV Setup", _("Setup Video/Audio"), _("Setup your Video Mode, Video Output and other Video Settings")))
		self.list.append(QuickMenuEntryComponent("Tuner Setup", _("Setup Tuner"), _("Setup your Tuner and search for channels")))
		self.list.append(QuickMenuEntryComponent("Plugins", _("Setup Plugins"), _("Shows available plugins. Here you can download and install them")))
		self.list.append(QuickMenuEntryComponent("Harddisk", _("Harddisk Setup"), _("Setup your Harddisk")))
		self["list"].setList(self.list)

# ####### System Setup Menu ##############################
	def Qsystem(self):
		self.sublist = []
		self.sublist.append(QuickSubMenuEntryComponent("Customize", _("Setup Enigma2"), _("Customize enigma2 personal settings")))
		self.sublist.append(QuickSubMenuEntryComponent("OSD Settings", _("OSD Setup"), _("Setup your OSD")))
		self.sublist.append(QuickSubMenuEntryComponent("Button Setup", _("Button Setup"), _("Setup your remote buttons")))
		if BoxInfo.getItem("FrontpanelDisplay") and BoxInfo.getItem("Display"):
			self.sublist.append(QuickSubMenuEntryComponent("Display Settings", _("Setup your LCD"), _("Setup your display")))
		self.sublist.append(QuickSubMenuEntryComponent("Skin Settings", _("Select Enigma2 Skin"), _("Setup your Skin")))
		self.sublist.append(QuickSubMenuEntryComponent("Channel selection", _("Channel selection configuration"), _("Setup your Channel selection configuration")))
		self.sublist.append(QuickSubMenuEntryComponent("Recording Settings", _("Recording Setup"), _("Setup your recording config")))
		self.sublist.append(QuickSubMenuEntryComponent("EPG Settings", _("EPG Setup"), _("Setup your EPG config")))
		self["sublist"].setList(self.sublist)

# ####### Network Menu ##############################
	def Qnetwork(self):
		self.sublist = []
		if isPluginInstalled("NetworkWizard"):
			self.sublist.append(QuickSubMenuEntryComponent("Network Wizard", _("Configure your Network"), _("Use the Networkwizard to configure your Network. The wizard will help you to setup your network")))
		if len(self.adapters) > 1:  # show only adapter selection if more as 1 adapter is installed
			self.sublist.append(QuickSubMenuEntryComponent("Network Adapter Selection", _("Select Lan/Wlan"), _("Setup your network interface. If no Wlan stick is used, you only can select Lan")))
		if self.activeInterface is not None:  # show only if there is already a adapter up
			self.sublist.append(QuickSubMenuEntryComponent("Network Interface", _("Setup interface"), _("Setup network. Here you can setup DHCP, IP, DNS")))
		self.sublist.append(QuickSubMenuEntryComponent("Network Restart", _("Restart network to with current setup"), _("Restart network and remount connections")))
		self.sublist.append(QuickSubMenuEntryComponent("Network Services", _("Setup Network Services"), _("Setup Network Services (Samba, Ftp, NFS, ...)")))
		self.sublist.append(QuickSubMenuEntryComponent("MiniDLNA", _("Setup MiniDLNA"), _("Setup MiniDLNA")))
		self.sublist.append(QuickSubMenuEntryComponent("Inadyn", _("Setup Inadyn"), _("Setup Inadyn")))
		self.sublist.append(QuickSubMenuEntryComponent("uShare", _("Setup uShare"), _("Setup uShare")))
		self["sublist"].setList(self.sublist)

# ####### Mount Settings Menu ##############################
	def Qmount(self):
		self.sublist = []
		if NETWORKBROWSER:
			self.sublist.append(QuickSubMenuEntryComponent("Mount Manager", _("Manage network mounts"), _("Setup your network mounts")))
			self.sublist.append(QuickSubMenuEntryComponent("Network Browser", _("Search for network shares"), _("Search for network shares")))
		self.sublist.append(QuickSubMenuEntryComponent("Device Manager", _("Mounts Devices"), _("Setup your Device mounts (USB, HDD, others...)")))
		self["sublist"].setList(self.sublist)

# ####### Softcam Menu ##############################
	def Qsoftcam(self):
		self.sublist = []
		if BoxInfo.getItem("SoftCam"):  # show only when there is a softcam installed
			self.sublist.append(QuickSubMenuEntryComponent("Softcam Settings", _("Control your Softcams"), _("Use the Softcam Panel to control your Cam. This let you start/stop/select a cam")))
			if BoxInfo.getItem("ShowOscamInfo"):  # show only when oscam or ncam is active
				self.sublist.append(QuickSubMenuEntryComponent("OSCam Information", _("Show OSCam Information"), _("Show the OSCam information screen")))
			if BoxInfo.getItem("ShowCCCamInfo"):  # show only when CCcam is active
				self.sublist.append(QuickSubMenuEntryComponent("CCcam Information", _("Show CCcam Info"), _("Show the CCcam Info Screen")))
		self.sublist.append(QuickSubMenuEntryComponent("Download Softcams", _("Download and install cam"), _("Shows available softcams. Here you can download and install them")))
		self["sublist"].setList(self.sublist)

# ####### A/V Settings Menu ##############################
	def Qavsetup(self):
		self.sublist = []
		self.sublist.append(QuickSubMenuEntryComponent("Video Settings", _("Setup Videomode"), _("Setup your Video Mode, Video Output and other Video Settings")))
		self.sublist.append(QuickSubMenuEntryComponent("Audio Settings", _("Setup Audiomode"), _("Setup your Audio Mode")))
		if AUDIOSYNC:
			self.sublist.append(QuickSubMenuEntryComponent("Audio Sync", _("Setup Audio Sync"), _("Setup Audio Sync settings")))
		self.sublist.append(QuickSubMenuEntryComponent("Auto Language", _("Auto Language Selection"), _("Select your Language for Audio/Subtitles")))
		if VIDEOENH:
			self.sublist.append(QuickSubMenuEntryComponent("VideoEnhancement", _("VideoEnhancement Setup"), _("VideoEnhancement Setup")))

		self["sublist"].setList(self.sublist)

# ####### Tuner Menu ##############################
	def Qtuner(self):
		self.sublist = []
		self.sublist.append(QuickSubMenuEntryComponent("Tuner Configuration", _("Setup tuner(s)"), _("Setup each tuner for your satellite system")))
		if POSSETUP:
			self.sublist.append(QuickSubMenuEntryComponent("Positioner Setup", _("Setup rotor"), _("Setup your positioner for your satellite system")))
		self.sublist.append(QuickSubMenuEntryComponent("Automatic Scan", _("Automatic Service Searching"), _("Automatic scan for services")))
		self.sublist.append(QuickSubMenuEntryComponent("Manual Scan", _("Manual Service Searching"), _("Manual scan for services")))
		if SATFINDER:
			self.sublist.append(QuickSubMenuEntryComponent("Sat Finder", _("Search Sats"), _("Search Sats, check signal and lock")))
		self["sublist"].setList(self.sublist)

# ####### Software Manager Menu ##############################
	def Qsoftware(self):
		self.sublist = []
		self.sublist.append(QuickSubMenuEntryComponent("Software Update", _("Online software update"), _("Check/Install online updates (you must have a working Internet connection)")))
		self.sublist.append(QuickSubMenuEntryComponent("Flash Online", _("Flash Online a new image"), _("Flash on the fly your your Receiver software.")))
		self.sublist.append(QuickSubMenuEntryComponent("Complete Backup", _("Backup your current image"), _("Backup your current image to HDD or USB. This will make a 1:1 copy of your box")))
		self.sublist.append(QuickSubMenuEntryComponent("Backup Settings", _("Backup your current settings"), _("Backup your current settings. This includes E2-setup, channels, network and all selected files")))
		self.sublist.append(QuickSubMenuEntryComponent("Restore Settings", _("Restore settings from a backup"), _("Restore your settings back from a backup. After restore the box will restart to activated the new settings")))
		self.sublist.append(QuickSubMenuEntryComponent("Show Default Backup Files", _("Show files backed up by default"), _("Here you can browse (but not modify) the files that are added to the backupfile by default (E2-setup, channels, network).")))
		self.sublist.append(QuickSubMenuEntryComponent("Select Additional Backup Files", _("Select additional files to backup"), _("Here you can specify additional files that should be added to the backup file.")))
		self.sublist.append(QuickSubMenuEntryComponent("Select Excluded Backup Files", _("Select files to exclude from backup"), _("Here you can select which files should be excluded from the backup.")))
		self.sublist.append(QuickSubMenuEntryComponent("Software Manager Settings", _("Manage your online update files"), _("Here you can select which files should be updated with a online update")))
		self["sublist"].setList(self.sublist)

# ####### Plugins Menu ##############################
	def Qplugin(self):
		self.sublist = []
		self.sublist.append(QuickSubMenuEntryComponent("Plugin Browser", _("Open the Plugin Browser"), _("Shows Plugins Browser. Here you can setup installed Plugin")))
		self.sublist.append(QuickSubMenuEntryComponent("Download Plugins", _("Download and install Plugins"), _("Shows available plugins. Here you can download and install them")))
		self.sublist.append(QuickSubMenuEntryComponent("Remove Plugins", _("Delete Plugins"), _("Delete and uninstall Plugins. This will remove the Plugin from your box")))
		self.sublist.append(QuickSubMenuEntryComponent("Manage Plugins", _("Manage Plugins"), _("Manage Plugins. This will remove/install Plugins on your box")))
		self.sublist.append(QuickSubMenuEntryComponent("Plugin Browser Settings", _("Setup Plugin Browser"), _("Setup PluginBrowser. Here you can select which Plugins are showed in the PluginBrowser")))
		self.sublist.append(QuickSubMenuEntryComponent("IPK Installer", _("Install Local Extension"), _("Scan for local extensions and install them")))
		self["sublist"].setList(self.sublist)

# ####### Harddisk Menu ##############################
	def Qharddisk(self):
		self.sublist = []
		self.sublist.append(QuickSubMenuEntryComponent("Harddisk Setup", _("Harddisk Setup"), _("Setup your Harddisk")))
		self.sublist.append(QuickSubMenuEntryComponent("Initialization", _("Format HDD"), _("Format your hard drive")))
		self.sublist.append(QuickSubMenuEntryComponent("File System Check", _("Check HDD"), _("Filesystem check your hard drive")))
		if isFileSystemSupported("ext4"):
			self.sublist.append(QuickSubMenuEntryComponent("Convert ext3 to ext4", _("Convert file system ext3 to ext4"), _("Convert file system ext3 to ext4")))
		self["sublist"].setList(self.sublist)

	def ok(self):
		if self.menu > 0:
			self.okSubList()
		else:
			self.goRight()


# ####################################################################
# ####### Make Selection MAIN MENU LIST ##############################
# ####################################################################


	def okList(self):
		item = self["list"].getCurrent()[0]
# ####### Select Network Menu ##############################
		if item == _("Network"):
			self.GetNetworkInterfaces()
			self.Qnetwork()
# ####### Select System Setup Menu ##############################
		elif item == _("System"):
			self.Qsystem()
# ####### Select Mount Menu ##############################
		elif item == _("Mounts"):
			self.Qmount()
# ####### Select Softcam Menu ##############################
		elif item == _("Softcam"):
			self.Qsoftcam()
# ####### Select AV Setup Menu ##############################
		elif item == _("AV Setup"):
			self.Qavsetup()
# ####### Select Tuner Setup Menu ##############################
		elif item == _("Tuner Setup"):
			self.Qtuner()
# ####### Select Software Manager Menu ##############################
		elif item == _("Software Manager"):
			self.Qsoftware()
# ####### Select PluginDownloadBrowser Menu ##############################
		elif item == _("Plugins"):
			self.Qplugin()
# ####### Select Tuner Setup Menu ##############################
		elif item == _("Harddisk"):
			self.Qharddisk()
		self["sublist"].selectionEnabled(0)

# ####################################################################
# ####### Make Selection SUB MENU LIST ##############################
# ####################################################################

	def okSubList(self):
		item = self["sublist"].getCurrent()[0]
# ####### Select Network Menu ##############################
		if item == _("Network Wizard"):
			from Plugins.SystemPlugins.NetworkWizard.NetworkWizard import NetworkWizard
			self.session.open(NetworkWizard)
		elif item == _("Network Adapter Selection"):
			self.session.open(NetworkAdapterSelection)
		elif item == _("Network Interface"):
			self.session.open(AdapterSetup, self.activeInterface)
		elif item == _("Network Restart"):
			self.session.open(RestartNetwork)
		elif item == _("Network Services"):
			self.session.open(NetworkServicesSetup)
		elif item == _("MiniDLNA"):
			self.session.open(NetworkMiniDLNASetup)
		elif item == _("Inadyn"):
			self.session.open(NetworkInadynSetup)
		elif item == _("uShare"):
			self.session.open(NetworkuShareSetup)
# ####### Select System Setup Menu ##############################
		elif item == _("Customize"):
			self.openSetup("Usage")
		elif item == _("Button Setup"):
			self.openSetup("RemoteButton")
		elif item == _("Display Settings"):
			self.openSetup("Display")
		elif item == _("Skin Settings"):
			self.session.open(SkinSelection)
		elif item == _("OSD Settings"):
			self.openSetup("UserInterface")
		elif item == _("Channel Selection"):
			self.openSetup("ChannelSelection")
		elif item == _("Recording Settings"):
			self.openSetup("Recording")
		elif item == _("EPG Settings"):
			self.openSetup("EPG")
# ####### Select Mounts Menu ##############################
		elif item == _("Mount Manager"):
			from Plugins.SystemPlugins.NetworkBrowser.MountManager import AutoMountManager
			plugin_path_networkbrowser = eEnv.resolve("${libdir}/enigma2/python/Plugins/SystemPlugins/NetworkBrowser")
			self.session.open(AutoMountManager, None, plugin_path_networkbrowser)
		elif item == _("Network Browser"):
			from Plugins.SystemPlugins.NetworkBrowser.NetworkBrowser import NetworkBrowser
			plugin_path_networkbrowser = eEnv.resolve("${libdir}/enigma2/python/Plugins/SystemPlugins/NetworkBrowser")
			self.session.open(NetworkBrowser, None, plugin_path_networkbrowser)
		elif item == _("Device Manager"):
			self.session.open(HddMount)
# ####### Select Softcam Menu ##############################
		elif item == _("Softcam Settings"):
			self.session.open(SoftcamSetup)
		elif item == _("OSCam Information"):
			self.session.open(OSCamInfo)
		elif item == _("CCcam Information"):
			self.session.open(CCcamInfoMain)
		elif item == _("Download Softcams"):
			self.session.open(PackageAction, PackageAction.MODE_SOFTCAM)
# ####### Select AV Setup Menu ##############################
		elif item == _("Video Settings"):
			self.session.open(VideoSetup)
		elif item == _("Audio Settings"):
			self.openSetup("Audio")
		elif item == _("Auto Language"):
			self.openSetup("AutoLanguage")
		elif item == _("Audio Sync"):
			from Plugins.Extensions.AudioSync.AC3setup import AC3LipSyncSetup
			plugin_path_audiosync = eEnv.resolve("${libdir}/enigma2/python/Plugins/Extensions/AudioSync")
			self.session.open(AC3LipSyncSetup, plugin_path_audiosync)
		elif item == _("VideoEnhancement"):
			from Plugins.SystemPlugins.VideoEnhancement.plugin import VideoEnhancementSetup
			self.session.open(VideoEnhancementSetup)
# ####### Select TUNER Setup Menu ##############################
		elif item == _("Tuner Configuration"):
			self.session.open(NimSelection)
		elif item == _("Positioner Setup"):
			from Plugins.SystemPlugins.PositionerSetup.plugin import PositionerMain
			PositionerMain(self.session)
		elif item == _("Automatic Scan"):
			self.session.open(ScanSimple)
		elif item == _("Manual Scan"):
			self.session.open(ScanSetup)
		elif item == _("Sat Finder"):
			self.SatfinderMain()
# ####### Select Software Manager Menu ##############################
		elif item == _("Software Update"):
			from Screens.SoftwareUpdate import SoftwareUpdate
			self.session.open(SoftwareUpdate)
		elif item == _("Flash Online"):
			from Screens.FlashManager import FlashManager
			self.session.open(FlashManager)
		elif item == _("Complete Backup"):
			self.CompleteBackup()
		elif item == _("Backup Settings"):
			#self.session.openWithCallback(self.backupDone, BackupScreen, runBackup=True)
			self.session.open(BackupScreen, runBackup=True, closeOnSuccess=False)
		elif item == _("Restore Settings"):
			self.backuppath = getBackupPath()
			if not isdir(self.backuppath):
				self.backuppath = getOldBackupPath()
			self.backupfile = getBackupFilename()
			self.fullbackupfilename = self.backuppath + "/" + self.backupfile
			if exists(self.fullbackupfilename):
				self.session.openWithCallback(self.startRestore, MessageBox, _("Are you sure you want to restore your %s %s backup?\nSTB will restart after the restore") % getBoxDisplayName(), default=False)
			else:
				self.session.open(MessageBox, _("Sorry no backups found!"), MessageBox.TYPE_INFO, timeout=10)
		elif item == _("Show Default Backup Files"):
			self.session.open(BackupSelection, title=_("Default files/folders to backup"), configBackupDirs=config.plugins.configurationbackup.backupdirs_default, readOnly=True, mode="backupfiles")
		elif item == _("Select Additional Backup Files"):
			self.session.open(BackupSelection, title=_("Additional files/folders to backup"), configBackupDirs=config.plugins.configurationbackup.backupdirs, readOnly=False, mode="backupfiles_addon")
		elif item == _("Select Excluded Backup Files"):
			self.session.open(BackupSelection, title=_("Files/folders to exclude from backup"), configBackupDirs=config.plugins.configurationbackup.backupdirs_exclude, readOnly=False, mode="backupfiles_exclude")
		elif item == _("Software Manager Settings"):
			self.openSetup("SoftwareManager")
# ####### Select PluginDownloadBrowser Menu ##############################
		elif item == _("Plugin Browser"):
			self.session.open(PluginBrowser)
		elif item == _("Download Plugins"):
			self.session.open(PackageAction, PackageAction.MODE_INSTALL)
		elif item == _("Remove Plugins"):
			self.session.open(PackageAction, PackageAction.MODE_REMOVE)
		elif item == _("Manage Plugins"):
			self.session.open(PackageAction, PackageAction.MODE_MANAGE)
		elif item == _("Plugin Browser Settings"):
			self.openSetup("PluginBrowser")
		elif item == _("IPK Installer"):
			try:
				from Plugins.Extensions.MediaScanner.plugin import main
				main(self.session)
			except Exception:
				self.session.open(MessageBox, _("Sorry MediaScanner is not installed!"), MessageBox.TYPE_INFO, timeout=10)
# ####### Select Harddisk Menu ############################################
		elif item == _("Harddisk Setup"):
			self.openSetup("HardDisk")
		elif item == _("Initialization"):
			self.session.open(HarddiskSelection)
		elif item == _("File System Check"):
			self.session.open(HarddiskFsckSelection)
		elif item == _("Convert ext3 to ext4"):
			self.session.open(HarddiskConvertExt4Selection)

# ####### OPEN SETUP MENUS ####################
	def openSetup(self, dialog):
		self.session.openWithCallback(self.menuClosed, Setup, dialog)

	def menuClosed(self, *res):
		pass

# ####### NETWORK TOOLS #######################
	def GetNetworkInterfaces(self):
		self.adapters = [(iNetwork.getFriendlyAdapterName(x), x) for x in iNetwork.getAdapterList()]
		if not self.adapters:
			self.adapters = [(iNetwork.getFriendlyAdapterName(x), x) for x in iNetwork.getConfiguredAdapters()]
		if len(self.adapters) == 0:
			self.adapters = [(iNetwork.getFriendlyAdapterName(x), x) for x in iNetwork.getInstalledAdapters()]
		self.activeInterface = None
		for x in self.adapters:
			if iNetwork.getAdapterAttribute(x[1], "up") is True:
				self.activeInterface = x[1]
				return

# ####### TUNER TOOLS #######################
	def SatfinderMain(self):
		if NavigationInstance.instance.getAnyRecordingsCount():
			self.session.open(MessageBox, _("A recording is currently running. Please stop the recording before trying to start the satellite finder."), MessageBox.TYPE_ERROR)
		else:
			from Plugins.SystemPlugins.Satfinder.plugin import Satfinder
			self.session.open(Satfinder)

# ####### SOFTWARE MANAGER TOOLS #######################
	def backupDone(self, retval=None):
		self.session.open(MessageBox, _("Backup done.") if retval else _("Backup failed!"), MessageBox.TYPE_INFO if retval else MessageBox.TYPE_ERROR, timeout=10)

	def startRestore(self, ret=False):
		if (ret is True):
			self.exe = True
			self.session.open(RestoreScreen, runRestore=True)

	def CompleteBackup(self):
		if DFLASH:
			from Plugins.Extensions.dFlash.plugin import dFlash
			self.session.open(dFlash)
		elif DBACKUP:
			from Plugins.Extensions.dBackup.plugin import dBackup
			self.session.open(dBackup)
		else:
			from Plugins.SystemPlugins.SoftwareManager.ImageBackup import ImageBackup
			self.session.open(ImageBackup)


# ####### Create MENULIST format #######################
def QuickMenuEntryComponent(name, description, long_description=None, width=540):
	pngname = name.replace(" ", "_")
	png = LoadPixmap("/usr/share/enigma2/icons/" + pngname + ".png")
	if png is None:
		png = LoadPixmap("/usr/share/enigma2/icons/default.png")
	sf = getSkinFactor()
	return [
		_(name),
		MultiContentEntryText(pos=(60 * sf, 2 * sf), size=((width - 60) * sf, 28 * sf), font=0, text=_(name)),
		MultiContentEntryText(pos=(60 * sf, 25 * sf), size=((width - 60) * sf, 22 * sf), font=1, text=_(description)),
		MultiContentEntryPixmapAlphaBlend(pos=(10 * sf, 5 * sf), size=(40 * sf, 40 * sf), flags=BT_SCALE, png=png),
		MultiContentEntryText(pos=(0, 0), size=(0, 0), font=0, text=_(long_description))
	]


def QuickSubMenuEntryComponent(name, description, long_description=None, width=540):
	sf = getSkinFactor()
	return [
		_(name),
		MultiContentEntryText(pos=(10 * sf, 2 * sf), size=((width - 10) * sf, 28 * sf), font=0, text=_(name)),
		MultiContentEntryText(pos=(10 * sf, 25 * sf), size=((width - 10) * sf, 22 * sf), font=1, text=_(description)),
		MultiContentEntryText(pos=(0, 0), size=(0, 0), font=0, text=_(long_description))
	]


class QuickMenuList(MenuList):
	def __init__(self, list, enableWrapAround=True):
		MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
		sf = getSkinFactor()
		self.l.setFont(0, gFont("Regular", int(19 * sf)))
		self.l.setFont(1, gFont("Regular", int(16 * sf)))
		self.l.setItemHeight(int(50 * sf))


class QuickMenuSubList(QuickMenuList):
	pass


class QuickMenuDevices(Screen):
	skin = """
	<screen name="QuickMenuDevices" position="center,center" size="840,525" title="Devices" flags="wfBorder">
		<widget source="devicelist" render="Listbox" position="30,46" size="780,450" font="Regular;16" scrollbarMode="showOnDemand" transparent="1" backgroundColorSelected="grey" foregroundColorSelected="black">
			<convert type="TemplatedMultiContent">
				{"template":
					[
					MultiContentEntryText(pos = (90, 0), size = (600, 30), font=0, text = 0),
					MultiContentEntryText(pos = (110, 30), size = (600, 50), font=1, flags = RT_VALIGN_TOP, text = 1),
					MultiContentEntryPixmapAlphaBlend(pos = (0, 0), size = (80, 80), png = 2),
					],
				"fonts": [gFont("Regular", 24),gFont("Regular", 20)],
				"itemHeight": 85
				}
			</convert>
		</widget>
		<widget name="lab1" zPosition="2" position="126,92" size="600,40" font="Regular;22" halign="center" backgroundColor="black" transparent="1" />
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle(_("Devices"))
		self["lab1"] = Label()
		self.devicelist = []
		self["devicelist"] = List(self.devicelist)
		self["actions"] = HelpableActionMap(self, ["CancelActions"], {
			"cancel": self.close,
		}, prio=0)
		self.activityTimer = eTimer()
		self.activityTimer.timeout.get().append(self.updateList2)
		self.updateList()

	def updateList(self, result=None, retval=None, extra_args=None):
		scanning = _("Wait please while scanning for devices...")
		self["lab1"].setText(scanning)
		self.activityTimer.start(10)

	def updateList2(self):
		def swapCallback(data, retVal, extraArgs):
			list2 = []
			swapdevices = data.replace("\n", "").split("/")
			with open("/proc/partitions") as fd:
				for line in fd.readlines():
					parts = line.strip().split()
					if not parts:
						continue
					device = parts[3]
					if not search(r"^sd[a-z][1-9][\d]*$", device):
						continue
					if device in list2:
						continue
					self.buildMy_rec(device, swapdevices)
					list2.append(device)
			self["devicelist"].list = self.devicelist
			if len(self.devicelist) == 0:
				self["lab1"].setText(_("No Devices Found !!"))
			else:
				self["lab1"].hide()
		self.activityTimer.stop()
		self.devicelist = []
		Console().ePopen("sfdisk -l /dev/sd? | grep swap | awk '{print $(NF-9)}'", swapCallback)

	def buildMy_rec(self, device, swapdevices):
		device2 = sub(r"[\d]", "", device)  # Strip device number.
		deviceType = realpath("/sys/block/%s/device" % device2)
		name = "USB: "
		myPixmap = "/usr/share/enigma2/icons/dev_usbstick.png"
		with open("/sys/block/%s/device/model" % device2) as fd:
			model = fd.read()
			model = str(model).replace("\n", "")
		des = ""
		if deviceType.find("/devices/pci") != -1:
			name = _("HARD DISK: ")
			myPixmap = "/usr/share/enigma2/icons/dev_hdd.png"
		name = name + model
		with open("/proc/mounts") as fd:
			for line in fd.readlines():
				if line.find(device) != -1:
					parts = line.strip().split()
					d1 = parts[1]
					dtype = parts[2]
					rw = parts[3]
					break
				else:
					if device in swapdevices:
						parts = line.strip().split()
						d1 = _("None")
						dtype = "swap"
						rw = _("None")
						break
					else:
						d1 = _("None")
						dtype = _("unavailable")
						rw = _("None")
		with open("/proc/partitions") as fd:
			for line in fd.readlines():
				if line.find(device) != -1:
					parts = line.strip().split()
					size = int(parts[2])
				else:
					try:
						with open("/sys/block/%s/%s/size" % (device2, device)) as fd:
							size = fd.read()
						size = str(size).replace("\n", "")
						size = int(size)
						size = size // 2
					except Exception:
						size = 0
				if ((size / 1024) / 1024) > 1:
					des = "%s: %s %s" % (_("Size"), str((size // 1024) // 1024), _("GB"))
				else:
					des = "%s: %s %s" % (_("Size"), str(size // 1024), _("MB"))
		if des != "":
			if rw.startswith("rw"):
				rw = " R/W"
			elif rw.startswith("ro"):
				rw = " R/O"
			else:
				rw = ""
			des = "%s\t%s%s\n%s /dev/%s\t%s%s%s" % (des, _("Mount: "), d1, _("Device: "), device, _("Type: "), dtype, rw)
			png = LoadPixmap(myPixmap)
			self.devicelist.append((name, des, png))
