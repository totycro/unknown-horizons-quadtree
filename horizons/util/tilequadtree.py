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

from horizons.util.python import decorators

class _RadiusRect(object):
	"""Auxilary data structure for local use in this file.
	Mimics a Rectangle with a radius."""
	def __init__(self, center, radius):
		self.center = center
		self.radius = radius
		# eager evaluation, pulled out of loops
		self.radius_squared = radius ** 2
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

	def __init__(self, parent, x, y, width_of_children):
		# width_of_children == 0 => it's a leaf
		self.parent = parent
		self.x = x
		self.y = y
		assert width_of_children >= 0
		self.width_of_children = width_of_children
		self.children = [None] * 4
		#print 'create child at ', (self.x, self.y), ' with w ', self.width_of_children
		if self.width_of_children == 0:
			self.data = None
		elif self.width_of_children <= 2**3:
			# keep list of data that is stored in all children for smaller nodes
			self.child_data = []

		# list of non-null children
		self.existing_children = []

		# eager evaluation
		self.left = self.x - width_of_children
		self.right = self.x + width_of_children
		self.top = self.y - width_of_children
		self.bottom = self.y + width_of_children

		# special code for last non-leaf level. see @__visit_radius_tiles_last_level
		if self.width_of_children == 1:
			self.visit_radius_tiles = self.__visit_radius_tiles_last_level

	def create_child(self, quadrant):
		"""
		@param quadrant: integer quadrant id
		"""
		if self.width_of_children > 1 :
			direction = self.quadrant_directions[quadrant]
			child_width_of_children = self.width_of_children // 2
			self.children[quadrant] = \
			    _Node(self,
			          self.x + direction[0] * child_width_of_children,
			          self.y + direction[1] * child_width_of_children,
			          child_width_of_children)
		else:
			# since the coord of this node has no equivalent as real tile,
			# the final coord of the last tile has to be corrected here
			direction = self.leaf_quadrant_directions[quadrant]
			self.children[quadrant] = \
			    _Node(self, \
			          self.x + direction[0], \
			          self.y + direction[1], \
			          0)
		self.existing_children.append( self.children[quadrant] )

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

	def visit_tiles(self, callback):
		"""Calls callback on all tiles referenced by this node recursively"""
		if self.width_of_children == 0: # leaf
			callback(self.data)
		else:
			try:
				for data in self.child_data:
					callback(data)
			except AttributeError:  # visit_tiles is usually only used for smaller nodes, so this is unlikely
				for child in self.existing_children:
					child.visit_tiles(callback)

	def get_radius_tiles(self, radius_rect):
		"""TODO: unsused and outdate.
		Consider using visit_radius_tiles if you don't need to have a list,
		since passing the results through the whole tree is expensive"""
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


	def __visit_radius_tiles_last_level(self, radius_rect, callback):
		"""visit_radius_tile code for nodes directly above leaf-level.
		Since the level of a node is constant, the visit_radius_tiles-code
		of those nodes get's replaced by this in the constructor.
		A more intuitive, but slightly less efficient version would be to query
		the level, and then decide which code to run at runtime:
		if self.width_of_children == 1:
		  last_level()
		else:
		  normal_code()
		The purpose of this optimisation is to get rid of the if.
		"""
		# finish checking here, not at acctual leaf level,
		# because checking if full child is contained in the radius
		# doesn't make sense here anymore
		center = radius_rect.center
		for child in self.existing_children:
			# this if is an inline version of:
			#if radius_rect.center.distance_to_tuple((child.x, child.y)) <= radius_rect.radius
			if (max(center.left - child.x, 0, child.x - center.right) ** 2) + \
			    (max(center. top - child.y, 0, child.y - center.bottom) ** 2) <= \
			    radius_rect.radius_squared:
				#print 'found ', (self.x, self.y)
				callback(child.data)

	def visit_radius_tiles(self, radius_rect, callback):
		# we need 2 comparisions for x- and y-axis each, since
		# we are comparing 2 lines (rect boundaries w.r.t. x- and y-axis) to the axis

		if radius_rect.left_radius_border < self.x: # search left side for sure
			if radius_rect.right_radius_border < self.x:
				quadrants_to_search = set((0,2))
			else:
				quadrants_to_search = set((0,1,2,3))
		else:
			quadrants_to_search = set((1,3))

		if radius_rect.top_radius_border < self.y: # search top for sure
			if radius_rect.bottom_radius_border < self.y:
				quadrants_to_search.discard(2)
				quadrants_to_search.discard(3)
		else:
			quadrants_to_search.discard(0)
			quadrants_to_search.discard(1)

		for quadrant in quadrants_to_search:
			child = self.children[quadrant]
			if child is not None:
				full_child_included = False
				# only check if full child is included if children are smaller than the radius
				if self.width_of_children < radius_rect.radius:
					# search corner of child farthest away from the radius_rect
					center = radius_rect.center
					center_point = ((center.right + center.left) // 2, \
				                  (center.bottom + center.top) // 2)

					diff_left = abs(child.left - center_point[0])
					diff_right = abs(child.right - center_point[0])
					farthest_x = child.left if diff_left >= diff_right else child.right

					diff_top = abs(child.top - center_point[1])
					diff_bottom = abs(child.bottom - center_point[1])
					farthest_y = child.top if diff_top >= diff_bottom else child.bottom

					# this if is an inline version of:
					#if radius_rect.center.distance_to_tuple((farthest_x, farthest_y)) < radius_rect.radius:
					if (max(center.left - farthest_x, 0, farthest_x - center.right) ** 2) + \
				     (max(center.top - farthest_y, 0, farthest_y - center.bottom) ** 2) <= \
				     radius_rect.radius_squared:
						full_child_included = True

				if full_child_included:
					# full rect is included
					child.visit_tiles(callback)
				else:
					# go on checking on lower level
					child.visit_radius_tiles(radius_rect, callback)


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
		# we need to calculate the size of our children here.
		# the root will be located at the center, leaving a certain maximal distance
		# to the coordinate farthest away. The minimal power of two, which is >= to this
		# distance, will be the width_of_children of the root node
		half_max_length = max(self._island_dimensions.width, self._island_dimensions.height) // 2
		width_of_children = self.get_next_power_of_two(half_max_length)
		coords = (self._island_dimensions.center().x, self._island_dimensions.center().y)
		self.root = _Node(None, coords[0], coords[1], width_of_children)

		self._len = 0 # number of children

	def add_tile(self, tile):
		"""Adds a tile to the tree. A coordinate may only be occupied by one tile."""
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

				# add data to data list of parents
				cur = cur.parent
				while hasattr(cur, "child_data"):
					cur.child_data.append(tile)
					cur = cur.parent
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
		"""Returns all tiles in radius. Use this if you need to have a list of Tiles
		@param center: Rect
		@param radius: int
		@return: list of Tile objects
		"""
		l = []
		self.root.visit_radius_tiles(_RadiusRect(center, radius), l.append)
		return l

	def visit_radius_tiles(self, center, radius, callback):
		"""Calls a function on each tile within the radius. Has less overhead than get_radius_tiles."""
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

decorators.bind_all(TileQuadTree)
decorators.bind_all(_Node)
decorators.bind_all(_RadiusRect)

