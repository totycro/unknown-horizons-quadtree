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

from tabinterface import TabInterface
from horizons.util.python.roman_numerals import int_to_roman

class BuildTab(TabInterface):
	last_active_build_tab = None
	def __init__(self, tabindex = 0, events = {}):
		super(BuildTab, self).__init__(widget = 'build_menu/hud_build_tab' + str(tabindex) + '.xml')
		self.init_values()
		self.widget.mapEvents(events)
		self.button_up_image = 'content/gui/images/icons/hud/common/level%s_u.png' % tabindex
		self.button_active_image = 'content/gui/images/icons/hud/common/level%s_a.png' % tabindex
		self.button_down_image = 'content/gui/images/icons/hud/common/level%s_d.png' % tabindex
		self.button_hover_image = 'content/gui/images/icons/hud/common/level%s_h.png' % tabindex
		self.tooltip = unicode(_("Increment")+" "+int_to_roman(tabindex+1))
		self.tabindex = tabindex

	def refresh(self):
		pass

	def show(self):
		self.__class__.last_active_build_tab = self.tabindex
		super(BuildTab, self).show()

	def hide(self):
		super(BuildTab, self).hide()
