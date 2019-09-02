from websocket import create_connection
import json
import time
import socket
import sys
import numpy as np


class Game:
	protocol = 'ws'
	host = 'codebb.cloudapp.net'
	recv_port = '17427'
	send_port = '17429'
	user = 'Name'
	password = '678'
	play_delay = 0.001
	v_thresh_brake = 0.5
	v_thresh_align = 0.04
	d_thresh = 800
	d_thresh_stuck = 50
	stuck_count = 0
	stuck_count_thresh = 50
	mines = {}


	def __init__(self):
		# initialize server connection
		self.cin = create_connection(self.protocol + '://' + self.host + ':' + self.recv_port)
		self.me = {}
		self.objective = {}

		self.old_state = self.getState()
		self.state = self.getState()

		players = { k: v for k, v in enumerate(self.state.get('players')) }
		bombs = { k: v for k, v in enumerate(self.state.get('bombs')) }
		mines = { k: v for k, v in enumerate(self.state.get('mines')) }
		wormholes = { k: v for k, v in enumerate(self.state.get('wormholes')) }

		self.mines = mines

		for m_index, mine in self.mines.items():
			for wh_index, wormhole in wormholes.items():
				radius = wormhole.get('radius')
				wh_px = wormhole.get('px')
				wh_py = wormhole.get('py')

				mine_px = mine.get('px')
				mine_py = mine.get('py')

				dx = mine_px - wh_px
				dy = mine_py - wh_py

				dist = np.sqrt(dx**2 + dy**2)
				
				if dist < 1.1*radius:
					self.mines[m_index]['in_wormhole'] = True
					break
				else:
					self.mines[m_index]['in_wormhole'] = False

		self.me['playerIndex'] = self.getPlayerIndexByName(players, self.user)

		data = self.user + ' ' + self.password + '\n' + 'ACCELERATE 1 1' + '\nCLOSE_CONNECTION\n'
		with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
			sock.connect((self.host, int(self.send_port)))
			sock.sendall(bytes(data, 'utf-8'))
			#sfile = sock.makefile()
			#rline = sfile.readline()
			#while rline:
			    #print(rline.strip())
			    #rline = sfile.readline()
		time.sleep(3)

	def getPlayerIndexByName(self, players, name):
		for index, player in players.items():
			if player.get('name') == name:
				return index
		return -1

	def getNearestMine(self, mines):
		bestMine = {
			'px': sys.float_info.max,
			'py': sys.float_info.max,
			'dx': sys.float_info.max,
			'dy': sys.float_info.max,
			'dist': sys.float_info.max,
			'owner': None
		}

		# see how far each mine is from us
		# - make sure the mine is not in a wormhole
		# - 
		for index, mine in mines.items():
			if mine.get('owner') == self.me.get('name') or mine.get('in_wormhole'):
				#print('what?!?!?')
				continue

			dx = mine.get('px') - self.me.get('px')
			dy = mine.get('py') - self.me.get('py')
			dist = np.sqrt(dx**2 + dy**2)

			if dist < bestMine['dist']:
				#print('BETTER')
				bestMine['px'] = mine.get('px')
				bestMine['py'] = mine.get('py')
				bestMine['dx'] = dx
				bestMine['dy'] = dy
				bestMine['dist'] = dist
				bestMine['owner'] = mine.get('owner')

		return bestMine

	def translateAngle(self, angle):
		return (2*np.pi - angle) % 2*np.pi

##############################

	# gameplay loop
	def play(self):
		while True:
			# get the state
			state = self.getState()
			#print(state)

			# evaluate the state
			evaluation = self.evalState(state)
			
			# get the action
			action = self.getAction(evaluation)
		
			# send the action
			self.sendAction(action)
			
			# wait until next turn
			#time.sleep(self.play_delay)

##############################

	# determine the state by connecting to the server
	def getState(self):
		data = self.cin.recv()
		state = json.loads(data)
		return state
		

	# evaluate the state of the game for best approach
	def evalState(self, state):
		self.me = {
			**self.me,
			**state.get('players')[self.me.get('playerIndex')]
		}

		#print('Me:    px: ' + str(self.me.get('px')) + ', py: ' + str(self.me.get('py')))

		mines = { k: v for k, v in enumerate(state.get('mines')) }

		for index, mine in mines.items():
			mines[index]['in_wormhole'] = self.mines[index]['in_wormhole']

		self.mines = mines

		bestMine = self.getNearestMine(self.mines)

		return bestMine
	
	# get the action from the evaluation
	def getAction(self, evaluation):
		# calculate angle
		# we now have the best mine. how do we get there?
		bestMine = evaluation
		if self.me.get('aligned') == None or (bestMine.get('px') != self.me.get('bestMine').get('px') and bestMine.get('py') != self.me.get('bestMine').get('py')):
			self.me['aligned'] = False
			self.stuck_count = 0
		self.me['bestMine'] = bestMine
		angle = None

		dx = bestMine.get('dx')
		dy = bestMine.get('dy')

		#print('Mine:  px: ' + str(bestMine.get('px')) + ', py: ' + str(bestMine.get('py')) + ', dist: ' + str(bestMine.get('dist')))

		angle = np.arctan2(-dy, dx)

		if angle <= 0:
			return -angle
		else:
			return 2*np.pi - angle
	
	# translate the action into server language
	def sendAction(self, action):
		# gives the text action(s) of the action
		def processAction():
			if self.me.get('bestMine').get('dist') < self.d_thresh and not self.me.get('aligned') and abs(self.me.get('vx')) > self.v_thresh_align and abs(self.me.get('vy')) > self.v_thresh_align:
				self.stuck_count = 0
				return [ 'BRAKE' ]
			elif self.me.get('bestMine').get('dist') < self.d_thresh:
				self.me['aligned'] = True

				if self.me.get('bestMine').get('dist') < self.d_thresh_stuck:
					self.stuck_count += 1
					print(self.stuck_count)

				if self.stuck_count > self.stuck_count_thresh:
					self.stuck_count = 0
					self.me['aligned'] = False
					return [ 'ACCELERATE 0 1' ]

				else:
					return [ 'ACCELERATE ' + str(action) + ' 0.8' ]
			else:
				return [ 'ACCELERATE ' + str(action) + ' 1' ]

			


		action_array = processAction()
		#print(str(action))
		#print(action_array[0] + str(self.me.get('aligned')))
		

		# connect, then send commands, then chill
		data = self.user + ' ' + self.password + '\n' + '\n'.join(action_array) + '\nCLOSE_CONNECTION\n'
		with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
			sock.connect((self.host, int(self.send_port)))
			sock.sendall(bytes(data, 'utf-8'))
			#sfile = sock.makefile()
			#rline = sfile.readline()
			#while rline:
			    #print(rline.strip())
			    #rline = sfile.readline()

		return None

if __name__ == '__main__':
	the_game = Game()
	the_game.play()
