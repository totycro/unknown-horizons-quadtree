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
from random import randint

from fife import fife

import horizons.main
from horizons.scheduler import Scheduler

from horizons.world.concreteobject import ConcretObject
from horizons.world.settlement import Settlement
from horizons.ambientsound import AmbientSound
from horizons.util import ConstRect, Point, WorldObject, ActionSetLoader, decorators
from horizons.constants import RES, LAYERS, GAME
from horizons.world.building.buildable import BuildableSingle
from horizons.gui.tabs import EnemyBuildingOverviewTab


class BasicBuilding(AmbientSound, ConcretObject):
	"""Class that represents a building. The building class is mainly a super class for other buildings."""

	# basic properties of class
	walkable = False # whether we can walk on this building (true for e.g. streets, trees..)
	buildable_upon = False # whether we can build upon this building
	is_building = True
	tearable = True
	show_buildingtool_preview_tab = True # whether to show the tab of the building. not shown for
																			# e.g. paths. the tab hides a part of the map.
	extends_settlement = False
	enemy_tabs = (EnemyBuildingOverviewTab, )
	layer = LAYERS.OBJECTS

	log = logging.getLogger("world.building")

	"""
	@param x, y: int position of the building.
	@param owner: Player that owns the building.
	"""
	def __init__(self, x, y, rotation, owner, island, level=None, **kwargs):
		super(BasicBuilding, self).__init__(x=x, y=y, rotation=rotation, owner=owner, \
								                        island=island, **kwargs)
		self.__init(Point(x, y), rotation, owner, level)
		self.island = island
		self.settlement = self.island.get_settlement(Point(x, y)) or \
				self.island.add_settlement(self.position, self.radius, owner) if \
				owner is not None else None

	def __init(self, origin, rotation, owner, level=None):
		self.owner = owner
		if level is None:
			if self.owner is None:
				level = 0
			else:
				level = self.owner.settler_level
		self.level = level
		self._action_set_id = self.session.db.get_random_action_set(self.id, self.level)[0]
		self.position = ConstRect(origin, self.size[0]-1, self.size[1]-1)
		self.rotation = rotation
		if self.rotation in [135, 315]: # Rotate the rect correctly
			self.position = ConstRect(origin, self.size[1]-1, self.size[0]-1)
		else:
			self.position = ConstRect(origin, self.size[0]-1, self.size[1]-1)
		self._instance = self.getInstance(self.session, origin.x, origin.y, rotation = rotation)
		self._instance.setId(str(self.worldid))

		if self.running_costs != 0: # Get payout every 30 seconds
			Scheduler().add_new_object(self.get_payout, self, \
												         runin=self.session.timer.get_ticks(GAME.INGAME_TICK_INTERVAL), loops=-1)

		# play ambient sound, if available every 30 seconds
		if self.session.world.player == self.owner:
			play_every = 15 + randint(0, 15)
			for soundfile in self.soundfiles:
				self.play_ambient(soundfile, True, play_every)

	@property
	def name(self):
		return self._name

	def toggle_costs(self):
		self.running_costs , self.running_costs_inactive = \
				self.running_costs_inactive, self.running_costs

	def running_costs_active(self):
		return (self.running_costs > self.running_costs_inactive)

	def get_payout(self):
		"""gets the payout from the settlement in form of it's running costs"""
		self.owner.inventory.alter(RES.GOLD_ID, -self.running_costs)

	def remove(self):
		"""Removes the building"""
		self.log.debug("building: remove %s", self.worldid)
		self.island.remove_building(self)
		#instance is owned by layer...
		#self._instance.thisown = 1
		super(BasicBuilding, self).remove()
		# NOTE: removing layers from the renderer here will affect others players too!

	def save(self, db):
		super(BasicBuilding, self).save(db)
		db("INSERT INTO building (rowid, type, x, y, rotation, health, location, level) \
		   VALUES (?, ?, ?, ?, ?, ?, ?, ?)", \
								                       self.worldid, self.__class__.id, self.position.origin.x, \
								                       self.position.origin.y, self.rotation, \
								                       self.health, (self.settlement or self.island).worldid, self.level)

	def load(self, db, worldid):
		super(BasicBuilding, self).load(db, worldid)
		x, y, self.health, location, rotation, level= \
		 db("SELECT x, y, health, location, rotation, level FROM building WHERE rowid = ?", worldid)[0]

		owner_db = db("SELECT owner FROM settlement WHERE rowid = ?", location)
		owner = None if len(owner_db) == 0 else WorldObject.get_object_by_id(owner_db[0][0])

		self.__init(Point(x, y), rotation, owner, level)

		self.island, self.settlement = self.load_location(db, worldid)

		# island.add_building handles registration of building for island and settlement
		self.island.add_building(self, self.owner)

	def load_location(self, db, worldid):
		"""
		Does not alter self, just gets island and settlement from a savegame.
		@return: tuple: (island, settlement)
		"""
		location = db("SELECT location FROM building WHERE rowid = ?", worldid)[0][0]
		location_obj = WorldObject.get_object_by_id(location)
		if isinstance(location_obj, Settlement):
			# workaround: island can't be fetched from world, because it isn't fully constructed
			island_id = db("SELECT island FROM settlement WHERE rowid = ?", location_obj.worldid)[0][0]
			island = WorldObject.get_object_by_id(island_id)
			# settlement might not have been registered in island, so do it if getter fails
			settlement = island.get_settlement(self.position.center()) or \
								 island.add_existing_settlement(self.position, self.radius, location_obj)
		else: # loc is island
			island = location_obj
			settlement = None
		return (island, settlement)

	def get_buildings_in_range(self):
		# TODO Think about moving this to the Settlement class
		buildings = self.settlement.buildings
		ret_building = []
		for building in buildings:
			if building == self:
				continue
			if self.position.distance( building.position ) <= self.radius:
				ret_building.append( building )
		return ret_building

	def update_action_set_level(self, level=0):
		"""Updates this buildings action_set to a random actionset from the specified level
		(if an action set exists in that level).
		It's different to get_random_action_set is, that it just checks one lvl, and doesn't
		search for an action set everywhere, which makes it alot more effective, if you're
		just updating.
		@param level: int level number"""
		action_sets = self.session.db.get_random_action_set(self.id, level, exact_level=True)
		if action_sets:
			self._action_set_id = action_sets[0] # Set the new action_set
			self.act(self._action, repeating=True)

	def level_upgrade(self, lvl):
		"""Upgrades building to another increment"""
		self.level = lvl
		self.update_action_set_level(lvl)

	@classmethod
	def getInstance(cls, session, x, y, action='idle', level=0, rotation=45, **trash):
		"""Get a Fife instance
		@param x, y: The coordinates
		@param action: The action, defaults to 'idle'
		@param **trash: sometimes we get more keys we are not interested in
		"""
		assert isinstance(x, int)
		assert isinstance(y, int)
		#rotation = cls.check_build_rotation(session, rotation, x, y)
		# TODO: replace this with new buildable api
		# IDEA: save rotation in savegame
		facing_loc = fife.Location(session.view.layers[cls.layer])
		instance_coords = list((x, y, 0))
		layer_coords = list((x, y, 0))

		# NOTE:
		# nobody acctually knows how the code below works.
		# it's for adapting the facing location and instance coords in
		# different rotations, and works with all quadratic buildings (tested up to 4x4)
		# for the first unquadratic building (2x4), a hack fix was put into it.
		# the plan for fixing this code in general is to wait until there are more
		# unquadratic buildings, and figure out a pattern of the placement error,
		# then fix that generally.

		if rotation == 45:
			layer_coords[0] = x+cls.size[0]+3

			if cls.size[0] == 2 and cls.size[1] == 4:
				# HACK: fix for 4x2 buildings
				instance_coords[0] -= 1
				instance_coords[1] += 1

		elif rotation == 135:
			instance_coords[1] = y + cls.size[1] - 1
			layer_coords[1] = y-cls.size[1]-3

			if cls.size[0] == 2 and cls.size[1] == 4:
				# HACK: fix for 4x2 buildings
				instance_coords[0] += 1
				instance_coords[1] -= 1

		elif rotation == 225:
			instance_coords = list(( x + cls.size[0] - 1, y + cls.size[1] - 1, 0))
			layer_coords[0] = x-cls.size[0]-3

			if cls.size[0] == 2 and cls.size[1] == 4:
				# HACK: fix for 4x2 buildings
				instance_coords[0] += 1
				instance_coords[1] -= 1

		elif rotation == 315:
			instance_coords[0] = x + cls.size[0] - 1
			layer_coords[1] = y+cls.size[1]+3

			if cls.size[0] == 2 and cls.size[1] == 4:
				# HACK: fix for 4x2 buildings
				instance_coords[0] += 1
				instance_coords[1] -= 1

		else:
			return None
		instance = session.view.layers[cls.layer].createInstance(cls._object, \
											                                       fife.ModelCoordinate(*instance_coords))
		facing_loc.setLayerCoordinates(fife.ModelCoordinate(*layer_coords))

		action_set_id = session.db.get_random_action_set(cls.id, level=level)[0]
		fife.InstanceVisual.create(instance)

		action_sets = ActionSetLoader.get_action_sets()
		if not action in action_sets[action_set_id]:
			if 'idle' in action_sets[action_set_id]:
				action='idle'
			elif 'idle_full' in action_sets[action_set_id]:
				action='idle_full'
			else:
				# set first action
				action = action_sets[action_set_id].keys()[0]

		instance.act(action+"_"+str(action_set_id), facing_loc, True)
		return instance

	def init(self):
		"""init the building, called after the constructor is run and the building is positioned (the settlement variable is assigned etc)
		"""
		pass

	def start(self):
		"""This function is called when the building is built, to start production for example."""
		pass

	#@decorators.relese_mode(ret="Building")
	def __str__(self): # debug
		classname = horizons.main.db.cached_query("SELECT name FROM building where id = ?", self.id)[0][0]
		return '%s(id=%s;worldid=%s)' % (classname, self.id, \
								                     self.worldid)



class SelectableBuilding(object):
	range_applies_only_on_island = True
	selection_color = (255, 255, 0)
	_selected_tiles = [] # tiles that are selected. used for clean deselect.

	def select(self):
		"""Runs necessary steps to select the building."""
		renderer = self.session.view.renderer['InstanceRenderer']
		renderer.addOutlined(self._instance, self.selection_color[0], self.selection_color[1], \
								         self.selection_color[2], 1)
		self.__class__._selected_tiles = [] # TODO: this should be already empty here
		profile = False
		if profile:
			print 'selecting world id: ', self.worldid
			import cProfile as profile
			import tempfile
			outfilename = tempfile.mkstemp(text = True)[1]
			#print >>open("/tmp/a", "a"), "\n--- NEW DATA --\n"
			print 'profile to ', outfilename
			profile.runctx("self._do_select(renderer, self.position, self.session.world, self.settlement)", globals(), locals(), outfilename)
		else:
			#import time
			#a = time.time()
			self._do_select(renderer, self.position, self.session.world, self.settlement)
			#b = time.time()
			#print 'took: ', b-a

	def deselect(self):
		"""Runs neccassary steps to deselect the building."""
		renderer = self.session.view.renderer['InstanceRenderer']
		renderer.removeOutlined(self._instance)
		renderer.removeAllColored()

	def remove(self):
		super(SelectableBuilding, self).remove()
		if self.owner == self.session.world.player:
			self.deselect()

	@classmethod
	def select_building(cls, session, position, settlement):
		"""Select a hypothecial instance of this class. Use Case: Buildingtool.
		Only works on a subclass of BuildingClass, since it requires certain class attributes.
		@param session: Session instance
		@param position: Position of building, usually Rect
		@param settlement: Settlement instance the building belongs to"""
		renderer = session.view.renderer['InstanceRenderer']
		print 'calling select_building, len of selected_tiles: ' , len(cls._selected_tiles)

		import cProfile as profile
		import tempfile
		outfilename = tempfile.mkstemp(text = True)[1]
		print 'profile to ', outfilename
		# check if preview only moved a short distance (update instead of full redraw in this case)
		if False and hasattr(cls, "old_position") and \
		   abs(position.left - cls.old_position.left) <= 1 and \
		   abs(position.top - cls.old_position.top) <= 1:
			# position only changed at most one tile in both dimensions.
			# remove "outer ring" and draw new ring
			print 'doing update'
			#cls._do_update_selection(renderer, position, cls.old_position, session.world, settlement)
			profile.runctx( "cls._do_update_selection(renderer, position, cls.old_position, session.world, settlement)", globals(), locals(), outfilename)
		else:
			# recalculate and redraw full region
			"""
			"""
			print 'full recalc & redraw'
			cls.deselect_building(session)
			cls._do_select(renderer, position, session.world, settlement)
			#profile.runctx( "cls._do_select(renderer, position, session.world, settlement)", globals(), locals(), outfilename)

		cls.old_position = position

	@classmethod
	def deselect_building(cls, session):
		"""@see select_building,
		@return list of tiles that were deselected."""
		print 'calling deselect_building, len of selected_tiles: ' , len(cls._selected_tiles)
		remove_colored = session.view.renderer['InstanceRenderer'].removeColored
		for tile in cls._selected_tiles:
			remove_colored(tile._instance)
			if tile.object is not None:
				remove_colored(tile.object._instance)
		selected_tiles = cls._selected_tiles
		cls._selected_tiles = []
		return selected_tiles

	@classmethod
	@decorators.make_constants()
	def _do_update_selection(cls, renderer, position, old_position, world, settlement):
		# NOTE: only workes if range applies only on island
		# NOTE: only works if settlement is ground_holder
		ground_holder = settlement
		selected_tiles = set(cls._selected_tiles)
		def sign(x):
			if x < 0 : return -1
			elif x == 0: return 0
			return 1
		direction = ( sign(position.left - old_position.left),
		              sign(position.top - old_position.top) )

		# out with the old
		remove_colored = renderer.removeColored
		for coord_list in old_position.get_radius_border_coordinates(cls.radius).iteritems():
			if coord_list[0][0] != -direction[0] and \
			   coord_list[0][1] != -direction[1]:
				continue # drop the coords, that are in the opposite direction of the movement
			for coord in coord_list[1]:
				tile = ground_holder.ground_map.get(coord)
				if tile is not None:
					selected_tiles.discard(tile)
					remove_colored(tile._instance)
					if tile.object is not None:
						remove_colored(tile.object._instance)
		# in with the new
		add_colored = renderer.addColored
		for coord_list in position.get_radius_border_coordinates(cls.radius).iteritems():
			if False and coord_list[0][0] != direction[0] and \
			   coord_list[0][1] != direction[1]:
				continue
			for coord in coord_list[1]:
				tile = ground_holder.ground_map.get(coord)
				if tile is not None:
					selected_tiles.add(tile)
					add_colored(tile._instance, *cls.selection_color)
					if tile.object is not None:
						add_colored(tile.object._instance, *cls.selection_color)

		#cls._selected_tiles = list(selected_tiles)

	@classmethod
	@decorators.make_constants()
	def _do_select(cls, renderer, position, world, settlement):
		#print 'selecting at ', position, 'radius', cls.radius
		selected_tiles_add = cls._selected_tiles.append
		add_colored = renderer.addColored
		if cls.range_applies_only_on_island:
			island = world.get_island(position.origin)
			if island is None:
				return # preview isn't on island, and therefore invalid

			ground_holder = None # use settlement or island as tile provider (prefer settlement, since it contains fewer tiles)
			if settlement is None:
				ground_holder = island
			else:
				ground_holder = settlement

			selection_type = "cb3" # old | cb | cb2 | cb3 | iter | iter3

			if selection_type == "old":
				for tile in ground_holder.get_tiles_in_radius(position, cls.radius, include_self=True):
					try:
						if ( 'constructible' in tile.classes or 'coastline' in tile.classes ):
							selected_tiles_add(tile)
							add_colored(tile._instance, *cls.selection_color)
							# Add color to a building or tree that is present on the tile
							add_colored(tile.object._instance, *cls.selection_color)
					except AttributeError:
						pass # no tile or no object on tile

			# version with callback
			if selection_type == "cb":
				def cb(tile):
					selected_tiles_add(tile)
					add_colored(tile._instance, *cls.selection_color)
					# Add color to a building or tree that is present on the tile
					if tile.object is not None:
						add_colored(tile.object._instance, *cls.selection_color)
				settlement.tilequadtree.visit_radius_tiles(position, cls.radius, cb)

			if selection_type == "cb2":
				settlement.tilequadtree.visit_radius_tiles(position, cls.radius, selected_tiles_add)
				for tile in cls._selected_tiles:
					try:
						add_colored(tile._instance, *cls.selection_color)
						# Add color to a building or tree that is present on the tile
						add_colored(tile.object._instance, *cls.selection_color)
					except AttributeError:
						pass # no tile or no object on tile

			if selection_type == "cb3":
				#"""
				settlement.tilequadtree.visit_radius_tiles(position, cls.radius, selected_tiles_add)
				for tile in cls._selected_tiles:
					add_colored(tile._instance, *cls.selection_color)
					# Add color to a building or tree that is present on the tile
					if tile.object is not None:
						add_colored(tile.object._instance, *cls.selection_color)
				"""
				outer_part = position.get_radius_border_coordinates(cls.radius)
				for coord in outer_part[(-1, -1)] + outer_part[(1, 1)] + outer_part[(-1, 1)] + outer_part[(1, -1)]:
					if coord not in ground_holder.ground_map:
						continue
					tile = ground_holder.ground_map[coord]
					selected_tiles_add(tile)
					add_colored(tile._instance, *cls.selection_color)
					# Add color to a building or tree that is present on the tile
					if tile.object is not None:
						add_colored(tile.object._instance, *cls.selection_color)
				#"""

			if selection_type == "iter":
				# version with iteration
				for tile in settlement.tilequadtree.get_radius_tiles(position, cls.radius):
					try:
						selected_tiles_add(tile)
						add_colored(tile._instance, *cls.selection_color)
						# Add color to a building or tree that is present on the tile
						add_colored(tile.object._instance, *cls.selection_color)
					except AttributeError:
						pass # no tile or no object on tile

			if selection_type == "iter3":
				# version with iteration
				for tile in settlement.tilequadtree.get_radius_tiles(position, cls.radius):
					selected_tiles_add(tile)
					add_colored(tile._instance, *cls.selection_color)
					# Add color to a building or tree that is present on the tile
					if tile.object is not None:
						add_colored(tile.object._instance, *cls.selection_color)

		else:
			# we have to color water too
			for tile in world.get_tiles_in_radius(position.center(), cls.radius):
				try:
					if settlement is None or tile.settlement is None or tile.settlement == settlement:
						selected_tiles_add(tile)
						add_colored(tile._instance, *cls.selection_color)
						add_colored(tile.object._instance, *cls.selection_color)
				except AttributeError:
					pass # no tile or no object on tile


class DefaultBuilding(BasicBuilding, SelectableBuilding, BuildableSingle):
	"""Building with default properties, that does nothing."""
	pass
