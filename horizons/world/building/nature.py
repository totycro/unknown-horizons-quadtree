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

from horizons.world.building.building import BasicBuilding
from horizons.world.building.buildable import BuildableRect
from horizons.world.building.collectingbuilding import CollectingBuilding
from horizons.world.production.producer import ProducerBuilding
from horizons.entities import Entities
from horizons.constants import LAYERS
from horizons.world.storageholder import StorageHolder
from horizons.gui.tabs import ResourceDepositOverviewTab
from horizons.world.building.building import SelectableBuilding

class NatureBuilding(BuildableRect, BasicBuilding):
	"""Class for objects that are part of the environment, the nature"""
	walkable = True
	layer = LAYERS.OBJECTS

	def __init__(self, **kwargs):
		super(NatureBuilding, self).__init__(**kwargs)

class GrowingBuilding(ProducerBuilding, NatureBuilding):
	""" Class for stuff that grows, such as trees
	"""
	pass

class Field(GrowingBuilding):
	layer = LAYERS.FIELDS

class AnimalField(CollectingBuilding, Field):
	walkable = False
	def create_collector(self):
		self.animals = []
		for (animal, number) in self.session.db("SELECT unit_id, count FROM balance.animals \
		                                    WHERE building_id = ?", self.id):
			for i in xrange(0, number):
				Entities.units[animal](self, session=self.session)
		super(AnimalField, self).create_collector()

	def remove(self):
		while len(self.animals) > 0:
			self.animals[0].cancel()
			self.animals[0].remove()
		super(AnimalField, self).remove()

	def save(self, db):
		super(AnimalField, self).save(db)
		for animal in self.animals:
			animal.save(db)

	def load(self, db, worldid):
		super(AnimalField, self).load(db, worldid)
		self.animals = []
		# units are loaded separatly

class Tree(GrowingBuilding):
	buildable_upon = True
	layer = LAYERS.OBJECTS

class ResourceDeposit(SelectableBuilding, StorageHolder, NatureBuilding):
	"""Class for stuff like clay deposits."""
	tearable = False
	layer = LAYERS.OBJECTS
	tabs = [ ResourceDepositOverviewTab ]
	enemy_tabs = [ ResourceDepositOverviewTab ]
	walkable = False

	def __init__(self, inventory=None, *args, **kwargs):
		super(ResourceDeposit, self).__init__(*args, **kwargs)
		if inventory is None: # a new deposit
			for resource, min_amount, max_amount in \
			    self.session.db("SELECT resource, min_amount, max_amount FROM deposit_resources WHERE id = ?", \
			                    self.id):
				self.inventory.alter(resource, self.session.random.randint(min_amount, max_amount))
		else: # deposit was removed for mine, now build back
			for res, amount in inventory.iteritems():
				self.inventory.alter(res, amount)


	"""
	def load(self, *args, **kwargs):
		import pdb ; pdb.set_trace()
		super(ResourceDeposit, self).load(*args, **kwargs)
	"""


