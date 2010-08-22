#!/usr/bin/env python

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



import unittest
import copy

from horizons.util import Point, Rect, Circle
from horizons.util.tilequadtree import TileQuadTree

class _FakeTile(object):
	def __init__(self, x, y):
		self.x = x
		self.y = y
	def __str__(self):
		return 'FakeTile(x=%s,y=%s)' % (self.x, self.y)

class TestTileQuadTree(unittest.TestCase):
	default_fill_coords = [ (2, 2), (2, 3), (2, 4), (3, 2), (3, 3) ]
	default_rect = Rect.init_from_topleft_and_size(0,0, 5, 5)

	def _createTree(self):
		return TileQuadTree(self.default_rect)

	def _fillTree(self, tree):
		for coords in self.default_fill_coords:
			tree.add_tile( _FakeTile(*coords) )

	def testInsert(self):
		tiles = {}
		tiles[(2,2)] = _FakeTile(2, 2)
		tiles[(2,3)] = _FakeTile(2, 3)
		tiles[(3,2)] = _FakeTile(3, 2)
		tiles[(3,3)] = _FakeTile(3, 3)
		tiles[(0,0)] = _FakeTile(0, 0)
		tree = TileQuadTree(Rect.init_from_topleft_and_size(0,0, 5, 5))

		for coord, tile in tiles.iteritems():
			self.assertEqual( tree.get_tile(*coord), None )
			tree.add_tile(tile)
			self.assertEqual( tree.get_tile(*coord), tile )

	def testInsertFull(self):
		tiles = {}
		for coord in self.default_rect.tuple_iter():
			tiles[coord] = _FakeTile(coord[0], coord[1])
			tree = TileQuadTree(Rect.init_from_topleft_and_size(0,0, 5, 5))

		for coord, tile in tiles.iteritems():
			self.assertEqual( tree.get_tile(*coord), None )
			tree.add_tile(tile)
			self.assertEqual( tree.get_tile(*coord), tile )

	def testLen(self):
		tree = self._createTree()
		self._fillTree(tree)
		self.assertEqual(len(tree), len(self.default_fill_coords))

	def testIter(self):
		tree = self._createTree()
		self._fillTree(tree)
		coords = copy.deepcopy(self.default_fill_coords)
		for tile in tree:
			coords.remove( (tile.x, tile.y) )
		self.assertEqual(len(coords), 0)

	def testRadiusCoords(self):
		tree = self._createTree()
		for coord in self.default_rect.tuple_iter():
			tree.add_tile( _FakeTile(coord[0], coord[1] ) )
		rect = Rect.init_from_topleft_and_size(1, 1, 0, 0)

		for i in tree.get_radius_tiles(rect, 1):
			print i

	def testRadiusCoordsSpeed(self):
		tree = TileQuadTree(Rect.init_from_topleft_and_size(0, 0, 300, 300) )

		print 'testing speed (may take a while)'
		for x in xrange(0,300):
			print x
			for y in xrange(0,300):
				tree.add_tile(_FakeTile(x, y) )

		center = Rect.init_from_topleft_and_size(144,145,10,10)

		a = []
		a_app = a.append
		import cProfile as profile
		import tempfile
		outfilename = tempfile.mkstemp(text = True)[1]
		#print 'profile to ', outfilename
		#profile.runctx( "for i in tree.get_radius_tiles(center, 100): a_app(i)" , globals(), locals(), outfilename)
		b = []
		b_app = b.append
		def cb(x): pass
		outfilename = tempfile.mkstemp(text = True)[1]
		print 'profile to ', outfilename
		profile.runctx( "tree.visit_radius_tiles(center, 100, cb)" , globals(), locals(), outfilename)

		print len(a)
		print len(b)