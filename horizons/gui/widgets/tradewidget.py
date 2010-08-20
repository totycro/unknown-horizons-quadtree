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
import logging
from fife.extensions import pychan

import horizons.main

from horizons.gui.widgets.imagefillstatusbutton import ImageFillStatusButton
from horizons.i18n import load_xml_translated
from horizons.command.uioptions import TransferResource

class TradeWidget(object):
	log = logging.getLogger("gui.tradewidget")

	# objects within this radius can be traded with, only used if the
	# main instance does not have a radius attribute
	radius = 5

	# map the size buttons in the gui to an amount
	exchange_size_buttons = {
	  1: 'size_1',
	  5: 'size_2',
	  10: 'size_3',
	  20: 'size_4',
	  50: 'size_5'
	  }

	images = {
	  #'box_highlighted': 'content/gui/images/icons/hud/ship/civil_32_h.png',
	  'box_highlighted': 'content/gui/images/icons/hud/ship/button_small_a.png',
	  'box': 'content/gui/images/icons/hud/ship/button_small.png'
	  }

	def __init__(self, instance):
		"""
		@param instance: ship instance used for trading
		"""
		self.widget = load_xml_translated('ship/trade.xml')
		self.widget.position = (
			horizons.main.fife.engine_settings.getScreenWidth() - self.widget.size[0],
			157
		)
		self.widget.stylize('menu_black')
		self.widget.findChild(name='headline').stylize('headline') # style definition for headline
		events = {}
		for k, v in self.exchange_size_buttons.iteritems():
			events[v] = pychan.tools.callbackWithArguments(self.set_exchange, k)
		self.widget.mapEvents(events)
		self.instance = instance
		self.partner = None
		self.set_exchange(10, initial=True)
		self.draw_widget()
		if hasattr(self.instance, 'radius'):
			self.radius = self.instance.radius

	def draw_widget(self):
		self.partners = self.find_partner()
		if len(self.partners) > 0:
			dropdown = self.widget.findChild(name='partners')
			#dropdown.setInitialData([item.settlement.name for item in self.partners])
			#dropdown.capture(pychan.tools.callbackWithArguments(self.set_partner, dropdown.getData()))
			nearest_partner = self.get_nearest_partner(self.partners)
			#dropdown.setData(nearest_partner)
			dropdown.text = unicode(self.partners[nearest_partner].settlement.name) # label fix for release use only
			self.partner = self.partners[nearest_partner]
			inv_partner = self.widget.findChild(name='inventory_partner')
			inv_partner.init(self.instance.session.db, self.partner.inventory)
			for button in self.get_widgets_by_class(inv_partner, ImageFillStatusButton):
				button.button.capture(pychan.tools.callbackWithArguments(self.transfer, button.res_id, self.partner, self.instance))
			inv = self.widget.findChild(name='inventory_ship')
			inv.init(self.instance.session.db, self.instance.inventory)
			for button in self.get_widgets_by_class(inv, ImageFillStatusButton):
				button.button.capture(pychan.tools.callbackWithArguments(self.transfer, button.res_id, self.instance, self.partner))
			self.widget.adaptLayout()

	def set_partner(self, partner_id):
		self.partner = self.partners[partner_id]

	def hide(self):
		self.widget.hide()
		self.instance.inventory.remove_change_listener(self.draw_widget)
		self.partner.inventory.remove_change_listener(self.draw_widget)

	def show(self):
		self.widget.show()
		self.instance.inventory.add_change_listener(self.draw_widget)
		self.partner.inventory.add_change_listener(self.draw_widget)

	def set_exchange(self, size, initial = False):
		"""
		@param initial: bool, use it to set exchange size when initing the widget
		"""
		# highlight box with selected amount and deselect old highlighted
		if not initial:
			old_box = self.widget.findChild(name= self.exchange_size_buttons[self.exchange])
			old_box.up_image = self.images['box']

		box_h = self.widget.findChild(name= self.exchange_size_buttons[size])
		box_h.up_image = self.images['box_highlighted']

		self.exchange = size
		self.log.debug("Tradewidget: exchange size now: %s", size)
		if not initial:
			self.draw_widget()

	def transfer(self, res_id, transfer_from, transfer_to):
		"""Transfers self.exchange tons of resid from transfer_from to transfer_to"""
		if self.instance.position.distance(transfer_to.position) <= self.radius and \
			 transfer_to is not None and transfer_from is not None:
			self.log.debug('TradeWidget : Transferring %s of res %s from %s to %s', self.exchange, \
			               res_id, transfer_from.name, transfer_to.name)
			TransferResource(self.exchange, res_id, transfer_from, transfer_to).execute(self.instance.session)
			# update gui
			self.draw_widget()

	def get_widgets_by_class(self, parent_widget, widget_class):
		"""Gets all widget of a certain widget class from the tab. (e.g. pychan.widgets.Label for all labels)"""
		children = []
		def _find_widget(widget):
			if isinstance(widget, widget_class):
				children.append(widget)
		parent_widget.deepApply(_find_widget)
		return children

	def find_partner(self):
		"""find all partners in radius"""
		partners = []
		branch_offices = self.instance.session.world.get_branch_offices(position=self.instance.position, radius=self.radius, owner=self.instance.owner)
		if branch_offices is not None:
			partners.extend(branch_offices)
		return partners

	def get_nearest_partner(self, partners):
		nearest = None
		nearest_dist = None
		for partner in partners:
			dist = partner.position.distance(self.instance.position)
			nearest = partners.index(partner) if dist < nearest_dist or nearest_dist is None else nearest
			nearest_dist = dist if dist < nearest_dist or nearest_dist is None else nearest_dist
		return nearest
