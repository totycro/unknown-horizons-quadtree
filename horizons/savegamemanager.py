# ###################################################
# Copyright (C) 2009 The Unknown Horizons Team
# team@unknown-horizons.org
# This file is part of Unknown Horizons.
#
# Unknown Horizons is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the
# Free Software Foundation, Inc.,
# 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
# ###################################################
import sqlite3
import tempfile
import logging
import os
import os.path
import glob
import time

from horizons.constants import PATHS, VERSION
from horizons.util import DbReader

import horizons.main

class SavegameManager(object):
	"""Controls savegamefiles.

	This class is rather a namespace than a "real" object, since it has no members.
	The instance in horizons.main is nevertheless important, since it creates
	the savegame directories

	The return values is usually a tuple: (list_of_savegame_files, list_of_savegame_names),
	where savegame_names are meant for displaying to the user.


	IMPORTANT:
	Whenever you make a change that breaks compatibility with old savegames, increase 
	horizons/constans.py:VERSION.SAVEGAMEREVISION by one !!
	"""
	log = logging.getLogger("savegamemanager")

	savegame_dir = PATHS.USER_DIR + "/save"
	autosave_dir = savegame_dir+"/autosave"
	quicksave_dir = savegame_dir+"/quicksave"
	demo_dir = "content/demo"
	maps_dir = "content/maps"
	scenarios_dir = "content/scenarios"

	savegame_extension = "sqlite"
	scenario_extension = "yaml"

	autosave_basename = "autosave-"
	quicksave_basename = "quicksave-"

	autosave_filenamepattern = autosave_basename+'%(timestamp)d.'+savegame_extension
	quicksave_filenamepattern = quicksave_basename+'%(timestamp).4f.'+savegame_extension

	display_timeformat = "%y/%m/%d %H:%M"

	# metadata of a savegame with default values
	savegame_metadata = { 'timestamp' : -1,	'savecounter' : 0, 'savegamerev' : 0 }
	savegame_metadata_types = { 'timestamp' : float, 'savecounter' : int, 'savegamerev': int }


	@classmethod
	def init(self):
		# create savegame directory if it does not exist
		if not os.path.isdir(self.autosave_dir):
			os.makedirs(self.autosave_dir)
		if not os.path.isdir(self.quicksave_dir):
			os.makedirs(self.quicksave_dir)

	@classmethod
	def __get_displaynames(self, files):
		"""Returns list of names files, that should be displayed to the user.
		@param files: iterable object containing strings"""
		displaynames = []
		def get_timestamp_string(savegameinfo):
			if savegameinfo['timestamp'] == -1:
				return ""
			else:
				return time.strftime("%y/%m/%d %H:%M", time.localtime(savegameinfo['timestamp']))

		for f in files:
			if f.startswith(self.autosave_dir):
				name = "Autosave %s" % get_timestamp_string(self.get_metadata(f))
			elif f.startswith(self.quicksave_dir):
				name = "Quicksave %s" % get_timestamp_string(self.get_metadata(f))
			else:
				name = os.path.splitext(os.path.basename(f))[0]

			if not isinstance(name, unicode):
				name = unicode(name, errors='replace') # only use unicode strings, guichan needs them
			displaynames.append( name )
		return displaynames

	@classmethod
	def __get_saves_from_dirs(self, dirs, include_displaynames = True, filename_extension = None):
		"""Internal function, that returns the saves of a dir"""
		if not filename_extension:
			filename_extension = self.savegame_extension
		files = [f for p in dirs for f in glob.glob(p+'/*.'+filename_extension) if \
						 os.path.isfile(f)]
		files.sort()
		if include_displaynames:
			return (files, self.__get_displaynames(files))
		else:
			return (files,)

	@classmethod
	def create_filename(self, savegamename):
		"""Returns the full path for a regular save of the name savegamename"""
		name = "%s/%s.%s" % (self.savegame_dir, savegamename, self.savegame_extension)
		self.log.debug("Savegamemanager: creating save-filename: %s", name)
		return name

	@classmethod
	def create_autosave_filename(self):
		"""Returns the filename for an autosave"""
		name = "%s/%s" % (self.autosave_dir, \
												 self.autosave_filenamepattern % {'timestamp':time.time()})
		self.log.debug("Savegamemanager: creating autosave-filename: %s", name)
		return name

	@classmethod
	def create_quicksave_filename(self):
		"""Returns the filename for a quicksave"""
		name = "%s/%s" % (self.quicksave_dir, \
												 self.quicksave_filenamepattern % {'timestamp':time.time()})
		self.log.debug("Savegamemanager: creating quicksave-filename: %s", name)
		return name

	@classmethod
	def delete_dispensable_savegames(self, autosaves = False, quicksaves = False):
		"""Delete savegames that are no longer needed
		@param autosaves, quicksaves: Bool, set to true if this kind of saves should be cleaned
		"""
		def tmp_del(pattern, limit):
			files = glob.glob(pattern)
			if len(files) > limit:
				files.sort()
				for i in xrange(0, len(files) - limit):
					os.unlink(files[i])

		if autosaves:
			tmp_del("%s/*.%s" % (self.autosave_dir, self.savegame_extension),
							horizons.main.fife.get_uh_setting("AutosaveMaxCount"))
		if quicksaves:
			tmp_del("%s/*.%s" % (self.quicksave_dir, self.savegame_extension),
							horizons.main.fife.get_uh_setting("QuicksaveMaxCount"))

	@classmethod
	def get_metadata(cls, savegamefile):
		"""Returns metainfo of a savegame as dict.
		"""
		db = DbReader(savegamefile)
		metadata = cls.savegame_metadata.copy()

		for key in metadata.iterkeys():
			result = db("SELECT `value` FROM `metadata` WHERE `name` = ?", key)
			if len(result) > 0:
				assert(len(result) == 1)
				metadata[key] = cls.savegame_metadata_types[key](result[0][0])

		screenshot_data = None
		try:
			screenshot_data = db("SELECT value from metadata_blob where name = ?", "screen")[0][0]
		except IndexError: pass
		except sqlite3.OperationalError: pass
		metadata['screenshot'] = screenshot_data

		return metadata

	@classmethod
	def write_metadata(cls, db, savecounter):
		"""Writes metadata to db.
		@param db: DbReader
		@param savecounter: int"""
		metadata = cls.savegame_metadata.copy()
		metadata['timestamp'] = time.time()
		metadata['savecounter'] = savecounter
		metadata['savegamerev'] = VERSION.SAVEGAMEREVISION

		for key, value in metadata.iteritems():
			db("INSERT INTO metadata(name, value) VALUES(?, ?)", key, value)

		# special handling for screenshot (as blob)
		"""
		import horizons.main
		screenshot_fd, screenshot_filename = tempfile.mkstemp()
		horizons.main.fife.engine.getRenderBackend().captureScreen(screenshot_filename)
		screenshot_data = os.fdopen(screenshot_fd, "r").read()
		db("INSERT INTO metadata_blob values(?, ?)", "screen", sqlite3.Binary(screenshot_data))
		os.unlink(screenshot_filename)
		"""

	@classmethod
	def get_regular_saves(self, include_displaynames = True):
		"""Returns all savegames, that were saved via the ingame save dialog"""
		self.log.debug("Savegamemanager: regular saves from: %s", self.savegame_dir)
		return self.__get_saves_from_dirs([self.savegame_dir], \
										  include_displaynames = include_displaynames)

	@classmethod
	def get_maps(cls, include_displaynames = True):
		cls.log.debug("Savegamemanager: get maps from %s", cls.maps_dir)
		return cls.__get_saves_from_dirs([cls.maps_dir], include_displaynames = include_displaynames)

	@classmethod
	def get_saves(self, include_displaynames = True):
		"""Returns all savegames"""
		self.log.debug("Savegamemanager: get saves from %s, %s, %s, %s", self.savegame_dir, \
									 self.autosave_dir, self.quicksave_dir, self.demo_dir)
		return self.__get_saves_from_dirs([self.savegame_dir, self.autosave_dir, \
										   self.quicksave_dir, self.demo_dir], \
										  include_displaynames = include_displaynames)

	@classmethod
	def get_quicksaves(self, include_displaynames = True):
		"""Returns all savegames, that were saved via quicksave"""
		self.log.debug("Savegamemanager: quicksaves from: %s", self.quicksave_dir)
		return self.__get_saves_from_dirs([self.quicksave_dir], \
										  include_displaynames = include_displaynames)

	@classmethod
	def get_scenarios(self, include_displaynames = True):
		"""Returns all scenarios"""
		self.log.debug("Savegamemanager: scenarios from: %s", self.scenarios_dir)
		return self.__get_saves_from_dirs([self.scenarios_dir], \
										  include_displaynames = include_displaynames,
		                  filename_extension = self.scenario_extension)

	@classmethod
	def get_savegamename_from_filename(cls, savegamefile):
		"""Returns a displayable name, extracted from a filename"""
		name = os.path.basename(savegamefile)
		name = name.rsplit(".%s"%cls.savegame_extension, 1)[0]
		cls.log.debug("Savegamemanager: savegamename: %s", name)
		return name
