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

from fife import fife
import horizons.main

import time
import sys
import math
import os.path
import yaml

from horizons.util.living import LivingObject
from horizons.util import WorldObject

class IngameKeyListener(fife.IKeyListener, LivingObject):
	"""KeyListener Class to process key presses ingame"""

	def __init__(self, session):
		super(IngameKeyListener, self).__init__()
		self.session = session
		horizons.main.fife.eventmanager.addKeyListenerFront(self)
		self.keysPressed = []
		# Used to sum up the keyboard autoscrolling
		self.key_scroll = [0, 0]

	def end(self):
		horizons.main.fife.eventmanager.removeKeyListener(self)
		self.session = None
		super(IngameKeyListener, self).end()

	def keyPressed(self, evt):
		keyval = evt.getKey().getValue()
		keystr = evt.getKey().getAsString().lower()

		was = keyval in self.keysPressed
		if not was:
			self.keysPressed.append(keyval)
		if keyval == fife.Key.LEFT:
			if not was: self.key_scroll[0] -= 25
		if keyval == fife.Key.RIGHT:
			if not was: self.key_scroll[0] += 25
		if keyval == fife.Key.UP:
			if not was: self.key_scroll[1] -= 25
		if keyval == fife.Key.DOWN:
			if not was: self.key_scroll[1] += 25

		# We scrolled, do autoscroll
		if self.key_scroll[0] != 0 or self.key_scroll != 0:
			self.session.view.autoscroll_keys(self.key_scroll[0], self.key_scroll[1])

		if keyval == fife.Key.ESCAPE:
			if not self.session.ingame_gui.on_escape():
				return # let the MainListener handle this
		elif keystr == 'g':
			gridrenderer = self.session.view.renderer['GridRenderer']
			gridrenderer.setEnabled( not gridrenderer.isEnabled() )
		elif keystr == 'x':
			self.session.destroy_tool()
		elif keystr == '+':
			self.session.speed_up()
		elif keystr == '-':
			self.session.speed_down()
		elif keystr == 'p':
			self.session.ingame_gui.toggle_ingame_pause()
		elif keystr == 'd':
			pass
			#import pdb; pdb.set_trace()
			#debug code to check for memory leaks:
			"""
			import gc
			import weakref
			all_lists = []
			for island in self.session.world.islands:
				buildings_weakref = []
				for b in island.buildings:
					buildings_weakref.append( weakref.ref(b) )
				import random
				random.shuffle(buildings_weakref)
				all_lists.extend(buildings_weakref)

				for b in buildings_weakref:
					if b().id == 17: continue
					if b().id == 1: continue # bo is unremovable

					#if b().id != 2: continue # test storage now

					print 'gonna remove: ', b()
					b().remove()
					collected = gc.collect()
					print 'collected: ', collected

					if b() is not None:
						import pdb ; pdb.set_trace()
						print 'referrers: ', gc.get_referrers(b())
						a = gc.get_referrers(b())
						print

			#print all_lists
			"""

		elif keystr == 'b':
			self.session.ingame_gui.show_build_menu()
		elif keystr == '.':
			if hasattr(self.session.cursor, "rotate_right"):
				self.session.cursor.rotate_right()
		elif keystr == ',':
			if hasattr(self.session.cursor, "rotate_left"):
				self.session.cursor.rotate_left()
		elif keystr == 'c':
			self.session.ingame_gui.show_chat_dialog()
		elif keyval in (fife.Key.NUM_0, fife.Key.NUM_1, fife.Key.NUM_2, fife.Key.NUM_3, fife.Key.NUM_4, fife.Key.NUM_5, fife.Key.NUM_6, fife.Key.NUM_7, fife.Key.NUM_8, fife.Key.NUM_9):
			num = int(keyval - fife.Key.NUM_0)
			if evt.isControlPressed():
				self.session.selection_groups[num] = self.session.selected_instances.copy()
				for group in self.session.selection_groups:
					if group is not self.session.selection_groups[num]:
						group -= self.session.selection_groups[num]
			else:
				for instance in self.session.selected_instances - self.session.selection_groups[num]:
					instance.deselect()
				for instance in self.session.selection_groups[num] - self.session.selected_instances:
					instance.select()
				self.session.selected_instances = self.session.selection_groups[num]
		elif keyval == fife.Key.F5:
			self.session.quicksave()
		elif keyval == fife.Key.F9:
			self.session.quickload()
		elif keystr == 't':
			# test performance
			print 'running tests'
			"""
			settler: wide range (12), 2x2
			weaver: medium range (8), 2x2
			market place: wide range (12), 6x6
			branch office/storage tent: extra wide range (24), 2x2

			small ranged buildings are not considerered
			(performance for very small ranges doesn't matter)
			"""
			testcases = {
			  100012: "settler left, mostly water, some trees",
			  100007: "settler center, some buildings (trees)",
			  100080: "settler right top, nearly only water, hardly any buildings",
			  100089: "settler bottom, 1/3 water, many buildings",
			  100103: "settler right, mostly no settlement, some buildings",
			  100097: "weaver right, nearly only water",
			  100094: "weaver bottom, mostly water, many buildings (trees)",
			  100100: "weaver center, only land, some buildings",
			  100087: "market place, mostly water, some buildings",
			  100085: "market place, water and land, some buildings",
			  100108: "storage tent, full settlement, water and land",
			  100002: "branch office, full settlement, water and land"
			  }

			categories = {
			  'settler' : [100012, 100007, 100080, 100089, 100103],
				'weaver' : [100097, 100094, 100100],
				'market' : [100087, 100085],
				'storage tent' : [100108],
				'branch office' : [100002]
				}

			avg = lambda l : float(sum(l)) / len(l)
			def med(l_orig):
				l = sorted(l_orig)
				if len(l) % 2 == 0:
					return float(l[ (len(l)/2) - 1 ] + l[ (len(l)/2) ]) / 2
				else:
					return l[ len(l)/2 ]
			def var(l):
				u = avg(l)
				var_sum = 0.0
				for i in l:
					var_sum += math.pow(i - u, 2)
				return var_sum / len(l)
			std_deriv = lambda l : math.sqrt(var(l))

			RUNS_PER_TESTCASE = 100

			results = dict.fromkeys(testcases.iterkeys()) # map testid -> result
			for testid in testcases:
				results[testid] = []
				obj = WorldObject.get_object_by_id(testid)
				print 'testing ', testid
				for i in xrange(RUNS_PER_TESTCASE):
					a = time.time()
					obj.select()
					b = time.time()
					results[testid].append(b-a)
					obj.deselect()
				#print 'avg: ', avg(results[testid])

			def analyse_category(cases):
				all_results =[]
				for case in cases: all_results.extend( results[case] )
				print 'avg: ', avg(all_results)
				print 'sdr: ', std_deriv(all_results)
				print 'med: ', med(all_results)
				print 'min: ', min(all_results)
				print 'rng: ', max(all_results) - min(all_results)
				return (avg(all_results), std_deriv(all_results))

			print 'done'
			main_values = []
			print 'results per test:'
			for case, description in testcases.iteritems():
				cat = ""
				for cat_i, cases in categories.iteritems():
					if case in cases:
						cat = cat_i
				print 'results for ', description, ' of cat ', cat
				m = analyse_category([case])
				main_values.append((str(case) + " "+ testcases[case], m))
				print

			print 'results per categories: (keep in mind: data get\'s mixed up here)'
			for cat, cases in categories.iteritems():
				print 'category ', cat
				m = analyse_category(cases)
				main_values.append((cat, m))
				print

			print 'all results combined (keep in mind: data get\'s mixed up here)'
			m = analyse_category(testcases)
			main_values.append(("all", m))

			print

			main_values_file = '/tmp/profile_test_main_values'
			if True or os.path.exists(main_values_file):
				print 'enter postfix for profile file to compare with:'
				postfix = sys.stdin.read(); print
				old_ms = None
				try:
					old_ms = yaml.load(open(main_values_file + '-' +postfix, 'r'))
				except IOError:
					print 'NO SUCH FILE'
				if old_ms != None:

					print 'main value comparison w/ last run\ncurrent - old;  current/old; old/current'
					for i in xrange(len(main_values)):
						new = main_values[i][1][0]
						old = old_ms[i][1][0]
						if main_values[i][0] != old_ms[i][0]:
							print 'INVALID COMPARISON'
						print new - old, ' ', new/old, ' ', old/new, 'for', main_values[i][0]
						#print main_values[i][1] - old_ms[i], ' ', main_values[i]/old_ms[i], \
						#	    ' ', old_ms[i]/main_values[i]
					print 'main value sum comparision'
					sum_new = sum(i[1][0] for i in main_values)
					sum_old = sum(i[1][0] for i in old_ms)

					print sum_new-sum_old, ' ', sum_new/sum_old, ' ', sum_old/sum_new
					#print sum(main_values) - sum(old_ms), ' ', sum(main_values)/sum(old_ms), \
					#	    ' ', sum(old_ms)/sum(main_values)

			yaml.dump(main_values, open(main_values_file, 'w'))

		else:
			return
		evt.consume()

	def keyReleased(self, evt):
		keyval = evt.getKey().getValue()
		try:
			self.keysPressed.remove(keyval)
		except:
			return
		if keyval == fife.Key.LEFT or \
		   keyval == fife.Key.RIGHT:
			self.key_scroll[0] = 0
		if keyval == fife.Key.UP or \
		   keyval == fife.Key.DOWN:
			self.key_scroll[1] = 0
		self.session.view.autoscroll_keys(self.key_scroll[0], self.key_scroll[1])

