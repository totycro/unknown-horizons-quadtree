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

class _RadiusRect(object):
	"""Auxilary data structure for local use in this file.
	Mimics a Rectangle with a radius."""
	def __init__(self, center, radius):
		self.center = center
		self.radius = radius
		self.left_radius_border = center.left - radius
		self.right_radius_border = center.right + radius
		self.top_radius_border = center.top - radius
		self.bottom_radius_border = center.bottom + radius

class _Node(object):
	"""Data structure used by TileQuadTree.
	Children are numbered like this:
	0 1
	2 3
	NOTE: in UH, lower on the y-axis means higher values. @see quadrant_directions below.
	"""
	quadrant_directions = {
		 0 : (-1, -1),
		 1 : ( 1, -1),
		 2 : (-1,  1),
		 3 : ( 1,  1)
	  }
	leaf_quadrant_directions = {
	  0 : (-1, -1),
	  1 : ( 0, -1),
	  2 : (-1,  0),
	  3 : ( 0,  0)
	 }
	# TODO:
	# color
	# settlement..
	def __init__(self, x, y, width_of_children):
		# width_of_children == 0 => it's a leaf
		self.x = x
		self.y = y
		assert width_of_children >= 0
		self.width_of_children = width_of_children
		self.children = [None] * 4
		#print 'create child at ', (self.x, self.y), ' with w ', self.width_of_children
		if self.width_of_children == 0:
			self.data = None

	def create_child(self, quadrant):
		"""
		@param quadrant: integer quadrant id
		"""
		if self.width_of_children > 1 :
			direction = self.quadrant_directions[quadrant]
			child_width_of_children = self.width_of_children // 2
			self.children[quadrant] = \
			    _Node(self.x + direction[0] * child_width_of_children,
			          self.y + direction[1] * child_width_of_children,
			          child_width_of_children)
		else:
			# since the coord of this node has no equivalent as real tile,
			# the final coord of the last tile has to be corrected here
			direction = self.leaf_quadrant_directions[quadrant]
			self.children[quadrant] = \
			    _Node(self.x + direction[0], self.y + direction[1], 0)

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

	def iterdata(self):
		"""Generator, yields the data of all children of this node"""
		if self.width_of_children == 0: # leaf
			yield self.data
		else:
			for child in self.children:
				if child is not None:
					for data in child.iterdata():
						yield data


	def get_radius_tiles(self, radius_rect):
		if self.width_of_children == 0:
			#print 'checking ', (self.x, self.y)
			if radius_rect.center.distance_to_tuple((self.x, self.y)) <= radius_rect.radius:
				#print 'found ', (self.x, self.y)
				yield self.data
		else:
			left = right = False
			if radius_rect.left_radius_border < self.x: # search left side for sure
				if radius_rect.right_radius_border < self.x:
					left = True
				else:
					left = right = True
			else:
				right = True

			bottom = top = False
			if radius_rect.top_radius_border < self.y: # search top for sure
				if radius_rect.bottom_radius_border < self.y:
					top = True
				else:
					bottom = top = True
			else:
				bottom = True

			if left:
				if top:
					if self.children[0] is not None:
						for tile in self.children[0].get_radius_tiles(radius_rect):
							yield tile
				if bottom:
					if self.children[2] is not None:
						for tile in self.children[2].get_radius_tiles(radius_rect):
							yield tile
			if right:
				if top:
					if self.children[1] is not None:
						for tile in self.children[1].get_radius_tiles(radius_rect):
							yield tile
				if bottom:
					if self.children[3] is not None:
						for tile in self.children[3].get_radius_tiles(radius_rect):
							yield tile

	def visit_radius_tiles(self, radius_rect, callback):
		if self.width_of_children == 0:
			#print 'checking ', (self.x, self.y)

			r = radius_rect.center
			if ((max(r.left - self.x, 0, self.x - r.right) ** 2) + (max(r.top - self.y, 0, self.y - r.bottom) ** 2)) ** 0.5 <= radius_rect.radius:
				#if radius_rect.center.distance_to_tuple((self.x, self.y)) <= radius_rect.radius:
				#print 'found ', (self.x, self.y)
				callback(self.data)
		else:
			left = right = False
			if radius_rect.left_radius_border < self.x: # search left side for sure
				if radius_rect.right_radius_border < self.x:
					left = True
				else:
					left = right = True
			else:
				right = True

			bottom = top = False
			if radius_rect.top_radius_border < self.y: # search top for sure
				if radius_rect.bottom_radius_border < self.y:
					top = True
				else:
					bottom = top = True
			else:
				bottom = True

			if left:
				if top:
					if self.children[0] is not None:
						self.children[0].visit_radius_tiles(radius_rect, callback)
				if bottom:
					if self.children[2] is not None:
						self.children[2].visit_radius_tiles(radius_rect, callback)
			if right:
				if top:
					if self.children[1] is not None:
						self.children[1].visit_radius_tiles(radius_rect, callback)
				if bottom:
					if self.children[3] is not None:
						self.children[3].visit_radius_tiles(radius_rect, callback)


	@property
	def empty(self):
		return self.children == [None] * 4

	def __str__(self):
		return "TileQuadTreeNode(x=%s, y=%s, child_w=%s)" % (self.x, self.y, self.width_of_children)


class TileQuadTree(object):
	class OverwriteError(Exception):
		pass

	def __init__(self, island_dimensions):
		"""
		@param island_dimensions: a Rect specifiying the boundaries of the island
		"""
		self._island_dimensions = island_dimensions.copy()
		half_max_length = max(self._island_dimensions.width, self._island_dimensions.height) // 2
		width_of_children = self.get_next_power_of_two(half_max_length)

		coords = self._island_dimensions.center().x, self._island_dimensions.center().y
		self.root = _Node(coords[0], coords[1], width_of_children)

		self._len = 0

	def add_tile(self, tile):
		assert self._island_dimensions.contains_tuple((tile.x, tile.y))

		cur = self.root
		#print ' add tile ', tile
		while True:
			#print 'iter at ' , cur
			# check if we're there
			if cur.width_of_children == 0: # last level
				#print 'addin at ', cur
				assert cur.x == tile.x and cur.y == tile.y
				if cur.data is not None:
					raise self.OverwriteError()
				cur.data = tile
				self._len += 1
				break

			# find quadrant, where child is located
			quadrant = cur.get_child_quadrant(tile.x, tile.y)
			#print 'going to q ', quadrant

			# create, if necessary
			if cur.children[quadrant] is None:
				cur.create_child(quadrant)

			# iterate
			cur = cur.children[quadrant]

	def get_tile(self, x, y):
		"""Returns tile referenced by coordinate tup.
		@param x, y: coords
		@return Tile object or None"""
		assert self._island_dimensions.contains_tuple((x, y))
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

	def get_radius_tiles(self, center, radius):
		"""Yields tiles in the radius of center.
		@param center: Rect
		@param radius: int
		"""
		for tile in self.root.get_radius_tiles(_RadiusRect(center, radius)):
			yield tile

	def visit_radius_tiles(self, center, radius, callback):
		self.root.visit_radius_tiles(_RadiusRect(center, radius), callback)

	def __iter__(self):
		"""Generator, yields every tile in the tree"""
		for data in self.root.iterdata():
			yield data

	def __len__(self):
		"""Returns number of added tiles"""
		return self._len

	@staticmethod
	def get_next_power_of_two(number):
		"""Returns minimal n for which (2^n >= number) holds"""
		n = 1
		while n < number:
			n *= 2
		return n

