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

from horizons.util import Point, Rect, Circle
from horizons.util.tilequadtree import TileQuadTree

class _FakeTile(object):
	def __init__(self, x, y):
		self.x = x
		self.y = y

class TestTileQuadTree(unittest.TestCase):

	def testInsert(self):
		tiles = {}
		tiles[(2,2)] = _FakeTile(2, 2)
		tiles[(2,3)] = _FakeTile(2, 3)
		tiles[(2,4)] = _FakeTile(2, 4)
		tiles[(3,3)] = _FakeTile(3, 3)
		tree = TileQuadTree(Rect.init_from_topleft_and_size(0,0, 5, 5))

		for coord, tile in tiles.iteritems():
			self.assertEqual( tree.get_tile(*coord), None )
			tree.add_tile(tile)
			self.assertEqual( tree.get_tile(*coord), tile )

