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
		area = Rect.init_from_topleft_and_size(0, 0, 100, 100)
		tree = TileQuadTree(area)
		tree2 = TileQuadTree(area)
		tree2_check = lambda coord : coord[0] % 2 == 0 and coord[0] % 3 == 0 and coord[1] % 5 == 0
		for coord in area.tuple_iter():
			tree.add_tile( _FakeTile(coord[0], coord[1] ) )
			if tree2_check(coord):
				tree2.add_tile( _FakeTile(coord[0], coord[1]) )

		def get_diff_msg(l1, l2):
			msg = 'unequal at radius '+ str(radius)
			msg += '\nl1: ' + str(l1)
			msg += '\nl2: ' + str(l2)
			diff1 = [ i for i in l1 if i not in l2 ]
			diff2 = [ i for i in l2 if i not in l1 ]
			msg += '\ndiff1: ' + str(diff1)
			msg += '\ndiff2: ' + str(diff2)
			return msg
		def do_test(center, radius):
			l1 = []
			for tile in tree.get_radius_tiles(center, radius):
				l1.append((tile.x, tile.y))
			l2 = []
			tree.visit_radius_tiles(center, radius, lambda x : l2.append((x.x, x.y)))
			l1.sort()
			l2.sort()
			l3 = sorted(center.get_radius_coordinates(radius, include_self=True))
			self.assertEqual(l1, l3, get_diff_msg(l1, l3))
			self.assertEqual(l1, l2, get_diff_msg(l1, l2))
		def do_test2(center, radius):
			l1 = []
			for tile in tree2.get_radius_tiles(center, radius):
				l1.append((tile.x, tile.y))
			l2 = []
			tree2.visit_radius_tiles(center, radius, lambda x : l2.append((x.x, x.y)))
			l1.sort()
			l2.sort()
			l3 = [ x for x in sorted(center.get_radius_coordinates(radius, include_self=True)) if tree2_check(x)]
			self.assertEqual(l1, l3, get_diff_msg(l1, l3))
			self.assertEqual(l1, l2, get_diff_msg(l1, l2))


		center = Rect.init_from_topleft_and_size(20, 20, 0, 0)
		center2 = Rect.init_from_topleft_and_size(20, 20, 3, 3)
		center3 = Rect.init_from_topleft_and_size(20, 20, 5, 2)

		print 'checking for correctness'
		for radius in xrange(0,15):
			do_test(center, radius)
			do_test(center2, radius)
			do_test(center3, radius)
			do_test2(center, radius)
			do_test2(center2, radius)
			do_test2(center3, radius)



	def testRadiusCoordsSpeed(self):
		tree = TileQuadTree(Rect.init_from_topleft_and_size(0, 0, 300, 300) )

		print 'testing speed (may take a while)'
		for x in xrange(0,300):
			if x % 20 == 0: print int((float(x)/300)*100)
			for y in xrange(0,300):
				tree.add_tile(_FakeTile(x, y) )

		center = Rect.init_from_topleft_and_size(144,145,10,10)

		import cProfile as profile
		import tempfile
		#outfilename = tempfile.mkstemp(text = True)[1]
		#print 'profile to ', outfilename
		#profile.runctx( "for i in tree.get_radius_tiles(center, 100): a_app(i)" , globals(), locals(), outfilename)
		def cb(x): pass
		outfilename = tempfile.mkstemp(text = True)[1]
		print 'profile to ', outfilename
		profile.runctx( "tree.visit_radius_tiles(center, 120, cb)" , globals(), locals(), outfilename)

