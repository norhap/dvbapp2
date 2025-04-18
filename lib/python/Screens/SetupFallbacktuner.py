from enigma import getPeerStreamingBoxes

from Screens.Setup import Setup
from Components.config import config, configfile, ConfigSelection, ConfigIP, ConfigInteger, ConfigBoolean
from Components.ImportChannels import ImportChannels
from Tools.Directories import isPluginInstalled
from Screens.MessageBox import MessageBox
from Screens.InfoBar import InfoBar
from Screens.Standby import TryQuitMainloop

class SetupFallbacktuner(Setup):
	def __init__(self, session):
		self.createConfig()
		Setup.__init__(self, session, "Fallbacktuner")
		self.remote_fallback_prev = config.usage.remote_fallback_import.value

	def createConfig(self):

		def set_avahiselect_seperate(configElement):
			seperateBoxes = [("same", _("Same as stream"))] + self.peerStreamingBoxes
			if configElement.value not in ("url", "ip") and configElement.value in seperateBoxes:
				seperateBoxes.remove(configElement.value)
			default = config.usage.remote_fallback_import_url.value if config.usage.remote_fallback_import_url.value and config.usage.remote_fallback_import_url.value != config.usage.remote_fallback.value else "same"
			self.avahiselect_seperate = ConfigSelection(default=default, choices=seperateBoxes)
			default = config.usage.remote_fallback_dvb_t.value if config.usage.remote_fallback_dvb_t.value and config.usage.remote_fallback_dvb_t.value != config.usage.remote_fallback.value else "same"
			self.avahi_dvb_t = ConfigSelection(default=default, choices=seperateBoxes)
			default = config.usage.remote_fallback_dvb_c.value if config.usage.remote_fallback_dvb_c.value and config.usage.remote_fallback_dvb_c.value != config.usage.remote_fallback.value else "same"
			self.avahi_dvb_c = ConfigSelection(default=default, choices=seperateBoxes)
			default = config.usage.remote_fallback_atsc.value if config.usage.remote_fallback_atsc.value and config.usage.remote_fallback_atsc.value != config.usage.remote_fallback.value else "same"
			self.avahi_atsc = ConfigSelection(default=default, choices=seperateBoxes)

		self.peerStreamingBoxes = getPeerStreamingBoxes() + [("ip", _("Enter IP address")), ("url", _("Enter URL"))]
		peerDefault = peerDefault_sepearate = None
		if config.usage.remote_fallback.value:
			peerDefault = peerDefault_sepearate = config.usage.remote_fallback.value
			if config.usage.remote_fallback.value and config.usage.remote_fallback.value not in self.peerStreamingBoxes:
				self.peerStreamingBoxes = [config.usage.remote_fallback.value] + self.peerStreamingBoxes
			if config.usage.remote_fallback_import_url.value and config.usage.remote_fallback_import_url.value not in self.peerStreamingBoxes:
				self.peerStreamingBoxes = [config.usage.remote_fallback_import_url.value] + self.peerStreamingBoxes
			if config.usage.remote_fallback_dvb_t.value and config.usage.remote_fallback_dvb_t.value not in self.peerStreamingBoxes:
				self.peerStreamingBoxes = [config.usage.remote_fallback_dvb_t.value] + self.peerStreamingBoxes
			if config.usage.remote_fallback_dvb_c.value and config.usage.remote_fallback_dvb_c.value not in self.peerStreamingBoxes:
				self.peerStreamingBoxes = [config.usage.remote_fallback_dvb_c.value] + self.peerStreamingBoxes
			if config.usage.remote_fallback_atsc.value and config.usage.remote_fallback_atsc.value not in self.peerStreamingBoxes:
				self.peerStreamingBoxes = [config.usage.remote_fallback_atsc.value] + self.peerStreamingBoxes
		self.avahiselect = ConfigSelection(default=peerDefault, choices=self.peerStreamingBoxes)
		self.avahiselect.addNotifier(set_avahiselect_seperate)
		try:
			ipDefault = [int(x) for x in config.usage.remote_fallback.value.split(":")[1][2:].split(".")]
			portDefault = int(config.usage.remote_fallback.value.split(":")[2])
		except:
			ipDefault = [0, 0, 0, 0]
			portDefault = 8001
		self.ip = ConfigIP(default=ipDefault, auto_jump=True)
		self.port = ConfigInteger(default=portDefault, limits=(1, 65535))
		self.ip_seperate = ConfigIP(default=ipDefault, auto_jump=True)
		self.port_seperate = ConfigInteger(default=portDefault, limits=(1, 65535))
		self.ip_dvb_t = ConfigIP(default=ipDefault, auto_jump=True)
		self.port_dvb_t = ConfigInteger(default=portDefault, limits=(1, 65535))
		self.ip_dvb_c = ConfigIP(default=ipDefault, auto_jump=True)
		self.port_dvb_c = ConfigInteger(default=portDefault, limits=(1, 65535))
		self.ip_atsc = ConfigIP(default=ipDefault, auto_jump=True)
		self.port_atsc = ConfigInteger(default=portDefault, limits=(1, 65535))

	def keySave(self):
		if isPluginInstalled("FastChannelChange"):  # OpenSPA [norhap] sync with FCC.
			if config.usage.remote_fallback_enabled.value and config.plugins.fccsetup.activate.value:
				self.syncWithFCC()
				return
		if self.avahiselect.value == "ip":
			config.usage.remote_fallback.value = "http://%d.%d.%d.%d:%d" % (tuple(self.ip.value) + (self.port.value,))
		elif self.avahiselect.value != "url":
			config.usage.remote_fallback.value = self.avahiselect.value
		if self.avahiselect_seperate.value == "ip":
			config.usage.remote_fallback_import_url.value = "http://%d.%d.%d.%d:%d" % (tuple(self.ip_seperate.value) + (self.port_seperate.value,))
		elif self.avahiselect_seperate.value == "same":
			config.usage.remote_fallback_import_url.value = ""
		elif self.avahiselect_seperate.value != "url":
			config.usage.remote_fallback_import_url.value = self.avahiselect_seperate.value
		if config.usage.remote_fallback_alternative.value and not (self.avahi_dvb_t.value == self.avahi_dvb_c.value == self.avahi_atsc.value == "same"):
			if self.avahi_dvb_t.value == "ip":
				config.usage.remote_fallback_dvb_t.value = "http://%d.%d.%d.%d:%d" % (tuple(self.ip_dvb_t.value) + (self.port_dvb_t.value,))
			elif self.avahi_dvb_t.value == "same":
				config.usage.remote_fallback_dvb_t.value = config.usage.remote_fallback.value
			elif self.avahi_dvb_t.value != "url":
				config.usage.remote_fallback_dvb_t.value = self.avahi_dvb_t.value
			if self.avahi_dvb_c.value == "ip":
				config.usage.remote_fallback_dvb_c.value = "http://%d.%d.%d.%d:%d" % (tuple(self.ip_dvb_c.value) + (self.port_dvb_c.value,))
			elif self.avahi_dvb_c.value == "same":
				config.usage.remote_fallback_dvb_c.value = config.usage.remote_fallback.value
			elif self.avahi_dvb_c.value != "url":
				config.usage.remote_fallback_dvb_c.value = self.avahi_dvb_c.value
			if self.avahi_atsc.value == "ip":
				config.usage.remote_fallback_atsc.value = "http://%d.%d.%d.%d:%d" % (tuple(self.ip_atsc.value) + (self.port_atsc.value,))
			elif self.avahi_atsc.value == "same":
				config.usage.remote_fallback_atsc.value = config.usage.remote_fallback.value
			elif self.avahi_atsc.value != "url":
				config.usage.remote_fallback_atsc.value = self.avahi_atsc.value
		else:
			config.usage.remote_fallback_dvb_t.value = config.usage.remote_fallback_dvb_c.value = config.usage.remote_fallback_atsc.value = ""
			config.usage.remote_fallback_alternative.value = False
		if config.usage.remote_fallback_import_url.value == config.usage.remote_fallback.value:
			config.usage.remote_fallback_import_url.value = ""
		config.usage.remote_fallback_enabled.save()
		config.usage.remote_fallback_import.save()
		config.usage.remote_fallback_import_url.save()
		config.usage.remote_fallback_import_restart.save()
		config.usage.remote_fallback_import_standby.save()
		config.usage.remote_fallback_extension_menu.save()
		config.usage.remote_fallback_ok.save()
		config.usage.remote_fallback_nok.save()
		config.usage.remote_fallback.save()
		config.usage.remote_fallback_external_timer.save()
		config.usage.remote_fallback_external_timer_default.save()
		config.usage.remote_fallback_openwebif_customize.save()
		config.usage.remote_fallback_openwebif_userid.save()
		config.usage.remote_fallback_openwebif_password.save()
		config.usage.remote_fallback_openwebif_port.save()
		config.usage.remote_fallback_alternative.save()
		config.usage.remote_fallback_dvb_t.save()
		config.usage.remote_fallback_dvb_c.save()
		config.usage.remote_fallback_atsc.save()
		configfile.save()
		if not self.remote_fallback_prev and config.usage.remote_fallback_import.value:
			ImportChannels()
		self.close(False)

	def syncWithFCC(self, answer):  # OpenSPA [norhap] sync with FCC.
		from Screens.Standby import TryQuitMainloop
		if answer:
			config.plugins.fccsetup.activate.value = False
			config.plugins.fccsetup.activate.save()
			self.session.open(TryQuitMainloop, 3)
		else:
			config.usage.remote_fallback_enabled.value = False
			config.usage.remote_fallback_enabled.save()

	def syncWithFCC(self):  # sync with FCC.
		def disableFCC(answer=False):
			if answer:
				config.plugins.fccsetup.activate.value = False
				config.plugins.fccsetup.activate.save()
				config.usage.remote_fallback_enabled.value = True
				config.usage.remote_fallback_enabled.save()
				self.session.open(TryQuitMainloop, 3)
			else:
				config.usage.remote_fallback_enabled.value = False
				Setup.keySave(self)

		inTimeshift = InfoBar and InfoBar.instance and InfoBar.ptsGetTimeshiftStatus(InfoBar.instance)
		if not inTimeshift and not self.session.nav.getRecordings():
			self.session.openWithCallback(disableFCC, MessageBox, _("FCC usage will be disabled to use the fallback tuner.\nEnigma2 needs to be restarted.\nDo you want to do it now?"), type=MessageBox.TYPE_YESNO, simple=True)
		else:
			config.usage.remote_fallback_enabled.value = False
			Setup.keySave(self)
