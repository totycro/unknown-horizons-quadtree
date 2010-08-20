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

"""
Put all code here that is not directly related to the game,
but rather a generic enhancement of the programming language.
"""

import decorators
from callback import Callback
from stablelist import stablelist
from weaklist import WeakList
from weakmethod import WeakMethod
from weakmethodlist import WeakMethodList
from singleton import Singleton, ManualConstructionSingleton


class Const(object):
	"""An immutable type. Think C++-like const"""
	def __setattr__(self, name, value):
		"""Disallow changing an already set attribute, as an asymptote to const behaviour,
		which is not supported by python"""
		if name in self.__dict__:
			raise Exception, "Can't change a ConstRect"
		super(Const, self).__setattr__(name, value)
