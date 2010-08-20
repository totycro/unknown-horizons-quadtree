# -*- coding: utf-8 -*-
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

__all__ = ['island', 'nature', 'player', 'settlement', 'ambientsound']

import weakref
import random
import logging

import horizons.main
from horizons.world.island import Island
from horizons.world.player import Player, HumanPlayer
from horizons.util import Point, Color, Rect, LivingObject, Circle
from horizons.constants import UNITS, BUILDINGS, RES, GROUND
from horizons.ai.trader import Trader
from horizons.ai.pirate import Pirate
from horizons.entities import Entities
from horizons.util import decorators

class World(LivingObject):
	"""The World class represents an Unknown Horizons map with all its units, grounds, buildings, etc.

	   * players - a list of all the session's players - Player instances
	   * islands - a list of all the map's islands - Island instances
	   * grounds - a list of all the map's groundtiles
	   * ground_map - a dictionary that binds tuples of coordinates with a reference to the tile:
	                  { (x, y): tileref, ...}
					  This is important for pathfinding and quick tile fetching.
	   * ships 		- a list of all the ships ingame - horizons.world.units.ship.Ship instances
	   * ship_map 	- same as ground_map, but for ships
	   * session 	- reference to horizons.session.Session instance of the current game
	   * water 		- List of coordinates that are water
	   * trader 	- The worlds ingame free trader player instance
	   TUTORIAL: You should now check out the _init() function.
	"""
	log = logging.getLogger("world")
	def __init__(self, session):
		"""
		@param session: instance of session the world belongs to.
		"""
		self.inited = False
		self.session = session
		super(World, self).__init__()

	def end(self):
		self.session = None
		self.properties = None
		self.players = None
		self.player = None
		self.ground_map = None
		self.water = None
		self.ship_map = None
		self.ships = None
		self.trader = None
		self.islands = None
		super(World, self).end()

	@decorators.make_constants()
	def _init(self, savegame_db):
		"""
		@param savegame_db: Dbreader with loaded savegame database
		"""
		#load properties
		self.properties = {}
		for (name, value) in savegame_db("SELECT name, value FROM map_properties"):
			self.properties[name] = value

		# create playerlist
		self.players = []
		self.player = None # player sitting in front of this machine
		self.trader = None
		self.pirate = None

		# load player
		human_players = []
		for player_worldid, client_id in savegame_db("SELECT rowid, client_id FROM player WHERE is_trader = 0"):
			player = None
			# check if player is an ai
			ai_data = self.session.db("SELECT class_package, class_name FROM ai WHERE id = ?", client_id)
			if len(ai_data) > 0:
				class_package, class_name = ai_data[0]
				# import ai class and call load on it
				module = __import__('horizons.ai.'+class_package, fromlist=[class_name])
				ai_class = getattr(module, class_name)
				player = ai_class.load(self.session, savegame_db, player_worldid)
			else: # no ai
				player = HumanPlayer.load(self.session, savegame_db, player_worldid)
			self.players.append(player)

			if client_id == horizons.main.fife.get_uh_setting("ClientID"):
				self.player = player
			elif client_id is not None and len(ai_data) == 0:
				# possible human player candidate with different client id
				human_players.append(player)

		if self.player is None:
			# we have no human player.
			# check if there is only one player with an id (i.e. human player)
			# this would be the case if the savegame originates from a different installation.
			# if there's more than one of this kind, we can't be sure what to select.
			# TODO: create interface for selecting player, if we want this
			if(len(human_players) == 1):
				# exactly one player, we can quite safely use this one
				self.player = human_players[0]

		if self.player is None and self.session.is_game_loaded():
			self.log.warning('WARNING: Cannot autoselect a player because there are no \
			or multiple candidates.')

		#load islands
		self.islands = []
		for (islandid,) in savegame_db("SELECT rowid + 1000 FROM island"):
			island = Island(savegame_db, islandid, self.session)
			self.islands.append(island)

		#calculate map dimensions
		self.min_x, self.min_y, self.max_x, self.max_y = None, None, None, None
		for i in self.islands:
			self.min_x = i.rect.left if self.min_x is None or i.rect.left < self.min_x else self.min_x
			self.min_y = i.rect.top if self.min_y is None or i.rect.top < self.min_y else self.min_y
			self.max_x = i.rect.right if self.max_x is None or i.rect.right > self.max_x else self.max_x
			self.max_y = i.rect.bottom if self.max_y is None or i.rect.bottom > self.max_y else self.max_y
		self.min_x -= 10
		self.min_y -= 10
		self.max_x += 10
		self.max_y += 10

		self.map_dimensions = Rect.init_from_borders(self.min_x, self.min_y, self.max_x, self.max_y)

		#add water
		self.log.debug("Filling world with water...")
		self.ground_map = {}
		default_grounds = Entities.grounds[int(self.properties.get('default_ground', GROUND.WATER))]

		for x in xrange(self.min_x, self.max_x, 10):
			for y in xrange(self.min_y, self.max_y, 10):
				ground = default_grounds(self.session, x, y)
				# -5 to 5 to accomodate for nen shifted 10x10 tile graphic
				for x_offset in xrange(-5,6):
					for y_offset in xrange(-5,6):
						self.ground_map[(x+x_offset, y+y_offset)] = ground

		# "unfill" parts that are occupied by island
		# TODO: check if constructing a list of water coords is faster than calling the Ground() so many times
		for island in self.islands:
			for coord in island.ground_map:
				if coord in self.ground_map:
					del self.ground_map[coord]

		self.num_water = len(self.ground_map)
		self.water = list(self.ground_map)

		# create ship position list. entries: ship_map[(x, y)] = ship
		self.ship_map = {}

		# create shiplist, which is currently used for saving ships
		# and having at least one reference to them
		self.ships = []

		if self.session.is_game_loaded():
			# for now, we have one trader in every game, so this is safe:
			trader_id = savegame_db("SELECT rowid FROM player WHERE is_trader = 1")[0][0]
			self.trader = Trader.load(self.session, savegame_db, trader_id)

		# load all units (we do it here cause all buildings are loaded by now)
		for (worldid, typeid) in savegame_db("SELECT rowid, type FROM unit ORDER BY rowid"):
			Entities.units[typeid].load(self.session, savegame_db, worldid)

		if self.session.is_game_loaded():
			# let trader command it's ships. we have to do this here cause ships have to be
			# initialised for this, and trader has to exist before ships are loaded.
			self.trader.load_ship_states(savegame_db)

		self.inited = True
		"""TUTORIAL:
		To dig deeper, you should now continue to horizons/world/island.py,
		to check out how buildings and settlements are added to the map"""

	@decorators.make_constants()
	def init_new_world(self):
		"""This should be called if a new map is loaded (not a savegame, a fresh
		map). In other words when it is loaded for the first time.

		NOTE: commands for creating the world objects are executed directly, bypassing the manager
		      this is necessary, because else the commands would be transmitted over the wire
					in network games.

		@return: Returs the coordinates of the players first ship
		"""
		# workaround: the creation of all the objects causes a lot of logging output, we don't need
		#             therefore, reset the levels for now
		loggers_to_silence = { 'world.production' : None }
		for logger_name in loggers_to_silence:
			logger = logging.getLogger(logger_name)
			loggers_to_silence[logger_name] = logger.getEffectiveLevel()
			logger.setLevel( logging.WARN )

		from horizons.command.building import Build
		from horizons.command.unit import CreateUnit
		# add a random number of environmental objects to the gameworld
		if int(self.properties.get('RandomTrees', 1)) == 1:
			Tree = Entities.buildings[BUILDINGS.TREE_CLASS]
			Clay = Entities.buildings[BUILDINGS.CLAY_DEPOSIT_CLASS]
			max_clay_deposits = self.session.random.randint(2, 3)
			for island in self.islands:
				num_clay_deposits = 0
				# TODO: fix this sorted()-call. its slow but orderness of dict-loop isn't guaranteed
				for coords, tile in sorted(island.ground_map.iteritems()):
					# add tree to every nth tile
					if self.session.random.randint(0, 2) == 0 and Tree.check_build(self.session, tile, \
										                                           check_settlement=False):
						building = Build(Tree, coords[0], coords[1], ownerless=True,island=island)(issuer=None)
						building.finish_production_now() # make trees big and fill their inventory
						if self.session.random.randint(0, 40) == 0: # add animal to every nth tree
							CreateUnit(island.worldid, UNITS.WILD_ANIMAL_CLASS, *coords)(issuer=None)
					elif num_clay_deposits < max_clay_deposits and \
						 self.session.random.randint(0, 30) == 0 and \
						 Clay.check_build(self.session, tile, check_settlement=False):
						num_clay_deposits += 1
						cmd = Build(Clay, coords[0], coords[1], ownerless=True, island=island)(issuer=None)

		# reset loggers, see above
		for logger_name, level in loggers_to_silence.iteritems():
			logging.getLogger(logger_name).setLevel(level)

		# add free trader
		self.trader = Trader(self.session, 99999, u"Free Trader", Color())
		ret_coords = None
		for player in self.players:
			# Adding ships for the players
			point = self.get_random_possible_ship_position()
			# Execute command directly, not via manager, because else it would be transmitted over the
			# network to other players. Those however will do the same thing anyways.
			ship = CreateUnit(player.worldid, UNITS.PLAYER_SHIP_CLASS, point.x, point.y)(issuer=self.session.world.player)
			# give ship basic resources
			for res, amount in self.session.db("SELECT resource, amount FROM start_resources"):
				ship.inventory.alter(res, amount)
			if player is self.player:
				ret_coords = (point.x, point.y)

		# add a pirate ship
		# TODO: enable pirate as soon as save/load for it is fixed
		#       currently, it breaks human player selection on load
		#self.pirate = Pirate(self.session, 99998, "Captain Blackbeard", Color())

		# Fire a message for new world creation
		self.session.ingame_gui.message_widget.add(self.max_x/2, self.max_y/2, 'NEW_WORLD')
		assert ret_coords is not None, "Return coords are none. No players loaded?"
		return ret_coords

	@decorators.make_constants()
	def get_random_possible_ship_position(self):
		"""Returns a position in water, that is not at the border of the world"""
		offset = 2
		while True:
			x = self.session.random.randint(self.min_x + offset, self.max_x - offset)
			y = self.session.random.randint(self.min_y + offset, self.max_y - offset)

			if (x, y) in self.ship_map:
				continue # don't place ship where there is already a ship

			# check if there is an island nearby (check only important coords)
			position_possible = True
			for first_sign in (-1, 0, 1):
				for second_sign in (-1, 0, 1):
					point_to_check = Point( x + offset*first_sign, y + offset*second_sign )
					if self.get_island(point_to_check) is not None:
						position_possible = False
						break
			if not position_possible: # propagate break
				continue

			break # all checks successful

		return Point(x, y)

	#----------------------------------------------------------------------
	def get_tiles_in_radius(self, position, radius, shuffle=False):
		"""Returns a all tiles in the radius around the point.
		This is a generator, make sure you use it appropriately.
		@param position: Point instance
		@return List of tiles in radius.
		"""
		assert isinstance(position, Point)
		points = Circle(position, radius)
		if shuffle:
			points = list(points)
			self.session.random.shuffle(points)
		for point in points:
			if self.map_dimensions.contains_without_border(point):
				# don't yield if point is not in map, those points don't exist
				yield self.get_tile(point)

	def setup_player(self, id, name, color, local):
		"""Sets up a new Player instance and adds him to the active world.
		@param local: bool, whether the player is the one sitting on front of this machine."""
		inv = self.session.db.get_player_start_res()
		player = None
		if local:
			player = HumanPlayer(self.session, id, name, color, inventory=inv)
			self.player = player
			self.session.ingame_gui.update_gold()
			self.player.inventory.add_change_listener(self.session.ingame_gui.update_gold)
		else:
			player = Player(self.session, id, name, color, inventory=inv)
		self.players.append(player)

	def get_tile(self, point):
		"""Returns the ground at x, y.
		@param point: coords as Point
		@return: instance of Ground at x, y
		"""
		i = self.get_island(point)
		if i is not None:
			return i.get_tile(point)
		return self.ground_map[(point.x, point.y)]

	def get_settlement(self, point):
		"""Returns settlement on point. Very fast (O(1)).
		Returns None if point isn't on world.
		@param point: instance of Point
		@return: instance of Settlement or None"""
		try:
			return self.get_tile(point).settlement
		except KeyError:
			return None

	@property
	def settlements(self):
		"""Returns all settlements on world"""
		settlements = []
		for i in self.islands:
			settlements.extend(i.settlements)
		return settlements

	def get_building(self, point):
		"""Returns the building at the position x, y.
		@param point: Point instance
		@return: Building class instance if a building is found, else None."""
		i = self.get_island(point)
		return None if i is None else i.get_building(point)

	def get_island(self, point):
		"""Returns the island for that coordinate, if none is found, returns None.
		@param point: instance of Point"""
		for island in self.islands:
			# TODO: check if this optimisation check acctually slows the function down
			# the dict lookup below should be very fast anyways
			if not island.rect.contains(point):
				continue
			if point.to_tuple() in island.ground_map:
				return island
		return None

	def get_islands_in_radius(self, point, radius):
		"""Returns all islands in a certain radius around a point.
		@return set of islands in radius"""
		islands = set()
		for island in self.islands:
			for tile in island.get_surrounding_tiles(point, radius):
				islands.add(island)
				break
		return islands

	@decorators.make_constants()
	def get_branch_offices(self, position=None, radius=None, owner=None):
		"""Returns all branch offices on the map. Optionally only those in range
		around the specified position.
		@param position: Point or Rect instance.
		@param radius: int radius to use.
		@param owner: Player instance, list only branch offices belonging to this player.
		@return: List of branch offices.
		"""
		branchoffices = []
		islands = []
		if radius is not None and position is not None:
			islands = self.get_islands_in_radius(position, radius)
		else:
			islands = self.islands
		for island in islands:
			for settlement in island.settlements:
				for building in settlement.buildings:
					# TODO: find a better way to find out if a building is a bo. possibly keep a list
					#       of bo's per island/settlement
					if isinstance(building, horizons.world.building.storages.BranchOffice):
						if (radius is None or position is None or \
							building.position.distance(position) <= radius) and \
						   (owner is None or building.owner == owner):
							branchoffices.append(building)
		return branchoffices

	@decorators.make_constants()
	def get_ships(self, position=None, radius=None):
		"""Returns all ships on the map. Optionally only those in range
		around the specified position.
		@param position: Point or Rect instance.
		@param radius: int radius to use.
		@return: List of ships.
		"""
		if position is not None and radius is not None:
			circle = Circle(position, radius)
			ships = []
			for ship in self.ships:
				if circle.contains(ship.position):
					ships.append(ship)
			return ships
		else:
			return self.ships

	def save(self, db):
		"""Saves the current game to the specified db.
		@param db: DbReader object of the db the game is saved to."""
		for name, value in self.properties.iteritems():
			db("INSERT INTO map_properties (name, value) VALUES (?, ?)", name, value)
		for island in self.islands:
			island.save(db)
		for player in self.players:
			player.save(db)
		if self.trader is not None:
			self.trader.save(db)
		if self.pirate is not None:
			self.pirate.save(db)
		for ship in self.ships:
			ship.save(db)

	def get_checkup_hash(self):
		dict = {
			'rngvalue': self.session.random.random(),
			'settlements': [],
		}
		for island in self.islands:
			for settlement in island.settlements:
				entry = {
					'owner': str(settlement.owner.worldid),
					'tax_settings': str(settlement.tax_setting),
					'inhabitants': str(settlement.inhabitants),
					'cumulative_running_costs': str(settlement.cumulative_running_costs),
					'cumulative_taxes': str(settlement.cumulative_taxes),
					'inventory' : str(settlement.inventory._storage),
				}
				dict['settlements'].append(entry)
		return dict

	def notify_new_settlement(self):
		"""Called when a new settlement is created"""
		# make sure there's a trader ship for 2 settlements
		if len(self.settlements) > self.trader.get_ship_count() * 2:
			self.trader.create_ship()


def load_building(session, db, typeid, worldid):
	"""Loads a saved building. Don't load buildings yourself in the game code."""
	Entities.buildings[typeid].load(session, db, worldid)
