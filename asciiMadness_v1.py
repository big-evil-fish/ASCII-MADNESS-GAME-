#credit to 112 tetris for a few matrix collision functions!
from cmu_graphics import *
import copy
import math
import random


def onAppStart(app):
    app.highScore = 0
    app.hasWon = False
    onGameStart(app)


def onGameStart(app):
    app.paused = True
    app.width = 1024
    app.height = 768

    app.terminalLeft = 30
    app.terminalTop = app.height/15
    app.terminalWidth = 800
    app.terminalHeight = 650

    app.isSplashScreen = True
    button.i = 0
    app.buttons = [button(app, 'storymode', 80, 30), 
                   button(app, 'infinite', 80, 30)]
    app.hoveredButton = None

    terminalcx, terminalcy = getTerminalCxCy(app)

    app.playerBoundLeft = app.terminalLeft + app.terminalWidth/15
    app.playerBoundTop = app.terminalTop + app.terminalHeight/15
    app.playerBoundRight = (app.terminalLeft + app.terminalWidth 
                            - app.terminalWidth/15)
    app.playerBoundBottom = (app.terminalTop + app.terminalHeight 
                             - app.terminalHeight/15)

    app.cellSize = 11 #px
    playerDesign = loadDesign('player')
    app.player = playerSprite(playerDesign, terminalcx, terminalcy) 
    
    app.walkCounter = 0
    app.echoFadeCounter = 0
    app.smokeCounter = 0
    app.smokeSpawnCounter = 0
    app.dashCounter = 0
    app.attackCounter = 0
    app.blockCharCounter = 0
    app.cursorSpawnCounter = 0
    app.cursorSpawnThreshhold = 90
    app.codeBlockSpawnCounter = 0
    app.powerUpSpawnCounter = 0
    
    app.points = 0
    
    app.cursors = []

    app.codeBlocks = []
    app.isTypingCodeBlock = False
    app.blockChars = []
    app.powerUps = []
    app.healthPacks = []

    app.sweepConeWidth = 70
    app.attackOffset = 40

    app.echoTimeLength = 60
    app.personalMouseDMG = 10
    app.sidePressed = False
    app.verticalPressed = False

    app.buffDuration = 1000

    app.storyStep = 0
    app.textToDisplay = ''
    app.displayedText = ''
    app.bigText = False

###### CLASSES
class button():
    i = 0 # to more easily add buttons in future
    def __init__(self, app, string, width, height):
        self.name = string
        self.cx = app.terminalLeft + app.terminalWidth/2
        self.cy = app.terminalTop + app.terminalHeight/1.4 + button.i*70
        self.width = width
        self.height = height
        button.i += 1

class playerSprite:
    def __init__(self, design, cx, cy):
        self.body = design # 2D list of ASCII indexes
        self.walkingBody = copy.copy(self.body)
        self.cx = cx 
        self.cy = cy
        self.dx = 1

        self.moveSpeed = 6
        self.isWalking = False
        self.steppingOut = True
        self.hasFeet = True
        
        self.dashLength = 10
        self.dashCoolDown = 10
        self.dashAvailable = True
        self.dashEchoes = []

        self.smokeSpirals = []
        self.hasBuff = False
        self.buffs = dict() # mapping of buff name : time left

        self.isAttacking = False
        self.attackAngle = 0

        self.isDead = False

    def damage(self, row, col, amt):
        #apply damage
        self.body[row][col] = max(self.body[row][col] - amt, 32) #cutoff at 32
        #check if row is empty
        if rowIsAll32s(self.body[row]):
            if self.hasFeet:
                rows = len(self.body)
                footRow = rows - 1
                if row == footRow: self.hasFeet = False
            self.body.pop(row)
        # check if col is empty
        elif colIsAll32s(self.body, col):
            removeCol(self.body, col)

    def flip(self):
        self.body = flippedHorizontally(self.body)

    def move(self, app, dy, dx): 
        self.cx += self.moveSpeed * dx
        self.cy += self.moveSpeed * dy
        if not spriteIsLegal(app):
            self.cx -= self.moveSpeed * dx
            self.cy -= self.moveSpeed * dy
            return False
        return True
    
    def walk(self, app):
        self.walkingBody = copy.deepcopy(self.body) # dont mess with og matrix
        left = True if self.dx == 1 else False # more readable direction
        rows = len(self.body)
        footRow = rows - 1
        # how to animate if one foot left
        if self.hasFeet and feetCount(self.body[footRow]) == 1:
            footIndex = self.body[footRow].index(124)
            if app.player.steppingOut:
                self.walkingBody[footRow][footIndex] = 47 if left else 92 #/ or \
            else:
                self.walkingBody[footRow][footIndex] = 124 # |
        #how to animate if two feet left 
        elif self.hasFeet and feetCount(self.body[footRow]) == 2:
            footIndex1 = getFirstFootIndex(self.body[footRow])
            footIndex2 = footIndex1 + 1
            steppingFoot = footIndex1 if app.player.steppingOut else footIndex2
            standingFoot = footIndex2 if app.player.steppingOut else footIndex1
            self.walkingBody[footRow][standingFoot] = 124 # |
            self.walkingBody[footRow][steppingFoot] = 47 if left else 92 #/ or \

    def dash(self, app, dy, dx):
        preDashLeftCoord, predashTopCoord = getPlayerLeftTop(app)
        self.dashEchoes.append((echo(preDashLeftCoord, predashTopCoord, 
                                     app.player.dx)))
        i = 0
        while self.move(app, dy, dx):
            i += 1
            if i == self.dashLength:
                break
    
    #buffs
    def spawnSmoke(self, app):
        left, top = getPlayerLeftTop(app)
        rows, cols = len(self.body), len(self.body[0])
        playerWidth, playerHeight = cols * app.cellSize, rows * app.cellSize
        right, bottom = left+ playerWidth, top + playerHeight
        cy = bottom
        cx = random.randrange(int(left), int(right))
        self.smokeSpirals.append(smoke(cx,cy, top))
    
    def addBuff(self, name, app):
        #applying buff effects:
        if name not in self.buffs:
            if name == 'green':
                self.dashLength *= 2
            if name == 'blue':
                self.moveSpeed *= 1.5
            if name == 'purple':
                self.dashCoolDown /= 2
        #adding buff to time dictionary
        self.buffs[name] = app.buffDuration
        self.hasBuff = True

    
    def revertBuff(self, buff):
        #reversing effects of given buff
        if buff == 'green':
            self.dashLength /= 2
        if buff == 'blue':
            self.moveSpeed /=1.5
        if buff == 'purple':
            self.dashCoolDown *= 2
        
    
    def decayBuffs(self):
        if len(self.buffs) == 0:
            self.hasBuff = False
        for buff in self.buffs:
            if self.buffs[buff] == 0:
                self.revertBuff(buff)
                self.buffs.pop(buff)
                break
            else:
                self.buffs[buff] -= 1
    
    ## attack
    def attack(self, mouseX, mouseY):
        self.attackAngle = getAngle(self.cx, self.cy, mouseX, mouseY)
        self.isAttacking = True

    def animateAttack(self, app):
        sweepConeWidth = app.sweepConeWidth
        if app.attackCounter == 0:
            self.startAngle = self.attackAngle-(sweepConeWidth/2) + 10
            self.sweepAngle = sweepConeWidth
        elif 4 > app.attackCounter >= 3:
            self.startAngle = self.attackAngle-(sweepConeWidth/2)
            self.sweepAngle = sweepConeWidth/1.9
        elif 6 > app.attackCounter >= 4:
            self.startAngle = self.attackAngle-(sweepConeWidth/2)
            self.sweepAngle = sweepConeWidth/2.7
        app.attackCounter += 1
        if app.attackCounter >= 6:
            self.isAttacking = False
            app.attackCounter = 0

    def drawAttack(self, app):
        rows, cols = len(app.player.body), len(app.player.body[0])
        playerWidth, playerHeight = cols * app.cellSize, rows * app.cellSize
        offset = app.attackOffset 
        attackHeight = playerHeight + offset
        attackWidth = playerWidth + offset
        if app.attackCounter > 0:
            drawArc(self.cx, self.cy, attackWidth, attackHeight, 
                    self.startAngle, self.sweepAngle, fill = 'white')
            drawOval(self.cx, self.cy, playerWidth + 35, playerHeight + 35)


class echo():
    def __init__(self, left, top, dx):
        self.left = left
        self.top = top
        self.dx = dx
        self.time = 0

    def draw(self, app, body):
        x, y = self.left, self.top
        if (self.dx == -1 and app.player.dx == 1
            or self.dx == 1 and app.player.dx == -1):
            echoBody = flippedHorizontally(body)
        else:
            echoBody = copy.deepcopy(body)
        cellWidth = cellHeight = app.cellSize
        rows, cols = len(body), len(body[0])
        for row in range(rows):
            for col in range(cols):
                if echoBody[row][col] != 32:
                    #aligning with body since mssg is centered
                    echoCellX = (x + cellWidth) + col * (cellWidth) 
                    echoCellY = (y + cellHeight) + row * (cellHeight)
                    drawLabel('.', echoCellX, echoCellY, fill = 'white', 
                              size = 20, opacity = 100/(self.time+1))


class smoke:

    def __init__(self, cx, cy, top):
        boundRadius = 4
        self.cx = cx
        self.bound1 = cx - boundRadius
        self.bound2 = cx + boundRadius
        self.cyBound = top
        self.cy = cy
        self.dx = 1
        self.opacity = 100
    
    def changeDirection(self):
        self.dx *= -1

    def move(self):
        self.cx += self.dx
        self.cy -= 2
    
    def draw(self, app):
        if len(app.player.buffs) > 0: #flashy effect!
            fillColor = random.choice(list(app.player.buffs)) 
        else:
            fillColor = 'grey' #signals that buff is over
        drawLabel('@', self.cx, self.cy, 
                  opacity = self.opacity, fill = fillColor, size = 15)

class cursor:
    def __init__(self, app, cx, cy, dx, dy, accelerationx, accelerationy):
        self.cx = cx
        self.cy = cy
        self.dx = dx
        self.dy = dy
        self.accelerationx = accelerationx
        self.accelerationy = accelerationy
        self.angle = getAngle(self.cx, self.cy, app.player.cx, app.player.cy)
        self.lifeSpan = 120

    def move(self):
        self.cx += self.dx
        self.cy += self.dy
        self.dx += self.accelerationx
        self.dy += self.accelerationy
    
    def updateAngle(self, app):
        self.angle = getAngle(self.cx, self.cy, app.player.cx, app.player.cy)


    def draw(self):
        angle = 90 - self.angle
        seperation = 8
        drawRegularPolygon(self.cx, self.cy, 7, 3, fill = 'white', 
                           rotateAngle = angle)
        drawRect(self.cx-self.accelerationx*seperation, 
                 self.cy-self.accelerationy*seperation, 3, 15, fill = 'white', 
                 align = 'center', rotateAngle = angle)

class arcCursor(cursor):
    def __init__(self, app, cx, cy, dx, dy, accelerationx, 
                 accelerationy, speed = 0.13, amplitude = 7):
        super().__init__(app, cx, cy, dx, dy, accelerationx, accelerationy)
        self.linearCx = cx
        self.linearCy = cy
        self.counter = 0
        self.speed = speed
        self.amplitude = amplitude

    
    def move(self):
        self.linearCx += self.dx
        self.linearCy += self.dy
        self.cx = self.linearCx + self.dy*math.sin(self.counter)*self.amplitude
        self.cy = self.linearCy + self.dx*math.sin(self.counter)*self.amplitude
        self.dx += self.accelerationx
        self.dy += self.accelerationy
        self.counter += self.speed
        self.amplitude += self.speed*3

class bouncyCursor(cursor):
    def __init__(self, app, cx, cy, dx, dy, accelerationx, accelerationy):
        super().__init__(app, cx, cy, dx, dy, accelerationx, accelerationy)
        self.bottomBound = app.terminalTop + app.terminalHeight

    
    def move(self):
        self.cx += self.dx
        self.cy += self.dy
        self.dx += self.accelerationx
        self.dy += self.accelerationy
        if self.cy > self.bottomBound:
            self.dy *= -1 #flip direction

class zigZagCursor(cursor): 
    def __init__(self, app, cx, cy, dx, dy):
        self.lifeSpan = 120
        self.cx = cx
        self.cy = cy
        self.dx = dx
        self.dy = dy
        self.angle = getAngle(self.cx, self.cy, app.player.cx, app.player.cy)
        self.topBound = app.terminalTop
        self.bottomBound = app.terminalTop + app.terminalHeight
    
    def move(self):
        self.cx += self.dx
        self.cy += self.dy
        if self.cy <= self.topBound or self.cy >= self.bottomBound:
            self.dy *= -1
    
    def draw(self):
        angle = 90 - self.angle
        seperation = 0.3
        drawRegularPolygon(self.cx, self.cy, 7, 3, fill = 'white', 
                           rotateAngle = angle)
        drawRect(self.cx-self.dx*seperation, self.cy-self.dy*seperation, 
                 3, 15, fill = 'white', align = 'center', rotateAngle = angle)


class powerUp:
    def __init__(self, cx, cy, type):
        self.cx = cx
        self.cy = cy
        self.type = type
    
    def draw(self):
        drawLabel('***', self.cx, self.cy, fill = self.type, size = 26, 
                  bold = True)


class codeBlock:

    def __init__(self, app, cx, cy, string):
        self.left = cx - app.cellSize*(len(string)/2)
        self.cy = cy
        self.string = string
        self.typed = False
        self.i = 0
    
    def type(self, app): # type ith letter
        if self.i < len(self.string):
            codeCharLeft = self.left + self.i*app.cellSize
            spawnCodeChar(app, codeCharLeft, self.cy, self.string[self.i])
            self.i += 1
        else:
            self.typed = True



class blockChar:
    def __init__(self, cx, cy, c):
        self.cx = cx
        self.cy = cy
        self.c = c
    
    def draw(self):
        drawLabel(self.c, self.cx, self.cy, size = 15, 
                  font = 'monospace', fill = 'red', bold = True)

class healthPack:
    def __init__(self, cx, cy, hp):
        self.cx = cx
        self.cy = cy
        self.hp = 10
    
    def healPlayer(self, app):
        body = (app.player.body)
        rows, cols = len(body), len(body[0])
        for row in range(rows):
            for col in range(cols):
                if body[row][col] != 32 and body[row][col] < 126:
                    app.player.body[row][col] += 1
    def draw(self):
        drawLabel('+', self.cx, self.cy, size = 20, font = 'monospace', 
                  bold = True, fill = 'greenYellow')

####### CLASS-RELATED UTILITY FUNCTIONS

def getEllipseRadius(a, b, theta):
    return ((a*b)/((a**2) * (math.sin(theta)**2) + (b**2) 
                   * (math.cos(theta)**2))**0.5) # ellipse formula

def toRad(degrees):
    return degrees * (math.pi/180)
    
def toDegrees(rad):
    return rad * (180/math.pi)


def getAngle(cx, cy, mouseX, mouseY):
    clickdistance = (distance(cx, cy, mouseX, mouseY))
    if clickdistance == 0:
        return 0
    horizontal = mouseX - cx
    theta = math.acos(horizontal/clickdistance)
    theta *= 180/math.pi
    if mouseY > cy:
        theta = 180 - theta
        theta += 180
    return theta

##

def getTerminalCxCy(app):
    terminalcx = (app.terminalLeft + app.terminalWidth/2)
    terminalcy = (app.terminalTop + app.terminalHeight/2)
    return terminalcx, terminalcy



#####


def feetCount(row):
    return row.count(124)

def getFirstFootIndex(row):
    cols = len(row)
    for col in range(cols):
        if row[col] != 32: return col
    return
    
 #####
 
def rowIsAll32s(row):
        cols = len(row)
        for col in range(cols):
            if row[col] != 32:
                return False
        return True
    
def colIsAll32s(L, col):
        rows = len(L)
        for row in range(rows):
            if L[row][col] != 32:
                return False
        return True

def removeCol(L, col):
    rows = len(L)
    for row in range(rows):
        L[row].pop(col)


################################# FLIPPING
def flippedHorizontally(L):
    rows = len(L)
    flippedBody = []
    for row in range(rows):
        # get row while changing direction of /, \, <, > symbols (odd)
        currentRow = [x if isNotOddSymbol(x) else oddSymbolSwap(x) 
                      for x in L[row]]
        #flip row
        flippedRow = list(reversed(currentRow))
        flippedBody += [flippedRow]
    return flippedBody

def isNotOddSymbol(x):
    return x != 47 and x != 92 and x != 60 and x!= 62

def oddSymbolSwap(x):
    if x == 47: return 92
    if x == 92: return 47
    if x == 60: return 62
    if x == 62: return 60
######################## DRAWING

def redrawAll(app):
    drawBackground(app)
    drawTerminal(app)
    if not app.paused and not app.player.isDead and len(app.player.body) != 0:
        if app.player.isAttacking:
            app.player.drawAttack(app)
        if len(app.blockChars) != 0:
            for char in app.blockChars:
                char.draw()
        if len(app.powerUps) != 0:
            for powerUp in app.powerUps:
                powerUp.draw()
        if len(app.healthPacks) != 0:
            for pack in app.healthPacks:
                pack.draw()
        if len(app.player.dashEchoes) != 0:
            drawEchoes(app)
        if app.player.isWalking and app.player.hasFeet:
            drawPlayer(app, app.player.walkingBody)
        else:
            if len(app.player.body) != 0:
                drawPlayer(app, app.player.body)
        drawBorder(app)
        if len(app.player.smokeSpirals) != 0:
            drawSmoke(app)
        if len(app.cursors) != 0:
            for currentCursor in app.cursors:
                currentCursor.draw()
        if app.gameMode == 'infinite':
            drawLabel(f'points = {app.points}', 
                      app.terminalLeft + app.terminalWidth/5, 
                    app.terminalTop + 20, size = 20, font = 'monospace', 
                    fill = 'white')
            drawLabel(f'high score = {app.highScore}', 
                      app.terminalLeft + app.terminalWidth/1.3, 
                    app.terminalTop + 20, size = 20, font = 'monospace', 
                    fill = 'white')
        else:
            if app.displayedText != '':
                if app.bigText:
                    drawLabel(app.displayedText, app.terminalLeft + 
                            app.terminalWidth/2, app.terminalTop + 
                            app.terminalWidth/2, size = 30, font = 'monospace', 
                            fill = 'white', italic = True)
                else:
                    drawLabel(app.displayedText, 
                              app.terminalLeft + app.terminalWidth/2, 
                            app.terminalTop + 20, size = 20, font = 'monospace', 
                            fill = 'white', bold = True)
    elif app.player.isDead:
        drawDeathScreen(app)
    elif app.isSplashScreen:
        drawSplashScreen(app)
    else:
        drawPauseScreen(app)

def drawSplashScreen(app):
    terminalcx, terminalcy = getTerminalCxCy(app)
    drawPlayer(app, loadDesign('player'))
    drawLabel('ASCII MADNESS',terminalcx, 
                app.terminalTop + app.terminalHeight/3, fill = 'white', 
                font = 'monospace', bold = False, size = 30)
    drawLabel('select your game mode:', terminalcx, 
                app.terminalTop + app.terminalHeight/1.6, fill = 'white', 
                size = 20, font = 'monospace')
    for button in app.buttons:
        if app.hoveredButton != None and button == app.hoveredButton:
            fillcolor = 'darkGrey'
        else:
            fillcolor = 'white'
        drawRect(button.cx - button.width/2, button.cy - button.height/2, 
                 button.width, button.height, fill = 'black')
        drawLabel(button.name, button.cx, button.cy, fill = fillcolor, 
                  font = 'monospace', size = 18)
    if app.hasWon:
        drawLabel('gg! :>', terminalcx + app.terminalWidth/3, 
                  app.terminalTop + app.terminalHeight/3, 
                  rotateAngle = 37, fill = 'pink', size = 20, 
                  font = 'monospace', bold = True)


def drawDeathScreen(app):
    drawLabel('***YOU DIED***', app.terminalLeft + app.terminalWidth/2, 
              app.terminalTop + app.terminalHeight/3, 
              fill = 'red', font = 'monospace', bold = False, size = 30)
    if app.gameMode == 'infinite':
        drawLabel(f'final score = {app.points}',  
                app.terminalLeft + app.terminalWidth/2, 
                app.terminalTop + app.terminalHeight/2, size = 20, 
                font = 'monospace', fill = 'red')
    drawLabel('press r to restart', app.terminalLeft + app.terminalWidth/2, 
              app.terminalTop + app.terminalHeight/2 + 100, fill = 'red', 
              font = 'monospace', size = 20)

def drawPauseScreen(app):
    drawPlayer(app, loadDesign('player'))
    drawLabel('ASCII MADNESS', app.terminalLeft + app.terminalWidth/2, 
              app.terminalTop + app.terminalHeight/3, fill = 'white', 
              font = 'monospace', bold = False, size = 30)
    drawLabel('press p to play/pause', app.terminalLeft + app.terminalWidth/2, 
              app.terminalTop + app.terminalHeight/2 + 100, fill = 'white', 
              font = 'monospace', size = 20)
    drawLabel('press r to restart', app.terminalLeft + app.terminalWidth/2, 
              app.terminalTop + app.terminalHeight/2 + 150, fill = 'white', 
              font = 'monospace', size = 20)
    drawLabel('wasd 2 move. space 2 dash.', 
              app.terminalLeft + app.terminalWidth/2, 
              app.terminalTop + app.terminalHeight/2 + 200, fill = 'white', 
              font = 'monospace', size = 20)

def drawSmoke(app):
    i = 0
    while i < (len(app.player.smokeSpirals)):
        app.player.smokeSpirals[i].draw(app)
        i += 1

def drawBorder(app):
    drawLine(app.playerBoundLeft, app.playerBoundTop, 
             app.playerBoundRight, app.playerBoundTop, fill = 'white', 
             dashes = True)
    drawLine(app.playerBoundLeft, app.playerBoundTop, 
             app.playerBoundLeft, app.playerBoundBottom, fill = 'white', 
             dashes = (15, 2))
    drawLine(app.playerBoundLeft, app.playerBoundBottom, 
             app.playerBoundRight, app.playerBoundBottom, fill = 'white', 
             dashes = True)
    drawLine(app.playerBoundRight, app.playerBoundBottom, 
             app.playerBoundRight, app.playerBoundTop, fill = 'white', 
             dashes = (15, 2))


def drawBackground(app):
    drawRect(0, 0, app.width, app.height, fill = 'blue')


def drawTerminal(app):
    greySize = 20
    #draw grey part
    drawRect(app.terminalLeft, app.terminalTop - greySize, 
             app.terminalWidth, greySize, fill = 'lightgrey')
    drawRect(app.terminalLeft + 20, app.terminalTop - greySize*(3/4), 
             30, greySize/1.5, fill = 'grey')
    #draw black part
    drawRect(app.terminalLeft, app.terminalTop,app.terminalWidth, 
             app.terminalHeight, fill = 'black')
    

def drawEchoes(app):
    for currentEcho in app.player.dashEchoes:
        currentEcho.draw(app, app.player.body)

def drawPlayerCell(app, row, col, ASCIIindex): # CREDIT TO 112 CS ACADEMY
    cellLeft, cellTop = getCellLeftTop(app, row, col) # (TETRIS)
    cellWidth = cellHeight = app.cellSize
    if ASCIIindex != 32:
        if ASCIIindex < 42:
            fillColor = 'red'
        else:
            fillColor = 'white'
        message = chr(ASCIIindex)
        drawLabel(message, cellLeft + cellWidth/2, 
                  cellTop + cellHeight/2, fill = fillColor, 
                  bold = True, size = 15, font = 'monospace')


def drawPlayer(app, body):
    rows, cols = len(body), len(body[0])
    for row in range(rows):
        for col in range(cols):
            drawPlayerCell(app, row, col, body[row][col])

def getCellLeftTop(app, row, col):
    playerLeft, playerTop = getPlayerLeftTop(app)
    cellLeft = playerLeft + (col * app.cellSize)
    cellTop = playerTop + (row * app.cellSize)
    return (cellLeft, cellTop)

def getPlayerLeftTop(app):
    rows, cols = len(app.player.body), len(app.player.body[0])
    playerWidth, playerHeight = cols * app.cellSize, rows * app.cellSize
    left = app.player.cx - playerWidth//2
    top =  app.player.cy - playerHeight//2
    return left, top

####################### KEY PRESS
def onKeyPress(app, key):
    if key == 'r':
        onGameStart(app)
    if key == 'p':
        app.paused = not app.paused
    if not app.paused and not app.player.isDead:
        if key == 'a':
            if app.player.dx != -1:
                app.player.flip()
            app.player.dx = -1
        elif key == 'd':
            if app.player.dx != 1:
                app.player.flip()
            app.player.dx = 1

        if app.player.dashAvailable:
            if key == 'space' and not app.verticalPressed:
                app.player.dashAvailable = False
                app.player.dash(app, 0, app.player.dx)
            elif key == 'space' and not app.sidePressed:
                app.player.dashAvailable = False
                app.player.dash(app, app.player.dy, 0)
            elif key == 'space' and app.verticalPressed and app.sidePressed:
                app.player.dashAvailable = False
                app.player.dash(app, app.player.dy, app.player.dx)
        
        #DEVTEST - UNCOMMENT TO PLAY W/ SPAWNING
        '''
        if key == 'g':
            app.player.addBuff('green', app)
        if key == 'b':
            app.player.addBuff('blue', app)
        if key == 'm':
            app.player.addBuff('purple', app)

        if key == 'k':
            spawnPolygonCursors(app, app.player.cx, app.player.cy, 8, 100, 
            0.10, isUniform = True, type = 'cursor')
        if key == 'l':
            spawnLinearCursors(app, app.player.cx, app.player.cy, 6, 200, 500, 
            0.50, 80, isUniform = False, type = 'cursor')

        if key == 'j':
            spawnCodeBlock(app, 'meow')
        
        if key == 'z':
            spawnZigZagCursor(app, 30, 3)
        
        if key == 'i':
            spawnPowerUp(app, 'green')
        if key == 'y':
            app.storyStep = 9300 # choose step from script
        '''
        
def onKeyRelease(app, keys):
    app.player.isWalking = False
    app.sidePressed = False
    app.verticalPressed = False

def onKeyHold(app, keys):
    if not app.paused and not app.player.isDead:
        if 'a' or 'd' or 's' or 'w' in keys:
            app.player.isWalking = True
        if ('a' not in keys and 'd' not in keys and 's' not in keys 
            and 'w' not in keys):
            app.player.isWalking = False
        if 'a' in keys:
            app.sidePressed = True
            app.player.move(app, 0, -1)
        if 'd' in keys:
            app.sidePressed = True
            app.player.move(app, 0, 1)
        if 's' in keys:
            app.verticalPressed = True
            app.player.dy = 1
            app.player.move(app, 1, 0)
        if 'w' in keys:
            app.verticalPressed = True
            app.player.dy = -1
            app.player.move(app, -1, 0)


def spriteIsLegal(app):
    rows, cols = len(app.player.body), len(app.player.body[0])
    left, top = getPlayerLeftTop(app)
    right = left + cols * app.cellSize
    bottom = top + rows * app.cellSize
    return (left > app.playerBoundLeft and right < app.playerBoundRight 
            and bottom < app.playerBoundBottom and top > app.playerBoundTop)

############################ MOUSE PRESS


def onMouseMove(app, mouseX, mouseY):
    if app.isSplashScreen:
        if inButtonHitbox(app, mouseX, mouseY) != None:
            app.hoveredButton = inButtonHitbox(app, mouseX, mouseY)
        else:
            app.hoveredButton = None

def inButtonHitbox(app,x,y): #assuming no overlap
    for button in app.buttons:
        if (button.cx + button.width/2 > x and button.cx - button.width/2 < x
            and button.cy + button.height/2 > y and 
            button.cy - button.height/2 < y):
            return button


def onMousePress(app, mouseX, mouseY):
    if not app.paused and not app.player.isDead:
        if isInPlayerHitbox(app, mouseX, mouseY):
            row, col = getPlayerCellTouched(app, mouseX, mouseY)
            if row != None and col != None:
                app.player.damage(row, col, app.personalMouseDMG)
        else:
            app.player.attack(mouseX, mouseY)
    elif app.isSplashScreen:
        if inButtonHitbox(app,mouseX,mouseY):
            app.gameMode = app.hoveredButton.name
            app.isSplashScreen = False
            app.paused = True

def distance(x0, y0, x1, y1):
    return ((y1 - y0)**2 + (x1 - x0)**2)**0.5

def isInPlayerHitbox(app, x, y): #MOVE TO COLLISION DETECTION
    cellWidth = cellHeight = app.cellSize
    leftCoord, topCoord = getPlayerLeftTop(app)
    playerRows, playerCols = len(app.player.body), len(app.player.body[0])
    rightCoord = leftCoord + playerCols * cellWidth
    bottomCoord =  topCoord + playerRows * cellHeight
    return (leftCoord <= x <= rightCoord) and (topCoord <= y <= bottomCoord)

def getPlayerCellTouched(app, x, y):
    leftCoord, topCoord = getPlayerLeftTop(app)
    dx = x - leftCoord
    dy = y - topCoord
    cellWidth = cellHeight = app.cellSize
    row = math.floor(dy / cellHeight)
    col = math.floor(dx / cellWidth)
    playerRows, playerCols = len(app.player.body), len(app.player.body[0])
    if (0 <= row < playerRows) and (0 <= col < playerCols):
      return (row, col)
    else:
      return (None, None)



############################### ON STEP

def onStep(app):
    if len(app.player.body) == 0:
            if app.points >= app.highScore:
                app.highScore = app.points
            app.player.isDead = True
    if not app.paused and not app.player.isDead:
        if app.player.isAttacking:
            app.player.animateAttack(app)
            checkPlayerAttackCollision(app)
            removeCodeBlocks(app)
        if app.player.isWalking and app.player.hasFeet:
            animateWalk(app)
        if len(app.player.dashEchoes) > 0:
            fadeEchoes(app)
        if len(app.powerUps) > 0:
            checkPowerUpCollision(app)
        if len(app.healthPacks) > 0:
            checkHealthPackCollision(app)
        if app.player.hasBuff:
            spawnSmokeSpirals(app)
            app.player.decayBuffs()    
        if len(app.player.smokeSpirals) > 0:
            animateSmoke(app)
        if not app.player.dashAvailable:
            resetDash(app)
        if len(app.cursors) > 0:
            moveCursors(app)
            checkCursorCollision(app)
        if len(app.codeBlocks) != 0:
            for block in app.codeBlocks:
                if not block.typed:
                    block.type(app)
        elif app.gameMode == 'infinite': #spawn patterns in infinite
            spawnCodeBlock(app, random.choice(loadDesign('codeBlocks')))
        if app.gameMode == 'infinite':
            manageCodeSpawning(app)
            manageCursorSpawning(app)
            managePowerUpsSpawning(app)
        else:
            if app.textToDisplay != '':
                app.displayedText = app.displayedText + app.textToDisplay[0]
                app.textToDisplay = app.textToDisplay[1:]
            readStoryScript(app)
        ###


##############STORY MODE - unforunately 'elif' chain only way to run story
def readStoryScript(app):
    terminalcx, terminalcy = getTerminalCxCy(app)
    if app.storyStep == 0:
        displayText("you're alive?", app)
    elif app.storyStep == 60:
        spawnLinearCursors(app, app.player.cx, app.player.cy, 1, 
                           300, 50, 0.50, 45, 
                           isUniform = True, type = 'cursor')
    elif app.storyStep == 120:
        displayText('bro', app)
    elif app.storyStep == 180:
        displayText('get out of my terminal', app)
    elif app.storyStep == 200:
        spawnPolygonCursors(app, app.player.cx, app.player.cy, 3, 
                            300, 0.50, 
                            type = 'cursor')
    elif app.storyStep == 240:
        spawnPolygonCursors(app, app.player.cx, app.player.cy, 4, 
                            350, 0.70, 
                            type = 'cursor')
    elif app.storyStep == 260:
        spawnPolygonCursors(app, app.player.cx, app.player.cy, 5, 
                            350, 0.70, 
                            type = 'cursor')
    elif app.storyStep == 340:
        displayText('...', app)
    elif app.storyStep == 370:
        displayText('seriously', app)
    elif app.storyStep == 400:
        displayText('GET OUT!!', app)
    elif app.storyStep >= 400 and app.storyStep <= 450:
        terminalShakeEffect(app, 400, 450)
        if app.storyStep == 420:
            spawnPolygonCursors(app, app.player.cx, app.player.cy, 10, 
                                300, 0.70, 
                                type = 'cursor')
    elif app.storyStep == 460:
        app.bigText = True
        displayText('objective: ', app)
    elif app.storyStep == 480:
        app.textToDisplay = 'survive'
    elif app.storyStep == 520:
        spawnPolygonCursors(app, app.player.cx, app.player.cy, 8, 500, 0.70, 
                                type = 'cursor')
    elif app.storyStep == 580:
        app.bigText = False
        app.displayedText = ''
    elif app.storyStep == 610:
        spawnPolygonCursors(app, app.player.cx, app.player.cy, 9, 400, 0.70, 
                                type = 'cursor')
    elif app.storyStep == 650:
        spawnPolygonCursors(app, app.player.cx, app.player.cy, 10, 200, 0.70, 
                                type = 'cursor')
    elif app.storyStep == 700:
        spawnLinearCursors(app, app.player.cx, app.player.cy, 10, 200, 200, 
                           0.50, 180, 
                           isUniform = True, type = 'cursor')
    elif app.storyStep == 740:
        spawnLinearCursors(app, app.player.cx, app.player.cy, 10, 200, 200, 
                           0.50, 0, 
                           isUniform = True, type = 'cursor')
    elif app.storyStep == 770:
        spawnLinearCursors(app, app.player.cx, app.player.cy, 10, 200, 200, 
                           0.50, 90,
                           isUniform = True, type = 'cursor')
        spawnLinearCursors(app, app.player.cx, app.player.cy, 10, 200, 200, 
                           0.50, 90, 
                           isUniform = True, type = 'cursor')
    elif app.storyStep == 830:
        xManeuver(app)
    elif app.storyStep == 900:
        displayText('you are so...', app)
    elif app.storyStep == 970:
        squareManuever(app)
    elif app.storyStep == 1025:
        app.textToDisplay = '...annoying'
    elif app.storyStep == 1080:
        spawnHealthPack(app)
        displayText("what's that?", app) 
    elif app.storyStep == 1200:
        if len(app.healthPacks) > 0: #variety of dialogue :>
            displayText("i sure hope you don't walk over to that object", app)
        else:
            displayText('a health pack? a little op for this no?', app)
    elif app.storyStep == 1300:
        app.displayedText = ''
        spawnLinearCursors(app, app.player.cx, app.player.cy, 1, 300, 50, 0.50, 
                           110, 
                           isUniform = True, type = 'cursor')
        spawnLinearCursors(app, app.player.cx, app.player.cy, 1, 300, 50, 0.50, 
                           190, 
                        isUniform = True, type = 'cursor')
    elif app.storyStep == 1500:
        if len(app.healthPacks) > 0: #variety of dialogue :>
            displayText("pick up the health pack dude...", app)
        else:
            displayText('man.', app)
    elif app.storyStep == 1680:
        displayText('oooh you know what i just remembered?', app)
    elif app.storyStep == 1790:
        displayText('this.', app)
    elif app.storyStep == 1880:
        spawnCodeBlock(app, 'EXIT')
    elif app.storyStep == 1900:
        app.bigText = True
        displayText('new objective: ', app)
    elif app.storyStep == 1970:
        app.textToDisplay = 'break code.'
    elif app.storyStep == 2100:
        app.halted = True
        spawnCodeBlock(app, 'EXIT')
        app.storyStep += 1
    elif app.storyStep == 2180:
        app.bigText = False
        displayText('...', app)
    elif app.storyStep == 2230:
        displayText('what.', app)
    elif app.storyStep == 2400:
        for i in range(15):
            spawnCodeBlock(app, 'EXIT')
    elif app.storyStep == 2401:
        app.halted = True
        if len(app.cursors) < 20:
            angle = random.randint(0, 360)
            spawnLinearCursors(app, app.player.cx, app.player.cy, 1, 300, 
                               50, 0.50, angle, 
                           isUniform = True, type = 'cursor')
    elif app.storyStep == 2500:
        displayText('uhh', app)
    elif app.storyStep == 2700:
        for i in range(10):
            spawnCodeBlock(app, 'cd')
        app.tempCx, app.tempCy = getRandomCoords(app)
    elif app.storyStep == 2701:
        app.halted = True
        if len(app.cursors) < 30:
                spawnPolygonCursors(app, app.tempCx, app.tempCy, 6, 
                                    200, 0.50, type = 'arcCursor')
    elif app.storyStep == 2719:
        for i in range(20):
            spawnCodeBlock(app, 'pip')
        spawnPowerUp(app, 'blue')
    elif app.storyStep == 2720:
            app.halted = True
            if len(app.cursors) < 50:
                spawnLinearCursors(app, app.player.cx, app.player.cy, 6, 
                        200, 500, 0.50, 80, isUniform = False, type = 'cursor')
    elif app.storyStep == 2725:
        spawnPowerUp(app, 'green')
    elif app.storyStep == 2779:
        for i in range(20):
            spawnCodeBlock(app, 'break')
    elif app.storyStep == 2780:
        app.halted = True
        if len(app.cursors) < 13:
            spawnZigZagCursor(app, 30, 2, speed = 6)
    elif app.storyStep == 2781:
        for i in range(3):
            spawnHealthPack(app)
        spawnPowerUp(app, 'purple')
    elif app.storyStep == 3119:
        for i in range(3):
            spawnCodeBlock(app, 'cd')
    elif app.storyStep == 3200:
        while len(app.codeBlocks) < 5 and len(app.codeBlocks) > 0:
            spawnCodeBlock(app, 'cd')
        app.halted = True
        while len(app.cursors) < 5:
            angle1 = random.randint(0, 360)
            spawnLinearCursors(app, app.player.cx, app.player.cy, 5, 
                               300, 300, 0.50, angle1, 
                            isUniform = True, type = 'cursor')
            angle2 = random.randint(0, 360)
            spawnLinearCursors(app, app.player.cx, app.player.cy, 5, 
                               300, 300, 0.50, angle2, 
                            isUniform = True, type = 'cursor')
    elif app.storyStep == 3203: #NO MORE MR NICE GUY
        displayText("you know what you are? a pest.", app)
    elif app.storyStep >= 3300 and app.storyStep <= 3350:
            terminalShakeEffect(app, 3300, 3350)
            if app.storyStep % 3 == 0:
                angle = random.randint(0, 360)
                spawnLinearCursors(app, app.player.cx, app.player.cy, 1, 
                                   300, 50, 0.50, angle, 
                            isUniform = True, type = 'cursor')
    elif app.storyStep == 3400:
        app.bigText = True
        displayText('good luck.', app)
        spawnPowerUp(app, 'blue')
    elif app.storyStep == 3549:
        app.bigText = False
        app.displayedText = ''
    elif app.storyStep >= 3550 and app.storyStep <= 4000:
        if app.storyStep % 5 == 0:
            amt = random.randint(2, 7)
            spawnLinearCursors(app, terminalcx, terminalcy, amt, 
                               app.terminalWidth/2, app.terminalHeight, 
                               0.2, 180, type = 'cursor')
    elif app.storyStep == 4060:
        displayText('and again.', app)
    elif app.storyStep >= 4100 and app.storyStep <= 4650:
        if app.storyStep % 5 == 0:
            amt = random.randint(2, 7)
            spawnLinearCursors(app, terminalcx, terminalcy, amt,
                                app.terminalWidth/2, app.terminalHeight, 
                                0.2, 0, type = 'cursor')
    elif app.storyStep == 4660:
        displayText('and now...', app)
    elif app.storyStep >= 4700 and app.storyStep < 5250:
        if app.storyStep % 10 == 0:
            angle = 180
        elif app.storyStep % 5 == 0:
            angle = 0
        if app.storyStep % 5 == 0:
            amt = random.randint(1, 5)
            spawnLinearCursors(app, terminalcx, terminalcy, amt, 
                               app.terminalWidth/2, app.terminalHeight, 
                               0.15, angle, type = 'cursor')
    elif app.storyStep == 5300:
        spawnPowerUp(app, 'green')
    elif app.storyStep >= 5400 and app.storyStep < 6100:
        if app.storyStep % 50 == 0:
            spawnLinearCursors(app, app.player.cx, terminalcy, 20, 
                               app.terminalHeight/2, app.terminalWidth, 
                               0.4, 90, type = 'cursor')
        if app.storyStep == 6050:
            spawnPowerUp(app, 'purple')
    elif app.storyStep == 6200:
        displayText('oh...', app)
    elif app.storyStep == 6230:
        app.textToDisplay = 'i forgot to plug in my mouse'
    elif app.storyStep >= 6300 and app.storyStep <= 6350:
        terminalShakeEffect(app, 6300, 6350)
        if app.storyStep % 20 == 0:
            spawnPolygonCursors(app, app.player.cx, app.player.cy, 9, 400, 0.70, 
                                type = 'cursor')
    elif app.storyStep >= 6400 and app.storyStep <= 6600:
        if app.storyStep % 40 == 0:
            angle = 180
        elif app.storyStep % 20 == 0:
            angle = 0
        if app.storyStep % 20 == 0:
            spawnLinearCursors(app, terminalcx, terminalcy, 9, 
                               app.terminalWidth/2, app.terminalHeight, 
                               0.4, angle, type = 'cursor')
    elif app.storyStep == 6650:
        app.displayedText = ''
        spawnPowerUp(app, 'blue')
    elif app.storyStep >= 6700 and app.storyStep <= 7400:
        if app.storyStep % 100 == 0:
            angle = 180
        elif app.storyStep % 50 == 0:
            angle = 0
        if app.storyStep % 50 == 0:
            spawnLinearCursors(app, terminalcx, terminalcy, 7, 
                               app.terminalWidth/2, app.terminalHeight, 
                               0.4, angle, type = 'cursor')
        if app.storyStep % 10 == 0:
            angleSoloCursor = random.randint(0, 360)
            spawnLinearCursors(app, app.player.cx, app.player.cy, 1, 
                               300, 50, 0.50, angleSoloCursor, 
                            isUniform = True, type = 'cursor')
    elif app.storyStep >= 7500 and app.storyStep <= 7900:
        if app.storyStep == 7600:
                spawnCodeBlock(app, 'EXIT')
        if app.storyStep % 20 == 0:
            spawnPolygonCursors(app, app.player.cx, app.player.cy, 
                                5, 200, 0.70, 
                                type = 'cursor')
        if app.storyStep == 7899:
            app.halted = True
    elif app.storyStep == 7910:
        displayText('I JUST WANT TO DO MY HOMEWORK!', app)
    elif app.storyStep == 7960:
        displayText('...', app)
    elif app.storyStep == 8000:
         displayText('it ends here.', app)
         spawnPowerUp(app, 'blue')
         spawnPowerUp(app, 'green')
         spawnPowerUp(app, 'purple')
    elif app.storyStep > 8200 and app.storyStep <= 8650:
        cx, cy = getRandomCoords(app)
        if app.storyStep % 5 == 0:
            amt = random.randint(2, 5)
            spawnLinearCursors(app, terminalcx, terminalcy, 
                               amt, app.terminalWidth/2, app.terminalHeight, 
                               0.2, 180, type = 'cursor')
        if app.storyStep % 15 == 0:
            spawnPolygonCursors(app, cx, cy, 5, 0.01, 0.7, type = 'cursor')
    elif app.storyStep >= 8651 and app.storyStep <= 9101:
        cx, cy = getRandomCoords(app)
        if app.storyStep % 5 == 0:
            amt = random.randint(2, 5)
            spawnLinearCursors(app, terminalcx, terminalcy, 
                               amt, app.terminalWidth/2, app.terminalHeight, 
                               0.2, 0, type = 'cursor')
        if app.storyStep % 15 == 0:
            spawnPolygonCursors(app, cx, cy, 5, 0.01, 0.7, type = 'cursor')
    elif app.storyStep == 9102:
        displayText('...', app)
    elif app.storyStep == 9200:
        displayText('fine', app)
    elif app.storyStep == 9300:
        displayText("i'll get you some other time.", app)
    elif app.storyStep == 9450:
        displayText("i should probably see my family anyway, huh?", app)
    elif app.storyStep == 9600:
        displayText("i've just been playing stupid videogames", app)
    elif app.storyStep == 9800:
        displayText("yeah...", app)
    elif app.storyStep == 9870:
        app.textToDisplay = "i think i'll go outside"
    elif app.storyStep == 10200:
        app.hasWon = True
        onGameStart(app)
    if len(app.codeBlocks) == 0:
        app.halted = False
    if not app.halted:
        app.storyStep += 1


def squareManuever(app, radius = 400, length = 200):
    spawnLinearCursors(app, app.player.cx, app.player.cy, 10, radius, length, 
                       0.50, 0, isUniform = True, type = 'cursor')
    spawnLinearCursors(app, app.player.cx, app.player.cy, 10, radius, length, 
                       0.50, 90, isUniform = True, type = 'cursor')
    spawnLinearCursors(app, app.player.cx, app.player.cy, 10, radius, length, 
                       0.50, 180, isUniform = True, type = 'cursor')
    spawnLinearCursors(app, app.player.cx, app.player.cy, 10, radius, length, 
                       0.50, 270, isUniform = True, type = 'cursor')


def xManeuver(app, radius = 400, length = 200):
    spawnLinearCursors(app, app.player.cx, app.player.cy, 10, radius, length, 
                       0.50, 45, isUniform = True, type = 'cursor')
    spawnLinearCursors(app, app.player.cx, app.player.cy, 10, radius, length, 
                       0.50, 135, isUniform = True, type = 'cursor')
    spawnLinearCursors(app, app.player.cx, app.player.cy, 10, radius, length, 
                       0.50, 225, isUniform = True, type = 'cursor')
    spawnLinearCursors(app, app.player.cx, app.player.cy, 10, radius, length, 
                       0.50, 315, isUniform = True, type = 'cursor')


def terminalShakeEffect(app, startTime, endTime):
    midPoint = (endTime + startTime)/2
    q1Point = (startTime + midPoint)/2
    q2Point = (endTime + midPoint)/2
    if app.storyStep <= q1Point or (app.storyStep >= midPoint and 
                                    app.storyStep < q2Point):
        offset = 1
    if (app.storyStep > q1Point and 
        app.storyStep < midPoint) or (app.storyStep >= q2Point):
        offset = -1
    app.terminalLeft += offset
    app.playerBoundLeft += offset
    app.player.cx += offset
    app.playerBoundRight += offset


def displayText(string, app):
    app.displayedText = ''
    app.textToDisplay = string

#########INFINITE MODE

def managePowerUpsSpawning(app):
    threshhold = 1000
    if app.powerUpSpawnCounter > threshhold:
        color = random.choice(['blue', 'green', 'purple'])
        spawnPowerUp(app, color)
        app.powerUpSpawnCounter = 0
    else:
        app.powerUpSpawnCounter += 1


def manageCursorSpawning(app):
    if app.cursorSpawnCounter > app.cursorSpawnThreshhold:
        for codeblock in app.codeBlocks:
            spawnNewAttack(app, codeblock.string)
        app.cursorSpawnCounter = 0
        if app.cursorSpawnThreshhold > 40:
            app.cursorSpawnThreshhold -= 1 # MAKE THE GAME FASTER!
    else:
        app.cursorSpawnCounter += 1

def removeCodeBlocks(app):
    letterSet = set()
    for char in app.blockChars:
        letterSet.add(char.c)
    i = 0
    while i < len(app.codeBlocks):
        codeBlockBroken = False
        for letter in app.codeBlocks[i].string:
            if letter not in letterSet:
                codeBlockBroken = True
        if codeBlockBroken:
            app.codeBlocks.pop(i)
            app.points += 1
        else:
            i += 1



def spawnNewAttack(app, string):
        if string == 'pip':
            spawnPipAttack(app)
        elif string == 'cd':
            spawnCdAttack(app)
        elif string == 'EXIT':
            spawnExitAttack(app)
        else: #codeblock is break
            spawnBreakAttack(app)


def spawnPipAttack(app):
    i = random.randint(1,5)
    n = random.randint(3, 8)
    r = random.randint(100, 600)
    if i == 0:
        spawnPolygonCursors(app, app.player.cx, app.player.cy, n, r, 0.50, 
                            type = 'arcCursor')
    else:
        spawnPolygonCursors(app, app.player.cx, app.player.cy, n, r, 0.50, 
                            type = 'cursor')

def spawnCdAttack(app):
    i = random.randint(1,5)
    n = random.randint(3, 8)
    r = random.randint(100, 600)
    l = random.randint(100, 700)
    a = random.randint(1, 360)
    if i == 0:
        for j in range(n):
            spawnZigZagCursor(app, app.player.cx, 2+j)
    else:
        spawnLinearCursors(app, app.player.cx, app.player.cy, n, r, l, 0.50, a, 
                           isUniform = True, type = 'cursor')

def spawnBreakAttack(app):
    n = random.randint(3, 8)
    r = random.randint(100, 600)
    l = random.randint(100, 700)
    spawnLinearCursors(app, app.player.cx, app.player.cy, n, r, l, 0.50, 80, 
                       type = 'bouncyCursor')

def spawnExitAttack(app):
    n = random.randint(4, 8)
    r = random.randint(100, 600)
    for i in range(2, n):
        spawnPolygonCursors(app, app.player.cx, app.player.cy, i, r, 0.50, 
                            type = 'arcCursor')



def manageCodeSpawning(app):
    codeBlockSpawnThreshhold= 1000
    if app.codeBlockSpawnCounter > codeBlockSpawnThreshhold:
        spawnCodeBlock(app, random.choice(loadDesign('codeBlocks')))
        app.codeBlockSpawnCounter = 0
    else:
        app.codeBlockSpawnCounter += 1


def getRandomCoords(app):
    cx = (random.randint(rounded(app.playerBoundLeft + 10), 
                         rounded(app.playerBoundRight -10)))
    cy = (random.randint(rounded(app.playerBoundTop + 10), 
                         rounded(app.playerBoundBottom - 10)))
    return cx, cy

def spawnPowerUp(app, type = 'green'):
    cx, cy = getRandomCoords(app)
    app.powerUps+= [powerUp( cx, cy, type)]


def spawnHealthPack(app):
    cx, cy = getRandomCoords(app)
    app.healthPacks+= [healthPack( cx, cy, type)]


def checkHealthPackCollision(app):
    i = 0
    while i < len(app.healthPacks):
        pack = app.healthPacks[i]
        if isInPlayerHitbox(app, pack.cx, pack.cy):
            pack.healPlayer(app)
            pack.hp -= 1
        if pack.hp == 0:
            app.healthPacks.pop(i)
        else:
            i += 1


def checkPowerUpCollision(app):
    i = 0
    while i < len(app.powerUps):
        powerUp = app.powerUps[i]
        if isInPlayerHitbox(app, powerUp.cx, powerUp.cy):
            app.player.addBuff(powerUp.type, app)
            app.powerUps.pop(i)
        else:
            i += 1


def checkPlayerAttackCollision(app):
    rows, cols = len(app.player.body), len(app.player.body[0])
    playerWidth, playerHeight = cols * app.cellSize, rows * app.cellSize
    i = 0
    while i < len(app.blockChars):
        char = app.blockChars[i]
        angle = getAngle(app.player.cx, app.player.cy, char.cx, char.cy)
        attackRadius = getEllipseRadius(playerWidth/2, playerHeight/2, angle)
        distanceFromPlayer = distance(char.cx, char.cy, 
                                      app.player.cx, app.player.cy)
        lesserBoundaryAngle = (app.player.attackAngle - 
                                        (app.sweepConeWidth+20))
        greaterBoundaryAngle = (app.player.attackAngle + 
                                        (app.sweepConeWidth +20))
        if (isInCounterClockWiseOrder(lesserBoundaryAngle, 
                                      angle, greaterBoundaryAngle) and 
                distanceFromPlayer < attackRadius + app.attackOffset):
            app.blockChars.pop(i)
        else:
            i += 1

def isInCounterClockWiseOrder(first, middle, last):
     first %= 360
     middle %= 360
     last %= 360
     if first <= last:
        return first <= middle <= last
     return(first<=middle) or (middle<=last)


def resetDash(app):
    if app.dashCounter >= app.player.dashCoolDown:
        app.player.dashAvailable = True
        app.dashCounter = 0
    else:
        app.dashCounter += 1
        
def spawnSmokeSpirals(app):
    smokeSpawnThreshhold = 20
    if app.smokeSpawnCounter >= smokeSpawnThreshhold:
        app.player.spawnSmoke(app)
        app.smokeSpawnCounter = 0
    else:
        app.smokeSpawnCounter += 1


def fadeEchoes(app):
    echoThreshhold = 3
    if app.echoFadeCounter >= echoThreshhold:
        adjustEchoTimes(app)
        app.echoFadeCounter = 0
    else:
        app.echoFadeCounter += 1

def adjustEchoTimes(app):
    i = 0
    while i < (len(app.player.dashEchoes)):
        currentEcho = app.player.dashEchoes[i]
        currentEcho.time += 1
        #remove old echoes
        if currentEcho.time == app.echoTimeLength:
            app.player.dashEchoes.pop(i)
        i += 1


def animateWalk(app):
    walkThreshhold = 3
    #getting (readable) direction
    ## pacing of footsteps
    if app.walkCounter >= walkThreshhold:
        app.player.steppingOut = not app.player.steppingOut
        app.walkCounter = 0
    else: 
        app.walkCounter += 1
    app.player.walk(app)

def animateSmoke(app):
    smokeThreshhold = 3
    if app.smokeCounter >= smokeThreshhold:
        moveSmoke(app)
        app.smokeCounter = 0
    else:
        app.smokeCounter += 1

def moveSmoke(app): #on step
    distanceThreshhold = 200
    i = 0
    while i < (len(app.player.smokeSpirals)):
        currentSmoke = app.player.smokeSpirals[i]
        if (currentSmoke.cy < currentSmoke.cyBound or 
            distance(currentSmoke.cx, currentSmoke.cy, 
                     app.player.cx, app.player.cy) 
            > distanceThreshhold):
            app.player.smokeSpirals.pop(i)
        else:
            if (currentSmoke.cx < currentSmoke.bound1 or 
                    currentSmoke.cx > currentSmoke.bound2):
                currentSmoke.changeDirection()
            currentSmoke.move()
            i += 1

### CURSOR ATTACKS

def checkCursorCollision(app):
    for currentCursor in app.cursors:
        if len(app.player.body) == 0:
            if app.points >= app.highScore:
                app.highScore = app.points
            app.player.isDead = True
            break
        x, y = currentCursor.cx, currentCursor.cy
        if isInPlayerHitbox(app, x, y):
            row, col = getPlayerCellTouched(app, x, y)
            if row != None and col != None:
                app.player.damage(row, col, app.personalMouseDMG)


def moveCursors(app):
    i = 0
    while i < (len(app.cursors)):
        currentCursor = app.cursors[i]
        currentCursor.updateAngle(app)
        currentCursor.lifeSpan -= 1
        if (currentCursor.lifeSpan <= 0):
            app.cursors.pop(i)
        else:
            currentCursor.move()
        i += 1

def spawnPolygonCursors(app, cx, cy, N, r, acceleration, isUniform=True, 
                        type = 'cursor'):
    bounceFactor = 4
    for n in range(N): # uses roots of unity to calculate pos
        cursorx, cursory = (cx + r*math.cos(toRad((360/N)*n)), 
                                cy + r*math.sin(toRad((360/N)*n)))
        xDistanceFromCx, yDistanceFromCy = (cx - cursorx), (cy - cursory)
        dx, dy = xDistanceFromCx/r, yDistanceFromCy/r
        if isUniform:
            accelerationX = dx * acceleration
            accelerationY = dy * acceleration
        else:
            accelerationX = dx * acceleration + dx * 1/(n+0.1)
            accelerationY = dy * acceleration + dx * 1/(n+0.1)
        if type == 'cursor':
            app.cursors += [cursor(app, cursorx, cursory, bounceFactor*-dx, 
                                   bounceFactor*-dy, accelerationX, 
                                   accelerationY)]
        elif type == 'arcCursor':
            app.cursors += [arcCursor(app, cursorx, cursory, 
                                      dx, dy, accelerationX, accelerationY)]
    
def spawnLinearCursors(app, cx, cy, amt, r, lineLength, acceleration, angle=180, 
                            isUniform=True, type = 'cursor'):
    bounceFactor = 4
    seperation = lineLength / amt-1
    xToMidPoint, yToMidPoint = r*math.cos(toRad(angle)), r*math.sin(toRad(angle))
    midCursorX, midCursorY = (cx + xToMidPoint), (cy - yToMidPoint)
    run, rise = yToMidPoint/r, xToMidPoint/r #perpendicular slope = -reciprocal
    dx, dy = -1*rise, run
    startPointx, startPointy = (midCursorX - ((amt-1)/2)*run*seperation, 
                                midCursorY - ((amt-1)/2)*rise*seperation)
    for i in range(amt):
        cursorx, cursory = (startPointx + i*run*seperation, 
                            startPointy + i*rise*seperation)
        if isUniform:
            accelerationX = dx * acceleration
            accelerationY = dy * acceleration
        else:
            accelerationX = dx * acceleration + dx * 1/(i+0.1)
            accelerationY = dy * acceleration + dx * 1/(i+0.1)
        if type == 'cursor':
            app.cursors += [cursor(app, cursorx, cursory, bounceFactor*-dx, 
                                   bounceFactor*-dy, accelerationX, 
                                    accelerationY)]
        elif type == 'arcCursor':
            app.cursors += [arcCursor(app, cursorx, cursory, dx, dy, 
                                      accelerationX, accelerationY)]
        elif type == 'bouncyCursor':
            app.cursors += [bouncyCursor(app, cursorx, cursory, dx, dy, 
                                         accelerationX, accelerationY)]
        

def spawnZigZagCursor(app, cx, N, speed = 7): #where N is number of peaks
    dx = ((abs(app.player.cx-cx))/(2.5*N))*0.01*speed
    dy = app.terminalHeight*0.01 * speed
    app.cursors += [zigZagCursor(app, cx, app.player.cy, dx, dy)]

### SPAWNING CODE BLOCKS
def spawnCodeBlock(app, string):
    cx = random.randint(rounded(app.playerBoundLeft + 10), 
                        rounded(app.playerBoundRight - 10))
    cy = random.randint(rounded(app.playerBoundTop + 10), 
                        rounded(app.playerBoundBottom - 10))
    app.codeBlocks += [codeBlock(app, cx, cy, string)]


def spawnCodeChar(app, left, cy, c):
    cx = left + app.cellSize/2
    app.blockChars += [blockChar(cx, cy, c)]

######################## DESIGNS

def loadDesign(name):
    # name -> design
    catalog = { 'player': [[32, 32, 95, 95, 32], 
                        [32, 95, 61, 61, 95], 
                        [32, 32, 124, 46, 62], 
                        [32, 32, 47, 32, 96], 
                        [32, 60, 42, 59, 92], 
                        [95, 45, 42, 95, 46], 
                        [32, 32, 124, 124, 32]],
                'codeBlocks': ['cd', 'pip', 'break', 'EXIT']
                        }
    return catalog[name]




def main():
    runApp()

main()