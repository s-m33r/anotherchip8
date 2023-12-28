import sys
import curses

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
            self.stdscr.addstr(y+i, x, line.replace('1','█').replace('0',' '))

        self.stdscr.refresh()

    def __del__(self):
        curses.nocbreak()
        self.stdscr.keypad(False)
        curses.echo()
        curses.endwin()

class Chip8:
    def __init__(self, program, display):
        self.program = program

        self.registers = {
            'V': {},
            'PC': 0,
            'I': 0,
        }

    def increment(self):
        self.registers['PC'] += 1

    def current(self):
        return f"{self.program[self.registers['PC']]:x}".upper()

    def interpret(self):
        while 1:
            instr = self.current()

            if instr == '0':
                self.increment()

                if self.current() == "E0":
                    #print("clear screen")
                    self.increment()

            elif instr[0] == '6':
                target_reg = int(instr[1], 16)

                self.increment()
                self.registers['V'][target_reg] = int(self.current(), 16)

                #print(f"V[{target_reg}] = {hex( int(self.current()) )}")
                self.increment()

            elif instr[0] == 'A':
                x1 = int(instr[1], 16)

                self.increment()
                x2 = int(self.current(), 16)

                self.registers['I'] = ( (x1 << 8) | x2 )

                #print(f"I = {self.registers['I']:x}")
                self.increment()

            elif instr[0] == 'D':
                # get co-ordinates
                x = self.registers['V'][int(instr[1])]

                self.increment()
                y = self.registers['V'][int(self.current()[0], 16)]

                # load n-bytes sprite from memory location `I`
                n = int(self.current()[1], 16)

                sprite = self.program[self.registers['I'] - 0x1FF - 1 : self.registers['I'] - 0x1FF + n - 1]

                # draw sprite at given coordinates
                display.draw(sprite, y, x)

                #print(f"draw {n}-long sprite at ({x},{y})")
                self.increment()


if __name__ == "__main__":
    rom_path = sys.argv[-1]

    program = None
    with open(rom_path, "rb") as f:
        program = f.read()

    display = Display()

    chip8 = Chip8(program, display)
    chip8.interpret()

