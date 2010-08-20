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
import math

from horizons.util import Point, Rect, decorators
from horizons.world.pathfinding.pather import StaticPather
from horizons.constants import BUILDINGS
from horizons.entities import Entities

class _BuildPosition(object):
	"""A possible build position in form of a data structure.
	Don't use directly outside of this file"""
	def __init__(self, position, rotation, tearset, buildable, action='idle'):
		"""
		@param position: Rect, building position and size
		@param rotation: int rotation of building
		@param tearset: list of worldids of buildings to tear for this building to build
		@param buildable: whether building is acctually buildable there
		@param action: action (animation of building)
		"""
		self.position = position
		self.rotation = rotation
		self.tearset = tearset
		self.buildable = buildable
		self.action = action

	def __nonzero__(self):
		"""Returns buildable value. This enables code such as "if cls.check_build()"""
		return self.buildable

	def __eq__(self, other):
		if not isinstance(other, _BuildPosition):
			return False
		return self.position == other.position and \
		       self.rotation == other.rotation and \
		       self.action == other.action and \
		       self.tearset == other.tearset

	def __ne__(self, other):
		return not self.__eq__(other)

class _NotBuildableError(Exception):
	"""Internal exception."""

class Buildable(object):
	"""Interface for every kind of buildable objects.
	Contains methods to determine whether a building can be placed on a coordinate, regarding
	island, settlement, ground requirements etc. Does not care about building costs."""

	# INTERFACE

	@classmethod
	def check_build(cls, session, point, rotation=45, check_settlement=True, ship=None, issuer=None):
		"""Check if a building is buildable here.
		All tiles, that the building occupies are checked.
		@param point: Point instance, coords
		@param rotation: prefered rotation of building
		@param check_settlement: whether to check for a settlement (for settlementless buildings)
		@param ship: ship instance if building from ship
		@return instance of _BuildPosition"""
		# for non-quadratic buildings, we have to switch width and height depending on the rotation
		if rotation == 45 or rotation == 225:
			position = Rect.init_from_topleft_and_size(point.x, point.y, cls.size[0]-1, cls.size[1]-1)
		else:
			position = Rect.init_from_topleft_and_size(point.x, point.y, cls.size[1]-1, cls.size[0]-1)

		buildable = True
		tearset = []
		try:
			cls._check_island(session, position)
			# TODO: if the rotation changes here for non-quadratic buildings, wrong results will be returned
			rotation = cls._check_rotation(session, position, rotation)
			tearset = cls._check_buildings(session, position)
			if check_settlement:
				cls._check_settlement(session, position, ship=ship, issuer=issuer)
		except _NotBuildableError:
			buildable = False
		return _BuildPosition(position, rotation, tearset, buildable)

	@classmethod
	def check_build_line(cls, session, point1, point2, rotation=45, ship=None):
		"""Checks out a line on the map for build possibilities.
		The line usually is a draw of the mouse.
		@param point1, point2: Point instance, start and end of the line
		@param rotation: prefered rotation
		@param ship: ship instance if building from ship
		@return list of _BuildPositions
		"""
		raise NotImplementedError

	@classmethod
	def is_tile_buildable(cls, session, tile, ship, island=None, check_settlement=True):
		"""Checks a tile for buildability.
		@param tile: Ground object
		@param ship: Ship instance if building from ship
		@param island: Island instance, if already known. If None, it will be calculated
		@param check_settlement: bool, whether to check for settlement
		@return bool, True for "is buildable" """
		position = Point(tile.x, tile.y)
		try:
			cls._check_island(session, position, island)
			if check_settlement:
				cls._check_settlement(session, position, ship=ship)
			cls._check_buildings(session, position)
		except _NotBuildableError:
			return False
		return True

	# PRIVATE PARTS

	@classmethod
	def _check_island(cls, session, position, island=None):
		"""Check if there is an island and enough tiles.
		@throws _NotBuildableError if building can't be built.
		@param position: coord Point to build at
		@param island: Island instance if known before"""
		if island is None:
			island = session.world.get_island(position.center())
			if island is None:
				raise _NotBuildableError()
		for tup in position.tuple_iter():
			# can't use get_tile_tuples since it discards None's
			tile = island.get_tile_tuple(tup)
			if tile is None or 'constructible' not in tile.classes:
				raise _NotBuildableError()

	@classmethod
	def _check_rotation(cls, session, position, rotation):
		"""Returns a possible rotation for this building.
		@param position: Rect or Point instance, position and size
		@param rotation: The prefered rotation
		@return: integer, an available rotation in degrees"""
		return rotation

	@classmethod
	def _check_settlement(cls, session, position, ship=None, issuer=None):
		"""Check if there is a settlement and if it belongs to the human player"""
		settlement = session.world.get_settlement(position.center())
		player = issuer if issuer is not None else session.world.player
		if settlement is None or player != settlement.owner:
			raise _NotBuildableError()

	@classmethod
	def _check_buildings(cls, session, position, island=None):
		"""Check if there are buildings blocking the build.
		@return Iterable of worldids of buildings that need to be teared in order to build here"""
		if island is None:
			island = session.world.get_island(position.center())
			# _check_island already confirmed that there must be an island here, so no check for None again
		tearset = set()
		for tile in island.get_tiles_tuple( position.tuple_iter() ):
			obj = tile.object
			if obj is not None: # tile contains an object
				if obj.buildable_upon:
					if obj.__class__ is cls:
						# don't tear trees to build trees over them
						raise _NotBuildableError()
					# tear it so we can build over it
					tearset.add(obj.worldid)
				else:
					# building is blocking the build
					raise _NotBuildableError()
		if hasattr(session.manager, 'get_builds_in_construction'):
			builds_in_constructin = session.manager.get_builds_in_construction()
			for build in builds_in_constructin:
				(sizex, sizey) = Entities.buildings[build.building_class].size
				for (neededx,neededy) in position.tuple_iter():
					if neededx in range(build.x, build.x+sizex) and neededy in range(build.y, build.y+sizey):
						raise _NotBuildableError()
		return tearset


class BuildableSingle(Buildable):
	"""Buildings one can build single. """
	@classmethod
	def check_build_line(cls, session, point1, point2, rotation=45, ship=None):
		# only build 1 building at endpoint
		# correct placement for large buildings (mouse should be at center of building)
		point2 = point2.copy() # only change copy
		point2.x -= (cls.size[0] - 1) / 2
		point2.y -= (cls.size[1] - 1) / 2
		return [ cls.check_build(session, point2, rotation=rotation, ship=ship) ]


class BuildableRect(Buildable):
	"""Buildings one can build as a Rectangle, such as Trees"""
	@classmethod
	def check_build_line(cls, session, point1, point2, rotation=45, ship=None):
		possible_builds = []
		area = Rect.init_from_corners(point1, point2)
		# correct placement for large buildings (mouse should be at center of building)
		area.left -= (cls.size[0] - 1) / 2
		area.right -= (cls.size[0] - 1) / 2
		area.top -= (cls.size[1] - 1) / 2
		area.bottom -= (cls.size[1] - 1) / 2

		for x in xrange(area.left, area.right+1, cls.size[0]):
			for y in xrange(area.top, area.bottom+1, cls.size[1]):
				possible_builds.append( \
				  cls.check_build(session, Point(x, y), rotation=rotation, ship=ship) \
				)
		return possible_builds


class BuildableLine(Buildable):
	"""Buildings one can build in a line, such as paths"""
	@classmethod
	def check_build_line(cls, session, point1, point2, rotation=45, ship=None):

		# Pathfinding currently only supports buildingsize 1x1, so don't use it in this case
		if cls.size != (1, 1):
			return [ cls.check_build(session, point2, rotation=rotation, ship=ship) ]

		# use pathfinding to get a path, then try to build along it
		island = session.world.get_island(point1)
		if island is None:
			return []

		path = StaticPather.get_direct_path(island, point1, point2)
		if path is None: # can't find a path between these points
			return [] # TODO: check alternative strategy

		possible_builds = []

		for i in path:
			action = ''
			for action_char, offset in \
			    sorted(BUILDINGS.ACTION.action_offset_dict.iteritems()): # order is important here
				if (offset[0]+i[0], offset[1]+i[1]) in path:
					action += action_char
			if action == '':
				action = 'ac' # default

			build = cls.check_build(session, Point(*i))
			build.action = action
			possible_builds.append(build)

		return possible_builds


class BuildableSingleOnCoast(BuildableSingle):
	"""Buildings one can only build on coast, such as BoatBuilder, Fisher"""
	@classmethod
	def _check_island(cls, session, position, island=None):
		# ground has to be either coastline or constructible, > 1 tile must be coastline
		# can't use super, since it checks all tiles for constructible

		if island is None:
			island = session.world.get_island(position.center())
			if island is None:
				raise _NotBuildableError()

		coastline_found = False
		for tup in position.tuple_iter():
			# can't use get_tile_tuples since it discards None's
			tile = island.get_tile_tuple(tup)
			if tile is None:
				raise _NotBuildableError()
			if 'coastline' in tile.classes:
				coastline_found = True
			elif 'constructible' not in tile.classes: # neither coastline, nor constructible
				raise _NotBuildableError()
		if not coastline_found:
			raise _NotBuildableError()

	@classmethod
	def _check_rotation(cls, session, position, rotation):
		"""Rotate so that the building faces the seaside"""
		# array of coords (points are True if is coastline)
		coastline = {}
		x, y = position.origin.to_tuple()
		for point in position:
			if session.world.map_dimensions.contains_without_border(point):
				is_coastline = ('coastline' in session.world.get_tile(point).classes)
			else:
				is_coastline = False
			coastline[point.x-x, point.y-y] = is_coastline

		""" coastline looks something like this:
		111
		000
		000
		we have to rotate to the direction with most 1s

		Rotations:
		   45
		135   315
		   225
		"""
		coast_line_points_per_side = {
		  45: sum( coastline[(x,0)] for x in xrange(0, cls.size[0]) ),
		  135: sum( coastline[(0,y)] for y in xrange(0, cls.size[1]) ),
		  225: sum( coastline[(x, cls.size[1]-1 )] for x in xrange(0, cls.size[0]) ),
		  315: sum( coastline[(cls.size[0]-1,y)] for y in xrange(0, cls.size[1]) ),
		}

		# return rotation with biggest value
		maximum = -1
		rotation = -1
		for rot, val in coast_line_points_per_side.iteritems():
			if val > maximum:
				maximum = val
				rotation = rot
		return rotation


class BuildableSingleFromShip(BuildableSingleOnCoast):
	"""Buildings that can be build from a ship. Currently only Branch Office."""
	@classmethod
	def _check_settlement(cls, session, position, ship, issuer=None):
		# building from ship doesn't require settlements
		# but a ship nearby:
		if ship.position.distance(position) > BUILDINGS.BUILD.MAX_BUILDING_SHIP_DISTANCE:
			raise _NotBuildableError()

		# and the island mustn't be owned by anyone else
		settlement = session.world.get_settlement(position.center())
		if settlement is not None:
			raise _NotBuildableError()

		# and player mustn't have a settlement here already
		island = session.world.get_island(position.center())
		for s in island.settlements:
			if s.owner == ship.owner:
				raise _NotBuildableError()

class BuildableSingleOnDeposit(BuildableSingle):
	"""For mines; those buildings are only buildable upon other buildings (clay pit on clay deposit, e.g.)
	For now, mines can only be built on a single type of deposit.
	This is specified in game.sqlite in the table "mine", and saved in cls.buildable_on_deposit in
	the buildingclass.
	"""
	@classmethod
	def _check_buildings(cls, session, position, island=None):
		"""Check if there are buildings blocking the build"""
		if island is None:
			island = session.world.get_island(position.center())
		deposit = None
		for tile in island.get_tiles_tuple( position.tuple_iter() ):
			if tile.object is None or \
			   tile.object.id != cls.buildable_on_deposit_type or \
			   (deposit is not None and tile.object != deposit): # only build on 1 deposit
				raise _NotBuildableError()
			deposit = tile.object
		return set([deposit.worldid])


# apply make_constant to classes
decorators.bind_all(Buildable)
decorators.bind_all(BuildableSingle)
decorators.bind_all(BuildableRect)
decorators.bind_all(BuildableSingleFromShip)
decorators.bind_all(BuildableSingleOnCoast)
decorators.bind_all(BuildableSingleOnDeposit)
