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

from horizons.ext.enum import Enum
from horizons.constants import RES
from horizons.scheduler import Scheduler


# event conditions to specify at check_events()
CONDITIONS = Enum('settlements_num_greater', 'settler_level_greater', \
                  'player_gold_greater', 'player_gold_less', 'settlement_balance_greater',
                  'building_num_of_type_greater', 'settlement_inhabitants_greater',
                  'player_balance_greater', 'player_inhabitants_greater',
                  'player_res_stored_greater', 'player_res_stored_less', 'settlement_res_stored_greater', 'time_passed', \
                  'var_eq', 'var_gt')

# Condition checking is split up in 2 types:
# 1. possible condition change is notified somewhere in the game code
# 2. condition is checked periodically

# conditions that can only be checked periodically
_scheduled_checked_conditions = (CONDITIONS.player_gold_greater, \
                                CONDITIONS.player_gold_less, \
                                CONDITIONS.settlement_balance_greater, \
                                CONDITIONS.settlement_inhabitants_greater, \
                                CONDITIONS.player_balance_greater, \
                                CONDITIONS.player_inhabitants_greater, \
                                CONDITIONS.player_res_stored_greater,
				CONDITIONS.player_res_stored_less,
                                CONDITIONS.settlement_res_stored_greater,
                                CONDITIONS.time_passed)

###
# Campaign Conditions

def settlements_num_greater(session, limit):
	"""Returns whether the number of settlements owned by the human player is greater than limit."""
	return len(_get_player_settlements(session)) > limit

def settler_level_greater(session, limit):
	"""Returns wheter the max level of settlers is greater than limit"""
	return (session.world.player.settler_level > limit)

def player_gold_greater(session, limit):
	"""Returns whether the player has more gold then limit"""
	return (session.world.player.inventory[RES.GOLD_ID] > limit)

def player_gold_less(session, limit):
	"""Returns whether the player has less gold then limit"""
	return (session.world.player.inventory[RES.GOLD_ID] < limit)

def settlement_balance_greater(session, limit):
	"""Returns whether at least one settlement of player has a balance > limit"""
	return any(settlement for settlement in _get_player_settlements(session) if \
	           settlement.balance > limit)

def player_balance_greater(session, limit):
	"""Returns whether the cumulative balance of all player settlements is > limit"""
	return (sum(settlement.balance for settlement in _get_player_settlements(session)) > limit)

def settlement_inhabitants_greater(session, limit):
	"""Returns whether at least one settlement of player has more than limit inhabitants"""
	return any(settlement for settlement in _get_player_settlements(session) if \
	           settlement.inhabitants > limit)

def player_inhabitants_greater(session, limit):
	"""Returns whether all settlements of player combined have more than limit inhabitants"""
	return (sum(settlement.inhabitants for settlement in _get_player_settlements(session)) > limit)

def building_num_of_type_greater(session, building_class, limit):
	"""Check if player has more than limit buildings on a settlement"""
	for settlement in _get_player_settlements(session):
		if len([building for building in settlement.buildings if \
		       building.id == building_class]) > limit:
			return True
	return False

def player_res_stored_greater(session, res, limit):
	"""Returns whether all settlements of player combined have more than limit of res"""
	return (sum(settlement.inventory[res] for settlement in _get_player_settlements(session)) > limit)

def player_res_stored_less(session, res, limit):
	"""Returns whether all settlements of player combined have less than limit of res"""
	return (sum(settlement.inventory[res] for settlement in _get_player_settlements(session)) < limit)

def settlement_res_stored_greater(session, res, limit):
	"""Returs whether at least one settlement of player has more than limit of res"""
	return any(settlement for settlement in _get_player_settlements(session) if \
	           settlement.inventory[res] > limit)

def time_passed(session, secs):
	"""Returns whether at least secs seconds have passed since start."""
	return (Scheduler().cur_tick >= Scheduler().get_ticks(secs))

def var_eq(session, name, value):
	if not name in _get_scenario_vars(session):
		return False
	return (_get_scenario_vars(session)[name] == value)

def var_gt(session, name, value):
	"""Variable greater then..."""
	if not name in _get_scenario_vars(session):
		return False
	return (_get_scenario_vars(session)[name] > value)

def _get_player_settlements(session):
	"""Helper generator, returns settlements of local player"""
	return session.world.player.settlements

def _get_scenario_vars(session):
	return session.campaign_eventhandler._scenario_variables

