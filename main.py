import sys
import curses
import time


class Display:
    def __init__(self):
        self.stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        self.stdscr.keypad(True)
        curses.curs_set(0)

    def draw(self, sprite, y, x):
        drawing = [f"{line:#010b}"[2:] for line in sprite]

        for i, line in enumerate(drawing):
            self.stdscr.addnstr(y+i, x, line.replace('1','█').replace('0',' ').rstrip(), 8)

        self.stdscr.refresh()

    def clear(self):
        self.stdscr.clear()
        self.stdscr.refresh()

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
            #print(f"{self.current():x}")
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
                    case 0:
                        self.registers['V'][x] = Vy
                    case 1:
                        self.registers['V'][x] = Vx | Vy
                    case 2:
                        self.registers['V'][x] = Vx & Vy
                    case 3:
                        self.registers['V'][x] = Vx ^ Vy
                    case 4:
                        result = Vx + Vy
                        self.registers['V'][x] = result & 0b11111111
                        if result > 255:
                            self.registers['V'][0xF] = 1
                        else:
                            self.registers['V'][0xF] = 0
                    case 5:
                        self.registers['V'][x] = (Vx - Vy) & 0b11111111
                        if Vx > Vy:
                            self.registers['V'][0xF] = 1
                        else:
                            self.registers['V'][0xF] = 0
                    case 6:
                        self.registers['V'][x] = Vx >> 1
                        self.registers['V'][0xF] = Vx & 0x1
                    case 7:
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

            elif instr >> 4 == 0xA:
                x1 = instr & 0xF

                self.increment()
                x2 = self.current()

                self.registers['I'] = (x1 << 8) | x2

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

