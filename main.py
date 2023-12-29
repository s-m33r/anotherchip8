import sys
import curses
import time
import random


class Display:
    def __init__(self):
        self.stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        self.stdscr.keypad(True)
        curses.curs_set(0)
        self.stdscr.nodelay(True)

    def draw(self, sprite, y, x):
        drawing = [f"{line:#010b}"[2:] for line in sprite]

        for i, line in enumerate(drawing):
            self.stdscr.addnstr(y+i, x, line.replace('1','█').replace('0',' ').rstrip(), 8)

        self.stdscr.refresh()

    def clear(self):
        self.stdscr.clear()
        self.stdscr.refresh()

    def getkeypress(self):
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

        self.keypad = {
            0x1: False,
            0x2: False,
            0x3: False,
            0xC: False,

            0x4: False,
            0x5: False,
            0x6: False,
            0xD: False,

            0x7: False,
            0x8: False,
            0x9: False,
            0xE: False,

            0xA: False,
            0x0: False,
            0xB: False,
            0xF: False,
        }

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
    
    def read_keypress(self, key):
        self.keypad = dict.fromkeys(self.keypad, False)

        if key == ord('1'):
            self.keypad[0x1] = True
        elif key == ord('2'):
            self.keypad[0x2] = True
        elif key == ord('3'):
            self.keypad[0x3] = True
        elif key == ord('4'):
            self.keypad[0xC] = True

        elif key == ord('q'):
            self.keypad[0x4] = True
        elif key == ord('w'):
            self.keypad[0x5] = True
        elif key == ord('e'):
            self.keypad[0x6] = True
        elif key == ord('r'):
            self.keypad[0xD] = True

        elif key == ord('a'):
            self.keypad[0x7] = True
        elif key == ord('s'):
            self.keypad[0x8] = True
        elif key == ord('d'):
            self.keypad[0x9] = True
        elif key == ord('f'):
            self.keypad[0xE] = True

        elif key == ord('z'):
            self.keypad[0xA] = True
        elif key == ord('x'):
            self.keypad[0x0] = True
        elif key == ord('c'):
            self.keypad[0xB] = True
        elif key == ord('v'):
            self.keypad[0xF] = True

    def interpret(self):
        while 1:
            #print(self.stack)
            #print(self.registers)
            #print(f"{self.current():x}")
            # print(self.keypad)
            #print("---")
            self.read_keypress(display.getkeypress())

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
                        self.registers['V'][x] = Vx >> 1
                        self.registers['V'][0xF] = Vx & 0x1
                    case 0x7:
                        self.registers['V'][x] = (Vy - Vx) & 0b11111111
                        if Vy > Vx:
                            self.registers['V'][0xF] = 1
                        else:
                            self.registers['V'][0xF] = 0
                    case 0xE:
                        self.registers['V'][x] = (Vx << 1) & 0b11111111
                        self.registers['V'][0xF] = Vx & 0x80

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
                self.display.draw(sprite, y, x)

                self.increment()

            elif instr >> 4 == 0xE:
                x = instr & 0xF

                self.increment()

                if self.current() == 0x9E:
                    if self.keypad[ self.registers['V'][x] ]: # Skip next instruction if key with the value of Vx is pressed.
                        self.increment(3)
                    else:
                        self.increment()

                if self.current() == 0xA1:
                    if not self.keypad[ self.registers['V'][x] ]: # Skip next instruction if key with the value of Vx is not pressed.
                        self.increment(3)
                    else:
                        self.increment()

            elif instr >> 4 == 0xF:
                x = instr & 0xF

                self.increment()
                
                if self.current() == 0x65: # read registers V0-x from memory, starting from location I
                    for i in range(x+1):
                        self.registers['V'][i] = self.memory[ self.registers['I'] + i ]

                elif self.current() == 0x55: # save registers V0-x to memory, starting from location I
                    for i in range(x+1):
                        self.memory[ self.registers['I'] + i ] = self.registers['V'][i]

                elif self.current() == 0x1E: # set I = I + Vx
                    self.registers['I'] += self.registers['V'][x]

                elif self.current() == 0x33: #  Store BCD representation of Vx in memory locations I, I+1, and I+2.
                    val = self.registers['V'][x]

                    self.memory[ self.registers['I'] + 2 ] = val % 10
                    val //= 10
                    self.memory[ self.registers['I'] + 1 ] = val % 10
                    val //= 10
                    self.memory[ self.registers['I'] ] = val % 10

                self.increment()


if __name__ == "__main__":
    rom_path = sys.argv[-1]

    program = None
    with open(rom_path, "rb") as f:
        program = f.read()

    display = Display()

    chip8 = Chip8(program, display)
    chip8.interpret()

