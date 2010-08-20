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

class _Node(object):
	"""Primitive data structure used by TileQuadTree.
	Children are numbered like this:
	0 1
	2 3
	NOTE: in UH, lower on the y-axis means higher values. @see quadrant_directions below.
	"""
	quadrant_directions = {
		  0 : (-1, -1),
		  1 : (-1,  1),
		  2 : ( 1, -1),
		  3 : ( 1,  1)
	  }
	# TODO:
	# color
	# settlement..
	def __init__(self, x, y, width_of_children):
		self.x = x
		self.y = y
		assert width_of_children >= 0
		self.width_of_children = width_of_children
		self.children = [None] * 4

	def create_child(self, quadrant):
		"""
		@param quadrant: integer quadrant id
		"""
		direction = self.quadrant_directions[quadrant]
		child_width_of_children = self.width_of_children // 2
		self.children[quadrant] = \
		    _Node(self.x + direction[0] * child_width_of_children,
		          self.y + direction[1] * child_width_of_children,
		          child_width_of_children)

	def get_child_quadrant(self, x, y):
		"""Returns id of quadrant, where an object at x, y can be found"""
		if x < self.x:
			if y < self.y:
				return 0
			else:
				return 2
		else:
			if y < self.y:
				return 1
			else:
				return 3

	def get_child_containing(self, x, y):
		return self.children[ self.get_child_quadrant(x, y) ]

	@property
	def empty(self):
		return self.children == [None] * 4

class TileQuadTree(object):
	def __init__(self, island_dimensions):
		"""
		@param island_dimensions: a Rect specifiying the boundaries of the island
		"""
		self._island_dimensions = island_dimensions.copy()
		half_max_length = max(self._island_dimensions.width, self._island_dimensions.height) // 2
		width_of_children = self.get_next_power_of_two(half_max_length)

		coords = self._island_dimensions.center().x, self._island_dimensions.center().y
		self.root = _Node(coords[0], coords[1], width_of_children)

	def add_tile(self, tile):
		assert self._island_dimensions.contains_tuple((tile.x, tile.y))

		cur = self.root
		while True:
			# find quadrant, where child is located
			quadrant = cur.get_child_quadrant(tile.x, tile.y)

			# create, if necessary
			if cur.children[quadrant] is None:
				cur.create_child(quadrant)

			# check if we're there
			if cur.width_of_children == 1: # last level
				cur.children[quadrant].data = tile
				break

			# iterate
			cur = cur.children[quadrant]


	def get_tile(self, x, y):
		"""Returns tile referenced by coordinate tup.
		@param x, y: coords
		@return Tile object or None"""
		cur = self.root
		while True:
			#print 'get ', (x, y), ' starting at width', cur.width_of_children, ' at ', (cur.x, cur.y)
			#if (x, y) == (2, 3): import pdb ; pdb.set_trace()
			if cur.width_of_children == 0:
				#print 'found'
				return cur.data
			cur = cur.get_child_containing(x, y)
			if cur is None:
				#print 'none found'
				return None

	@staticmethod
	def get_next_power_of_two(number):
		"""Returns minimal n for which (2^n >= number) holds"""
		n = 1
		while n < number:
			n *= 2
		return n

