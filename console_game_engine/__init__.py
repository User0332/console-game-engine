'''A handy module for creating game-like console applications with and without curses

console_game_engine supports:

keyboard input (from console ONLY)
frame limiting (through use of a time.sleep delay)
multiple games (through multiple filestreams)
update functions (pre-frame update and post-frame update)
and a full interface to creating different entities through the ConsoleGame and CursesGame classes'''

import msvcrt
import time
import copy
import warnings
import curses
from stdutils.io import Console
from types import FunctionType

class _Entity:
	def __init__(self, character, pos, collideable, collide_action):
		self.character = character
		self.pos = pos
		self.collideable = collideable
		self.action = collide_action

class _DynamicEntity(_Entity):
	def __init__(self, character, start_pos, collideable, collide_action):
		self.character = character
		self.pos = list(start_pos)
		self.collideable = collideable
		self.action = collide_action

	def _change_position(self, x, y):
		self.pos[0]+=x
		self.pos[1]+=y

class _Collectible(_Entity):
	def __init__(self, character, pos, action):
		self.char = character
		self.pos = pos
		self.action = action

class _Player(_DynamicEntity):
	def __init__(self, character, start_pos, mov_u, mov_l, mov_d, mov_r, collideable, collide_action):
		self.char = character
		self.pos = list(start_pos)
		self.left = mov_l
		self.right = mov_r
		self.up = mov_u
		self.down = mov_d
		self.collideable = collideable
		self.action = collide_action

	def change_position(self, key) -> int:
		if key in self.left:
			super()._change_position(-1, 0)
		elif key in self.right:
			super()._change_position(1, 0)
		elif key in self.up:
			super()._change_position(0, -1)
		elif key in self.down:
			super()._change_position(0, 1) 
		else:
			return -1

		return 0

class _Board:
	def __init__(self, board: list[list[str]]):
		self.board = board
		self.x = len(self.board)-1
		self.y = len(self.board[0])-1
		self._copy = copy.deepcopy(self.board)

	def __str__(self):
		board_str = ""

		for row in self.board:
			board_str+="".join(row)+"\n"
		
		return board_str
	def _original(self):
		return copy.deepcopy(self._copy)

	def _original_as_string(self):
		return str(_Board(self._original()))

class ConsoleGame:
	'''A non-curses console game class which uses 2D arrays for a map/board'''

	def __init__(self, board: list[list[str]]):
		self.board = _Board(board)
		self.entities = {
			"Players" : [],
			"Collectibles" : []
			}
		self._active = False

	def _get_input(self): 
		first = msvcrt.getch()
		
		if first == b'\xe0':
			try:										
				return { 
					72 : "up", 
					80 : "down", 
					77 : "right", 
					75 : "left" 
					}[ord(msvcrt.getch())]
			except KeyError:
				return "NULL"
		else:
			return first.decode()

	def initialize(self, smart_updating: bool=False, interval_updating: bool=False,  preupdate: FunctionType=None, postupdate: FunctionType=None, on_key: FunctionType=None, delay_per_iteration: float=0) -> None:
		if smart_updating and interval_updating:
			warnings.warn("Specifying both smart and interval updating will only result in the use of smart updating.", UserWarning)
			time.sleep(5)

		self.smart_updating = smart_updating
		self.interval_updating = interval_updating
		self.interval = 1
		self._pending_update = True
		self.preupdate = preupdate
		self.postupdate = postupdate 
		self.on_key = on_key
		self.delay = delay_per_iteration
		self._active = True
		
	def quit(self) -> None:
		self.smart_updating = False
		self.interval_updating = False		
		self._pending_update = False
		self.preupdate = None
		self.postupdate = None 
		self.on_key = None
		self.delay = 0
		self._active = False

	def change_player_position(self, player: _Player, key: str) -> int:
		res = player.change_position(key)
		self._pending_update = True
		return res

	def _update_and_display_board(self):
		Console.clear()

		self.board.board = self.board._original()

		#display players
		for player in self.entities["Players"]:
			player_x = player.pos[1]
			player_y = player.pos[0]
				
			#IndexError Protection
			if player_x > self.board.x:
				diff_x = player_x - self.board.x

				player_x-=diff_x

				player.pos[1] = player_x

			elif player_y > self.board.y:
				diff_y = player_y - self.board.y

				player_y-=diff_y

				player.pos[0] = player_y

			elif player_x < 0:
				player.pos[1] = player_x = 0

			elif player_y < 0:
				player.pos[0] = player_y = 0


			self.board.board[player_x][player_y] = player.char


		
		Console.writeline(self.board)

	def start(self) -> None:
		iteration = 0
		while self._active:

			if self.preupdate:
				self.preupdate()

			#keyinput
			if msvcrt.kbhit():
				key = self._get_input()
				if self.on_key:
					self.on_key(key)

			#Board updating using smart and interval updating
			if self.smart_updating:
				if self._pending_update:
					self._update_and_display_board()
					self._pending_update = False

			elif self.interval_updating:
				if iteration % self.interval == 0:
					self._update_and_display_board()
			else:
				self._update_and_display_board()
				

			if self.postupdate:
				self.postupdate()

			time.sleep(self.delay)
			
			iteration+=1

	def add_player(self, character: str, start_pos: tuple[int], mov_u: str="up", mov_l: str="left", mov_d: str="down", mov_r: str="right", collideable: bool=False, collide_action: FunctionType=None) -> _Player: 
		player = _Player(character, start_pos, mov_u, mov_l, mov_d, mov_r, collideable, collide_action)
		self.entities["Players"].append(player)
		return player

	def add_collectible(self, character: str, pos: tuple[int], action: FunctionType=None) -> _Collectible:
		def do_nothing(*args, **kwargs): pass
		action = action if action else do_nothing
		collectible = _Collectible(character, pos, action)
		self.entities["Collectibles"].append(collectible)
		return collectible



class CursesGame:
	def __init__(self, board):
		self.board = board

	def quit(self):
		self._running = False

	def start(self):
		self._running = True
		stdscr = curses.init()
		curses.curs_set(0)
		while self._running:
			pass #game

		curses.curs_set(1)
		curses.endwin()