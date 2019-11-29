import pygame, sys
from pygame.locals import *
import pickle
import select
import socket


WIDTH = 400
HEIGHT = 400
PLAYER_SIZE = 20
BUFFERSIZE = 4096
FONT_SIZE = 20
playerid = 0
players = []

pygame.font.init()

#game events
#['event type', param1, param2]
#
# player locations
# ['player locations', [id, x, y], [id, x, y] ...]
# settings
# ['settings',playerid,width,height,player_size,x,y]
# set name
# ['set name', id, name]
#user commands
# position update
# ['position update', id, x, y]
# set name
# ['set name', id, name]

class Player:
  def __init__(self, x, y, id, color = (0,0,0), score = 0,name = ""):
    self.x = x
    self.y = y
    self.vx = 0
    self.vy = 0
    self.id = id
    self.color = color
    self.score = score
    self.name = name

  #Move o quadrado de acordo com a vx e vy sem deixar sair da tela
  def update(self):
    self.x += self.vx
    self.y += self.vy

    if self.x > WIDTH - PLAYER_SIZE:
      self.x = WIDTH - PLAYER_SIZE
    if self.x < 0:
      self.x = 0
    if self.y > HEIGHT - PLAYER_SIZE:
      self.y = HEIGHT - PLAYER_SIZE
    if self.y < 0:
      self.y = 0

  #Desenha um quadrado de tamanho PLAYER_SIZE com a vertice superior esquerda em x,y
  def render(self):
    pygame.draw.polygon(screen,self.color, 
    [(self.x, self.y),(self.x + PLAYER_SIZE, self.y), (self.x + PLAYER_SIZE, self.y + PLAYER_SIZE),
    (self.x, self.y + PLAYER_SIZE)] )

#Configurações do socket
serverAddr = '127.0.0.1'
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((serverAddr, 4321))

#A primeira resposta do servidor é sempre as configurações do jogo, como o id que o jogador recebeu
#a largura e altura da tela, o tamanho da aresta que representa o jogador, e seu x,y inicial
data = sock.recv(BUFFERSIZE)
settings = pickle.loads(data)
print(str(settings))
playerid = settings[1]
WIDTH = settings[2]
HEIGHT = settings[3]
PLAYER_SIZE = settings[4]
x = settings[5]
y = settings[6]

#Gera um nome a partir do id que foi atribuido, se foi passado um nome como argumento 
#na chamada do jogo, usa este no lugar.
#Envia o nome ao servidor, que responde com o nome escolhido.
name = "player" + str(playerid)
if len(sys.argv) == 2:
  name = sys.argv[1]
sock.send(pickle.dumps(["set name",playerid,name]))
data = sock.recv(BUFFERSIZE)
settings = pickle.loads(data)

selfplayer = Player(x, y, 0,(0,128,0),name=settings[2])

#Configurações iniciais do pygame
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('Game')
font = pygame.font.Font('freesansbold.ttf', FONT_SIZE) 
clock = pygame.time.Clock()

#Loop de eventos
while True:
  #select faz com que ins = sock,este sendo o socket, quando este tem algo para ser recebido
  ins, outs, ex = select.select([sock], [], [], 0)

  for inm in ins: 
    try:
      #Servidor sempre envia um vetor, na primeira posição o nome do evento que ele enviou
      #Neste caso, ele somente envia regurlamente a atualização dos items no mapa
      gameEvent = pickle.loads(inm.recv(BUFFERSIZE))
      if gameEvent[0] == 'player locations':

        gameEvent.pop(0)
        players = []

        for item in gameEvent:
          # Se o id for 1, significa que o item é uma fruta, se for igual ao playerid, que é este jogador
          # Caso contrario são outros jogadores
          # item[1] = x,
          # item[2] = y,
          # item[0] = itemid
          # item[3] = pontuação
          # item[4] = nome
          if item[0] != playerid and item[0] != 1:
            players.append(Player(item[1], item[2], item[0],score=item[3],name=item[4] ) )

          if item[0] == 1:
            players.append(Player(item[1], item[2], item[0],(252, 202, 3) ) )

          if item[0] == playerid:
            selfplayer.score = item[3]

    except Exception as err:
      print(err)
      continue
    
  for event in pygame.event.get():
    if event.type == QUIT:
    	pygame.quit()
    	sys.exit()
    # Faz ter velocidade se apertar uma tecla e zera a velocidade quando solta
    if event.type == KEYDOWN:
      if event.key == K_LEFT: selfplayer.vx = -10
      if event.key == K_RIGHT: selfplayer.vx = 10
      if event.key == K_UP: selfplayer.vy = -10
      if event.key == K_DOWN: selfplayer.vy = 10

    if event.type == KEYUP:
      if event.key == K_LEFT: selfplayer.vx = 0
      if event.key == K_RIGHT: selfplayer.vx = 0
      if event.key == K_UP: selfplayer.vy = 0
      if event.key == K_DOWN : selfplayer.vy = 0

  # Limita 60fps
  clock.tick(60)
  # Fundo branco
  screen.fill((255,255,255))

  # Move o jogador
  selfplayer.update()

  # Renderiza todos os jogadores
  for p in players:
    p.render()
  selfplayer.render()

  # Cria um vetor com todos jogadores, ordena pelo score
  allPlayers = players.copy()
  allPlayers.append(selfplayer)
  allPlayers.sort(key = lambda x: x.score,reverse=True)
  
  # criar uma linha para cada jogador com o seu nome e pontuação, a partir do vetor ordenado
  line = 0
  for pl in allPlayers:
    if pl.id != 1:
      color = (200, 0, 0)
      if pl.id == playerid:
        color = (0, 0, 220)
      text = font.render(str(pl.name) + ": " + str(pl.score) , True, color )
      screen.blit(text, (0,(line*FONT_SIZE)+(5*line)))
      line += 1

  pygame.display.flip()

  # Envia para o servidor a posição do jogador
  dump = pickle.dumps(['position update', playerid, selfplayer.x, selfplayer.y])
  sock.send(dump)
sock.close()
