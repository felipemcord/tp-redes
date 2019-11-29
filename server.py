import socket
import asyncore
import random
import pickle
import time
import asyncio
import threading

BUFFERSIZE = 4096
WIDTH = 800
HEIGHT = 600
PLAYER_SIZE = 20
FRUIT_ID = 1
AI_ID = 2
AI_MOV = 1

# O socket de todos players ativo
playersSocket = []
# Todos os items/jogadores ativo
worldMap = {}
# O sockets que deram erro/tem que ser removidos
socketRemove = []

# move o item que é controlado pela máquina
# movementFrequency determina o quão frequente ela ira mover, determinando então sua velocidade
def moveAI():
  aiLastMove = 0
  movementFrequency = 0.004
  while True:
    if time.time() - aiLastMove > movementFrequency and len(worldMap.keys()) > 2:
      fruit = worldMap[FRUIT_ID]
      AI = worldMap[AI_ID]

      if AI.x > fruit.x:
        AI.x -= AI_MOV
      elif AI.x < fruit.x:
        AI.x += AI_MOV

      if AI.y > fruit.y:
        AI.y -= AI_MOV
      elif AI.y < fruit.y:
        AI.y += AI_MOV

      if(collisionFruit(AI.x,AI.y)):
        generateFruit()
        worldMap[AI_ID].score += 1

      aiLastMove = time.time()

# Items podem ser jogadores ou frutas
# São iniciados com uma posição aleatoria
class Item:
  def __init__(self, itemId, name):
    self.x = random.randint(0,WIDTH - PLAYER_SIZE)
    self.y = random.randint(0,HEIGHT - PLAYER_SIZE)
    self.itemId = itemId
    self.score = 0
    self.name = name

# Classes para receber dados dos clientes
# Quando o servidor recebe uma mensagem de um cliente, a função handle_read é chamada
# Le a mensagem e encaminha para a função apropriada
# Caso tenha um problema em ler a mensagem, o socket é fechado e o jogador retirado do jogo
class HandlePlayer(asyncore.dispatcher_with_send):
  def __init__(self,sock,playerId):
    asyncore.dispatcher_with_send.__init__(self,sock)
    self.playerSocket = sock
    self.playerId = playerId
  
  def handle_read(self):
    recievedData = self.recv(BUFFERSIZE)

    if recievedData:
      message = pickle.loads(recievedData)

      if(message[0] == "set name"):
        worldMap[message[1]].name = message[2]
        self.send(pickle.dumps(["set name",message[1],message[2]] ))

      else:
        updateWorld(message)

    else: 
      del worldMap[self.playerId]
      socketRemove.append(self.playerSocket)
      self.close()

# Função para gerar uma nova fruta no mapa
def generateFruit():
  fruit = Item(FRUIT_ID,"Fruit")
  worldMap[FRUIT_ID] = fruit

# Determinar se alguem encostou na fruta
def collisionFruit(x,y):
  fruit = worldMap[FRUIT_ID]
  
  if(fruit.x <= x <= fruit.x + PLAYER_SIZE or fruit.x <= x + PLAYER_SIZE <= fruit.x + PLAYER_SIZE):
    if(fruit.y <= y <= fruit.y + PLAYER_SIZE):
      return True
    if(fruit.y <= y + PLAYER_SIZE <= fruit.y + PLAYER_SIZE):
      return True
  return False

# Função para atualizar a posição do jogador que enviou uma mensagem ao servidor
# e replicar essa mudança aos outros jogadores
def updateWorld(message):
  global socketRemove
  arr = message
  playerId = arr[1]
  x = arr[2]
  y = arr[3]
  

  if playerId == 0: 
    return

  worldMap[playerId].x = x
  worldMap[playerId].y = y

  if(collisionFruit(x,y)):
    generateFruit()
    worldMap[playerId].score += 1

  update = ['player locations']

  for key, value in worldMap.items():
    update.append([value.itemId, value.x, value.y,value.score,value.name])
  
  dump = pickle.dumps(update)
  print(len(dump))
  for sockt in playersSocket:
    
    try:
      sockt.send(dump)
    except Exception:
      socketRemove.append(sockt)
      continue
  
  for r in socketRemove:
    try:
      playersSocket.remove(r)
    except Exception:
      continue
  socketRemove = []
 
# Função para receber novos jogadores
# Usa asyncore para receber as conexões de forma assíncrona
# Inicia em uma nova thread a função que move o jogador controlado pela máquina
# Quando uma nova conexão é recebida, handle_accept é chamada
class HandleNewPlayers(asyncore.dispatcher):

  def __init__(self, port):

    asyncore.dispatcher.__init__(self)
    self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
    self.bind(('', port))
    self.listen(10)

    generateFruit()
    worldMap[AI_ID] = Item(AI_ID,"ROBOT")
    self.moveAI = threading.Thread(target=moveAI)
    self.moveAI.start()
    
  # Chamada quando um novo jogador se conecta
  # Adiciona seu socket ao vetor de sockets, atribui um id, cria seu item no mapa
  # Envia as configurações usadas e então chama handleplayer para cuidar dos dados enviados a ele
  def handle_accept(self):

    sock, addr = self.accept()
    
    playersSocket.append(sock)

    playerId = random.randint(1000, 1000000)
    while playerId in worldMap.keys():
      playerId = random.randint(1000, 1000000)
    player = Item(playerId,"")

    worldMap[playerId] = player
    dump = pickle.dumps(['settings', playerId,WIDTH,HEIGHT,PLAYER_SIZE,player.x,player.y])
    print(len(dump))
    sock.send(dump)

    HandlePlayer(sock,playerId)


HandleNewPlayers(4321)
# Função para iniciar o loop de recepção de mensagens, nova conexões
asyncore.loop()
  