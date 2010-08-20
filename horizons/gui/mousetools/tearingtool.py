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

from fife import fife

import horizons.main

from navigationtool import NavigationTool
from selectiontool import SelectionTool
from horizons.command.building import Tear
from horizons.util import Point

class TearingTool(NavigationTool):
	"""
	Represents a dangling tool to remove (tear) buildings.
	"""

	tear_selection_color = (255, 255, 255)

	def __init__(self, session):
		super(TearingTool, self).__init__(session)
		self.coords = None
		self.selected = set()
		self.oldedges = None
		self.tear_tool_active = True
		self.session.gui.on_escape = self.on_escape
		horizons.main.fife.cursor.set(fife.CURSOR_IMAGE, horizons.main.fife.tearing_cursor_image)

	def end(self):
		self.tear_tool_active = False
		horizons.main.fife.cursor.set(fife.CURSOR_IMAGE, horizons.main.fife.default_cursor_image)
		super(TearingTool, self).end()

	def mouseDragged(self, evt):
		coords = self.session.view.cam.toMapCoordinates(fife.ScreenPoint(evt.getX(), evt.getY()), False)
		if self.coords is None:
			self.coords = (int(round(coords.x)), int(round(coords.y)))
		self._mark(self.coords, (int(round(coords.x)), int(round(coords.y))))
		evt.consume()

	def mouseMoved(self,  evt):
		super(TearingTool, self).mouseMoved(evt)
		coords = self.session.view.cam.toMapCoordinates(fife.ScreenPoint(evt.getX(), evt.getY()), False)
		self._mark((int(round(coords.x)), int(round(coords.y))))
		evt.consume()

	def on_escape(self):
		self._mark()
		self.tear_tool_active = False
		self.session.cursor = SelectionTool(self.session)

	def mouseReleased(self,  evt):
		"""Tear selected instances and set selection tool as cursor"""
		if fife.MouseEvent.LEFT == evt.getButton():
			coords = self.session.view.cam.toMapCoordinates(fife.ScreenPoint(evt.getX(), evt.getY()), False)
			if self.coords is None:
				self.coords = (int(round(coords.x)), int(round(coords.y)))
			self._mark(self.coords, (int(round(coords.x)), int(round(coords.y))))
			for i in self.selected:
				Tear(i).execute(self.session)
			self.tear_tool_active = False
			self.session.cursor = SelectionTool(self.session)
			evt.consume()

	def mousePressed(self,  evt):
		if fife.MouseEvent.RIGHT == evt.getButton():
			self.on_escape()
		elif fife.MouseEvent.LEFT == evt.getButton():
			coords = self.session.view.cam.toMapCoordinates(fife.ScreenPoint(evt.getX(), evt.getY()), False)
			self.coords = (int(round(coords.x)), int(round(coords.y)))
			self._mark(self.coords)
		else:
			return
		self.tear_tool_active = False
		evt.consume()

	def _mark(self, *edges):
		"""Highights building instances and keeps self.selected up to date."""
		if len(edges) == 1:
			edges = (edges[0], edges[0])
		elif len(edges) == 2:
			edges = ((min(edges[0][0], edges[1][0]), min(edges[0][1], edges[1][1])), \
					 (max(edges[0][0], edges[1][0]), max(edges[0][1], edges[1][1])))
		else:
			edges = None
		if self.oldedges != edges or edges is None:
			for i in self.selected:
				self.session.view.renderer['InstanceRenderer'].removeColored(i._instance)
			self.selected = set()
			self.oldedges = edges
		if edges is not None:
			for x in xrange(edges[0][0], edges[1][0] + 1):
				for y in xrange(edges[0][1], edges[1][1] + 1):
					b = self.session.world.get_building(Point(x, y))
					if b is not None and b.tearable and self.session.world.player == b.owner:
						self.selected.add(b)
			for i in self.selected:
				self.session.view.renderer['InstanceRenderer'].addColored(i._instance, \
				                                                          *self.tear_selection_color)
