import sys
import curses
import time
import random
import threading

FONT = [
    0xF0, 0x90, 0x90, 0x90, 0xF0, # 0
    0x20, 0x60, 0x20, 0x20, 0x70, # 1
    0xF0, 0x10, 0xF0, 0x80, 0xF0, # 2
    0xF0, 0x10, 0xF0, 0x10, 0xF0, # 3
    0x90, 0x90, 0xF0, 0x10, 0x10, # 4
    0xF0, 0x80, 0xF0, 0x10, 0xF0, # 5
    0xF0, 0x80, 0xF0, 0x90, 0xF0, # 6
    0xF0, 0x10, 0x20, 0x40, 0x40, # 7
    0xF0, 0x90, 0xF0, 0x90, 0xF0, # 8
    0xF0, 0x90, 0xF0, 0x10, 0xF0, # 9
    0xF0, 0x90, 0xF0, 0x90, 0x90, # A
    0xE0, 0x90, 0xE0, 0x90, 0xE0, # B
    0xF0, 0x80, 0x80, 0x80, 0xF0, # C
    0xE0, 0x90, 0x90, 0x90, 0xE0, # D
    0xF0, 0x80, 0xF0, 0x80, 0xF0, # E
    0xF0, 0x80, 0xF0, 0x80, 0x80, # F
]

KEYMAP = {
    '1': 0x1,
    '2': 0x2,
    '3': 0x3,
    '4': 0xC,

    'q': 0x4,
    'w': 0x5,
    'e': 0x6,
    'r': 0xD,

    'a': 0x7,
    's': 0x8,
    'd': 0x9,
    'f': 0xE,

    'z': 0xA,
    'x': 0x0,
    'c': 0xB,
    'v': 0xF,
}


class Display:
    def __init__(self):
        self.stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        self.stdscr.keypad(True)
        curses.curs_set(0)
        self.stdscr.nodelay(True)

        self.bitmap = [[0]*64 for _ in range(32)]
    
    def update_display(self):
        for Y, line in enumerate(self.bitmap):
            for X, pix in enumerate(line):
                self.stdscr.addnstr(Y, X, '█' if pix else ' ', 1)
        self.stdscr.refresh()

    def draw(self, sprite, y, x):
        drawing = [f"{line:#010b}"[2:] for line in sprite]

        overwrite_flag = False

        for i, line in enumerate(drawing):
            for j, ch in enumerate(line):
                X, Y = x+j, y+i

                if Y > 31:
                    Y -= 32
                elif Y < 0:
                    Y += 32
                    
                if X > 63:
                    X -= 64
                elif X < 0:
                    X += 64

                # sprites are XORd with existing pixel
                pix = int(ch) ^ self.bitmap[Y][X]

                if self.bitmap[Y][X] == 1 and pix == 0:
                    overwrite_flag = True

                self.bitmap[Y][X] = pix

        self.update_display()

        return overwrite_flag

    def clear(self):
        self.bitmap = [[0]*64 for _ in range(32)]
        self.update_display()

    def getkeypress(self):
        time.sleep(0.05)
        return self.stdscr.getch()

    def __del__(self):
        curses.nocbreak()
        self.stdscr.keypad(False)
        curses.echo()
        curses.endwin()

#class Display:
#    def __init__(self):
#        ...
#
#    def draw(self, sprite, y, x):
#        print(y, x)
#        drawing = [f"{line:#010b}"[2:] for line in sprite]
#
#        for line in drawing:
#            print(line.replace('1','█').replace('0',' '))
#        print()
#
#    def clear(self):
#        print("clear screen")


class Chip8:
    def __init__(self, program, display):
        self.memory = [0] * 4096
        for i, byte in enumerate(program):
            self.memory[0x200 + i] = byte

        for i, byte in enumerate(FONT):
            self.memory[i] = byte

        self.display = display

        self.stack = []
        self.registers = {
            'V': [0]*16,
            'PC': 0x200,
            'I': 0,
            'SP': -1,
            'DT': 0,
            'ST': 0
        }

        self.decrement_thread = threading.Thread(target=self.__decrement_timers, daemon=True)
        self.decrement_thread.start()

        self.keypress = -1

    def __decrement_timers(self):
        if self.registers['DT'] > 0:
            self.registers['DT'] -= 1
        if self.registers['ST'] > 0:
            self.registers['ST'] -= 1
        time.sleep(1/60)

    def increment(self, step=1):
        self.registers['PC'] += step

    def current(self):
        return self.memory[self.registers['PC']]

    def push(self, val):
        self.stack.append(val)
        self.registers['SP'] = len(self.stack) - 1

    def pop(self):
        self.registers['SP'] -= 1
        return self.stack.pop()

    def interpret(self):
        while 1:
            #print(self.stack)
            #print(self.registers)
            #print(hex(self.current()))
            #print("---")

            instr = self.current()

            if instr == 0x00:
                self.increment()

                if self.current() == 0xE0: # clear display
                    self.display.clear()
                    self.increment()

                elif self.current() == 0xEE: # return from subroutine
                    self.registers['PC'] = self.pop()

            elif instr >> 4 == 0x1: # jump to location nnn
                x1 = instr & 0xF

                self.increment()
                x2 = self.current()

                nnn = (x1 << 8) | x2
                self.registers['PC'] = nnn

            elif instr >> 4 == 0x2: # call subroutine at nnn
                self.push(
                    self.registers['PC'] + 2
                )

                x1 = instr & 0xF

                self.increment()
                x2 = self.current()

                nnn = (x1 << 8) | x2
                self.registers['PC'] = nnn

            elif instr >> 4 == 0x3: # skip next opcode if Vx == kk
                x = instr & 0xF

                self.increment()

                kk = self.current()

                if self.registers['V'][x] == kk:
                    self.increment(3)
                else:
                    self.increment()

            elif instr >> 4 == 0x4: # skip next opcode if Vx != kk
                x = instr & 0xF

                self.increment()

                kk = self.current()

                if self.registers['V'][x] != kk:
                    self.increment(3)
                else:
                    self.increment()

            elif instr >> 4 == 0x5: # skip next opcode if Vx == Vy
                x = instr & 0xF

                self.increment()

                y = self.current() >> 4

                if self.registers['V'][x] == self.registers['V'][y]:
                    self.increment(3)
                else:
                    self.increment()

            elif instr >> 4 == 0x6: # set Vx = byte
                target_reg = instr & 0xF

                self.increment()
                self.registers['V'][target_reg] = self.current()

                self.increment()

            elif instr >> 4 == 0x7: # Vx += byte
                target_reg = instr & 0xF

                self.increment()

                Vx = self.registers['V'][target_reg]
                self.registers['V'][target_reg] = (Vx + self.current()) & 0b11111111

                if Vx + self.current() > 255: # set carry bit in Vf
                    self.registers['V'][0xF] = 1
                else:
                    self.registers['V'][0xF] = 0

                self.increment()

            elif instr >> 4 == 0x8:
                x = instr & 0xF

                self.increment()
                
                y = self.current() >> 4

                mode = self.current() & 0xF

                Vx = self.registers['V'][x]
                Vy = self.registers['V'][y]

                match mode:
                    case 0x0:
                        self.registers['V'][x] = Vy
                    case 0x1:
                        self.registers['V'][x] = Vx | Vy
                    case 0x2:
                        self.registers['V'][x] = Vx & Vy
                    case 0x3:
                        self.registers['V'][x] = Vx ^ Vy
                    case 0x4:
                        result = Vx + Vy
                        self.registers['V'][x] = result & 0b11111111
                        if result > 255:
                            self.registers['V'][0xF] = 1
                        else:
                            self.registers['V'][0xF] = 0
                    case 0x5:
                        self.registers['V'][x] = (Vx - Vy) & 0b11111111
                        if Vx > Vy:
                            self.registers['V'][0xF] = 1
                        else:
                            self.registers['V'][0xF] = 0
                    case 0x6:
                        self.registers['V'][x] = (Vx >> 1) & 0b11111111
                        self.registers['V'][0xF] = Vx & 0x1
                    case 0x7:
                        self.registers['V'][x] = (Vy - Vx) & 0b11111111
                        if Vy > Vx:
                            self.registers['V'][0xF] = 1
                        else:
                            self.registers['V'][0xF] = 0
                    case 0xE:
                        self.registers['V'][x] = (Vx << 1) & 0b11111111
                        self.registers['V'][0xF] = Vx >> 7

                self.increment()

            elif instr >> 4 == 0x9: # skip next instruction if Vx != Vy
                x = instr & 0xF

                self.increment()

                y = self.current() >> 4

                if self.registers['V'][x] != self.registers['V'][y]:
                    self.increment(3)
                else:
                    self.increment()

            elif instr >> 4 == 0xA: # Set I = nnn.
                x1 = instr & 0xF

                self.increment()
                x2 = self.current()

                self.registers['I'] = (x1 << 8) | x2

                self.increment()

            elif instr >> 4 == 0xB: #  Jump to location nnn + V0.
                x1 = instr & 0xF

                self.increment()
                x2 = self.current()

                nnn = (x1 << 8) | x2

                self.registers['PC'] = nnn + self.registers['V'][0]

                self.increment()

            elif instr >> 4 == 0xC: #  Set Vx = random byte AND kk.
                x = instr & 0xF

                self.increment()
                kk = self.current()

                self.registers['V'][x] = random.randint(0, 255) & kk

                self.increment()

            elif instr >> 4 == 0xD:
                # get co-ordinates
                x = self.registers['V'][ instr & 0xF ]

                self.increment()
                y = self.registers['V'][ self.current() >> 4]

                # load n-bytes sprite from memory location `I`
                n = self.current() & 0xF

                sprite = self.memory[self.registers['I'] : self.registers['I'] + n]

                # draw sprite at given coordinates
                overwrite_flag = self.display.draw(sprite, y, x)

                # set collision bit
                if overwrite_flag:
                    self.registers['V'][0xF] = 0x1
                else:
                    self.registers['V'][0xF] = 0x0

                self.increment()

            elif instr >> 4 == 0xE:
                x = instr & 0xF

                self.increment()

                key = self.display.getkeypress()
                if key > 0 and chr(key) in KEYMAP:
                    key = KEYMAP[chr(key)]
                else:
                    self.increment()
                    continue
 
                if self.current() == 0x9E:
                    if key == self.registers['V'][x]: # Skip next instruction if key with the value of Vx is pressed.
                        self.increment(3)
                    else:
                        self.increment()

                elif self.current() == 0xA1:
                    if key != self.registers['V'][x]: # Skip next instruction if key with the value of Vx is not pressed.
                        self.increment(3)
                    else:
                        self.increment()

            elif instr >> 4 == 0xF:
                x = instr & 0xF

                self.increment()

                if self.current() == 0x7: # Set Vx = delay timer value.
                    self.registers['V'][x] = self.registers['DT']

                elif self.current() == 0xA: # Wait for a key press, store the value of the key in Vx.
                    key = self.display.getkeypress()
                    while key == -1 or chr(key) not in KEYMAP:
                        key = self.keypress

                    self.registers['V'][x] = KEYMAP[chr(key)]

                elif self.current() == 0x15: # Set delay timer = Vx.
                    self.registers['DT'] = self.registers['V'][x]

                elif self.current() == 0x18: # Set sound timer = Vx.
                    self.registers['ST'] = self.registers['V'][x]

                elif self.current() == 0x1E: # set I = I + Vx
                    self.registers['I'] += self.registers['V'][x]

                elif self.current() == 0x29: # Set I = location of sprite for digit Vx.
                    if 0x0 <= self.registers['V'][x] <= 0xF:
                        self.registers['I'] = self.registers['V'][x] * 5
                
                elif self.current() == 0x33: #  Store BCD representation of Vx in memory locations I, I+1, and I+2.
                    val = self.registers['V'][x]

                    self.memory[ self.registers['I'] + 2 ] = val % 10
                    val //= 10
                    self.memory[ self.registers['I'] + 1 ] = val % 10
                    val //= 10
                    self.memory[ self.registers['I'] ] = val % 10

                elif self.current() == 0x55: # save registers V0-x to memory, starting from location I
                    for i in range(x+1):
                        self.memory[ self.registers['I'] + i ] = self.registers['V'][i]

                elif self.current() == 0x65: # read registers V0-x from memory, starting from location I
                    for i in range(x+1):
                        self.registers['V'][i] = self.memory[ self.registers['I'] + i ]

                self.increment()

            time.sleep(1 / 300)
            self.registers['DT'] -= 1
            self.registers['ST'] -= 1

            if self.registers['ST'] > 0:
                # play tone
                ...

if __name__ == "__main__":
    rom_path = sys.argv[-1]

    program = None
    with open(rom_path, "rb") as f:
        program = f.read()

    display = Display()

    chip8 = Chip8(program, display)
    chip8.interpret()

