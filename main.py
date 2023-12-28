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
        return self.program[self.registers['PC']]

    def interpret(self):
        while 1:
            instr = self.current()

            if instr == 0x00:
                self.increment()

                if self.current() == 0xE0:
                    #print("clear screen")
                    self.increment()

            elif instr >> 4 == 0x6:
                target_reg = instr & 0xF

                self.increment()
                self.registers['V'][target_reg] = self.current()

                #print(f"V[{target_reg}] = {hex( int(self.current()) )}")
                self.increment()

            elif instr >> 4 == 0xA:
                x1 = instr & 0xF

                self.increment()
                x2 = self.current()

                self.registers['I'] = (x1 << 8) | x2

                #print(f"I = {self.registers['I']:x}")
                self.increment()

            elif instr >> 4 == 0xD:
                # get co-ordinates
                x = self.registers['V'][ instr & 0xF ]

                self.increment()
                y = self.registers['V'][ self.current() >> 4]

                # load n-bytes sprite from memory location `I`
                n = self.current() & 0xF

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

